# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""verify_source_disc: is this YOUR dump of the Japanese disc the one the translation data was made for?

The public repository holds no Japanese text and no game files (docs/l10n-format.md).  Everything that needs the original
(l10n import, texture deltas, the patch build) therefore starts from the player's own disc and REFUSES to run on a dump
that differs from the one the hashes were taken from.  This tool is that gate; tools/l10n.py and tools/setup_from_disc.py
call it before they read a single string.

    python -I -X utf8 tools/verify_source_disc.py "My Game.cue"            # BIN/CUE (Redump), one raw .bin per track
    python -I -X utf8 tools/verify_source_disc.py disc.gdi                 # GDI + raw track files
    python -I -X utf8 tools/verify_source_disc.py "My Game.iso"            # the 2048-byte 'volume ISO' (docs/xdelta-release.md)
    python -I -X utf8 tools/verify_source_disc.py --extracted extracted    # the folder made by tools/extract.py / setup_from_disc.py
    python -I -X utf8 tools/verify_source_disc.py --write-manifest l10n/disc-files.tsv "My Game.cue"   # maintainer only

What is checked
  disc image   size, SHA-1 and SHA-256 of every track file (cue/gdi) or of the volume ISO against the hashes recorded in
               tools/release.toml ([source.track1..5], [source.volume_iso]).  If the track files differ but hold the same game
               data (another dumper stored pregaps or audio differently) the cooked volume ISO is hashed instead (streamed, nothing
               is written) and accepted when it equals [source.volume_iso]; the tools read the disc through its LBAs, so that is enough.
  extracted/   every file of the manifest l10n/disc-files.tsv (path, LBA, size, SHA-256; BCAST/BCAST.BIN is not extracted and is
               skipped) must exist with that size and SHA-256.  Files that are not in the manifest are ignored.
Exit status: 0 verified, 1 mismatch (every difference is printed), 2 bad command line / unreadable input.
The hashes in tools/release.toml were measured on the repo author's Redump-style dump (Redump disc 27370, as dumped); the Redump
database itself was not consulted.  Pure standard library, Python 3.11+ (tomllib).
"""
import argparse
import hashlib
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bincue2iso as BC      # noqa: E402
import discformat as DF      # noqa: E402
import gdrom                 # noqa: E402

RELEASE_TOML = os.path.join(HERE, 'release.toml')
MANIFEST = os.path.join(ROOT, 'l10n', 'disc-files.tsv')
HD_BASE = 45000
SS = 2352
USER = 2048
BCAST_PATH = '/BCAST/BCAST.BIN'
IP_PATH = '/IP.BIN'
CHUNK = 1 << 24
HASHES = ('size', 'sha1', 'sha256')


class VerifyError(Exception):
    """A readable problem (printed without a traceback)."""


# ------------------------------------------------------------------------------------------- expected hashes
def load_expected(path=None):
    """{'track1'..'track5', 'volume_iso': {size, crc32, md5, sha1, sha256}} and the [release] table, from tools/release.toml."""
    try:
        import tomllib
    except ImportError:
        raise VerifyError('Python 3.11 or newer is needed (tomllib) to read tools/release.toml')
    with open(path or RELEASE_TOML, 'rb') as f:
        cfg = tomllib.load(f)
    src = cfg.get('source') or {}
    exp = {}
    for k in ['track%d' % n for n in range(1, 6)] + ['volume_iso']:
        h = src.get(k)
        if not h or not all(x in h for x in HASHES):
            raise VerifyError('%s has no recorded hashes for [source.%s]' % (path or RELEASE_TOML, k))
        exp[k] = dict(h)
    return exp, cfg.get('release', {})


# ------------------------------------------------------------------------------------------- hashing
class Progress:
    def __init__(self, label, log):
        self.label, self.log, self.shown = label, log, -1

    def __call__(self, done, total):
        pct = 100 * done // total if total else 100
        if self.log and pct // 25 != self.shown:
            self.shown = pct // 25
            self.log('    %s %d%%' % (self.label, pct))


def hash_file(path, progress=None):
    """size, sha1, sha256 of a file in one pass."""
    s1, s2 = hashlib.sha1(), hashlib.sha256()
    size = os.path.getsize(path)
    done = 0
    with open(path, 'rb') as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            s1.update(b)
            s2.update(b)
            done += len(b)
            if progress:
                progress(done, size)
    return {'size': size, 'sha1': s1.hexdigest(), 'sha256': s2.hexdigest()}


def same(h, want):
    return all(str(h[k]) == str(want[k]) for k in HASHES)


def diff_text(label, h, want):
    bits = []
    if h['size'] != int(want['size']):
        bits.append('size %s, expected %s' % ('{:,}'.format(h['size']), '{:,}'.format(int(want['size']))))
    for k, hname in (('sha1', 'SHA-1'), ('sha256', 'SHA-256')):
        if h[k] != want[k]:
            bits.append('%s %s, expected %s' % (hname, h[k], want[k]))
    return '%s: %s' % (label, '; '.join(bits))


# ------------------------------------------------------------------------------------------- reading a disc
class SourceDisc:
    """A player's disc image opened for reading by LBA.  `read(lba, size)` returns the user data (2048 bytes per
    sector) of consecutive sectors, whatever the container: raw 2352-byte tracks of a .cue / .gdi, or a volume ISO."""

    def __init__(self, path):
        try:
            self.info = DF.open_disc(path)
        except DF.DiscError as e:
            raise VerifyError(str(e))
        self.path = self.info.path
        self.kind = self.info.kind               # 'cue' | 'gdi' | 'iso'
        self._fh = {}
        self._files = None
        if self.kind == 'iso':
            self.iso = self.info.iso
            self.tracks = []
        else:
            try:
                self.tracks = [t for t in BC.load_tracks(self.path)]
            except BC.DumpError as e:
                raise VerifyError(str(e))
            self.iso = None

    def close(self):
        for f in self._fh.values():
            f.close()
        self._fh = {}

    def _open(self, path):
        f = self._fh.get(path)
        if f is None:
            f = self._fh[path] = open(path, 'rb')
        return f

    def _track_for(self, lba):
        for t in self.tracks:
            if t.kind == 'data' and t.lba <= lba < t.lba + t.sectors:
                return t
        return None

    def read(self, lba, size):
        nsec = (size + USER - 1) // USER
        if self.iso:
            f = self._open(self.iso)
            f.seek((lba - HD_BASE) * USER)
            b = f.read(nsec * USER)
            if len(b) < size:
                raise VerifyError('read past the end of %s (LBA %d)' % (self.iso, lba))
            return b[:size]
        out = []
        pos = lba
        left = nsec
        while left:
            t = self._track_for(pos)
            if t is None:
                raise VerifyError('LBA %d is not inside a data track of %s' % (pos, self.path))
            n = min(left, t.lba + t.sectors - pos)
            f = self._open(t.path)
            f.seek(t.file_offset + (pos - t.lba) * t.sector_size)
            raw = f.read(n * t.sector_size)
            if len(raw) != n * t.sector_size:
                raise VerifyError('%s is truncated' % t.path)
            if t.sector_size == USER:
                out.append(raw)
            else:
                ss = t.sector_size
                for i in range(n):
                    s = raw[i * ss:(i + 1) * ss]
                    if s[15] == 2:
                        out.append(s[24:24 + USER])
                    elif s[15] == 1:
                        out.append(s[16:16 + USER])
                    elif not any(s):
                        out.append(b'\0' * USER)
                    else:
                        raise VerifyError('LBA %d of %s: unexpected sector mode %d' % (pos + i, t.path, s[15]))
            pos += n
            left -= n
        return b''.join(out)[:size]

    # -- ISO9660 view
    def files(self):
        """[(iso path, lba, size)] of every file of the volume (IP.BIN not included), in directory order."""
        if self._files is None:
            try:
                root = gdrom.pvd_root(self)
                self._files = list(gdrom.walk(self, *root))
            except (struct.error, IndexError, VerifyError) as e:
                raise VerifyError('cannot read the ISO9660 volume of %s (%s)' % (self.path, e))
            if not self._files:
                raise VerifyError('no files found in the volume of %s' % self.path)
        return self._files

    def find(self, iso_path):
        for p, lba, size in self.files():
            if p == iso_path:
                return lba, size
        raise VerifyError('%s is not on the disc' % iso_path)

    def read_file(self, iso_path):
        lba, size = self.find(iso_path)
        return self.read(lba, size)

    def iter_file(self, lba, size, step=1 << 24):
        pos = 0
        while pos < size:
            n = min(step, size - pos)
            yield self.read(lba + pos // USER, n)
            pos += n


# ------------------------------------------------------------------------------------------- verification
class Result:
    def __init__(self):
        self.ok = False
        self.route = ''
        self.problems = []
        self.notes = []
        self.hashes = {}

    def text(self):
        out = list(self.notes)
        if self.ok:
            out.append('VERIFIED (%s)' % self.route)
        else:
            out.append('NOT VERIFIED:')
            out.extend('  ' + p for p in self.problems)
        return '\n'.join(out)


def volume_hash(tracks, log=None):
    """size, sha1, sha256 of the cooked volume ISO of a bin/cue or gdi (what tools/bincue2iso.py writes), streamed."""
    data = sorted([t for t in tracks if t.kind == 'data' and t.lba >= HD_BASE], key=lambda t: t.lba)
    if not data:
        raise VerifyError('no high-density data track found')
    end = max(t.lba + t.sectors for t in tracks if t.kind == 'data' and t.lba >= HD_BASE)
    audio_end = max([t.lba + t.sectors for t in tracks if t.lba >= HD_BASE], default=end)
    total = max(end, audio_end) - HD_BASE
    s1, s2 = hashlib.sha1(), hashlib.sha256()
    written = 0
    stats = BC.Stats()
    zero = b'\0' * USER

    def feed(b):
        s1.update(b)
        s2.update(b)

    try:
        for t in data:
            gap = (t.lba - HD_BASE) - written
            if gap < 0:
                raise VerifyError('track %d overlaps the previous track' % t.num)
            for _ in range(gap):
                feed(zero)
            written += gap
            for lba, cooked in BC.iter_cooked(t, stats, False):
                feed(cooked)
                written += len(cooked) // USER
            if log:
                log('    cooked track %d' % t.num)
        for _ in range(total - written):
            feed(zero)
    except BC.DumpError as e:
        raise VerifyError(str(e))
    return {'size': total * USER, 'sha1': s1.hexdigest(), 'sha256': s2.hexdigest()}


def verify_disc(path, release_toml=None, log=print):
    """Check a disc image against tools/release.toml.  Returns a Result (never raises for a mismatch)."""
    exp, _ = load_expected(release_toml)
    res = Result()
    if not os.path.isfile(path):
        res.problems.append('no such file: %s' % path)
        return res
    disc = SourceDisc(path)
    disc.close()
    if disc.kind == 'iso':
        log('Hashing the volume ISO %s' % disc.iso)
        h = hash_file(disc.iso, Progress('hashing', log))
        res.hashes['volume_iso'] = h
        if same(h, exp['volume_iso']):
            res.ok, res.route = True, 'volume ISO identical to the recorded dump'
        else:
            res.problems.append(diff_text('volume ISO %s' % disc.iso, h, exp['volume_iso']))
            res.problems.append('this is not the dump the translation data was made for (another dump, a modified or an '
                                'already patched image)')
        return res
    bad = []
    for t in sorted(disc.tracks, key=lambda t: t.num):
        key = 'track%d' % t.num
        log('Hashing track %d: %s' % (t.num, os.path.basename(t.path)))
        h = hash_file(t.path, Progress('hashing', log))
        res.hashes[key] = h
        if same(h, exp[key]):
            log('    -> identical')
        else:
            bad.append(diff_text('track %d (%s)' % (t.num, t.path), h, exp[key]))
            log('    -> DIFFERENT')
    if not bad:
        res.ok, res.route = True, '%s: all %d tracks identical to the recorded dump' % (disc.kind, len(disc.tracks))
        return res
    # same game data stored differently?  (the tools read through LBAs, so the cooked volume is what counts)
    log('A track file differs; comparing the cooked volume (game data only, streamed) ...')
    try:
        vh = volume_hash(disc.tracks, log)
    except VerifyError as e:
        res.problems = bad + [str(e)]
        return res
    res.hashes['volume_iso'] = vh
    if same(vh, exp['volume_iso']):
        res.ok = True
        res.route = 'the game data is identical (cooked volume ISO equals the recorded one); only the track files differ'
        res.notes.append('note: ' + '; '.join(bad))
        return res
    res.problems = bad + [diff_text('cooked volume of %s' % path, vh, exp['volume_iso']),
                          'this is not the dump the translation data was made for (another game revision, a bad dump, '
                          'or a modified image)']
    return res


# ------------------------------------------------------------------------------------------- manifest of the files
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def read_manifest(path=None):
    """[(iso path, lba, size, sha256)] from l10n/disc-files.tsv (lines starting with # are comments)."""
    path = path or MANIFEST
    if not os.path.isfile(path):
        raise VerifyError('the file manifest %s is missing (maintainers create it with --write-manifest)' % path)
    rows = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#') or line.startswith('path\t'):
                continue
            p, lba, size, sha = line.split('\t')
            rows.append((p, int(lba), int(size), sha))
    return rows


def write_manifest(disc, out_path, log=print):
    """Hash every file of the volume (and IP.BIN) read straight from the disc; BCAST.BIN is hashed too (it is not extracted)."""
    rows = [(IP_PATH, HD_BASE, 16 * USER, hashlib.sha256(disc.read(HD_BASE, 16 * USER)).hexdigest())]
    files = disc.files()
    for i, (p, lba, size) in enumerate(files):
        h = hashlib.sha256()
        for b in disc.iter_file(lba, size):
            h.update(b)
        rows.append((p, lba, size, h.hexdigest()))
        if size > 1 << 26:
            log('  hashed %s (%s bytes)' % (p, '{:,}'.format(size)))
    rows.sort(key=lambda r: r[0])
    tmp = out_path + '.tmp'
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# SakaTsuku Tokudaigou 2 source disc: every file of the volume (HDR-0183), written by tools/verify_source_disc.py --write-manifest.\n')
        f.write('# Used by tools/verify_source_disc.py --extracted DIR to check a folder made by tools/extract.py. No game data, only names, sizes, hashes.\n')
        f.write('path\tlba\tsize\tsha256\n')
        for p, lba, size, sha in rows:
            f.write('%s\t%d\t%d\t%s\n' % (p, lba, size, sha))
    os.replace(tmp, out_path)
    return rows


def verify_extracted(folder, manifest=None, log=print):
    """Check a folder of extracted files against the manifest.  Returns a Result."""
    res = Result()
    rows = read_manifest(manifest)
    if not os.path.isdir(folder):
        res.problems.append('no such folder: %s' % folder)
        return res
    n = checked = 0
    for p, lba, size, sha in rows:
        if p == BCAST_PATH:
            res.notes.append('note: %s is not extracted (it is read from the disc image itself)' % p)
            continue
        n += 1
        full = os.path.join(folder, *p.lstrip('/').split('/'))
        if not os.path.isfile(full):
            res.problems.append('missing: %s' % p)
            continue
        if os.path.getsize(full) != size:
            res.problems.append('%s: size %s, expected %s' % (p, '{:,}'.format(os.path.getsize(full)), '{:,}'.format(size)))
            continue
        if sha256_file(full) != sha:
            res.problems.append('%s: SHA-256 differs from the recorded dump' % p)
            continue
        checked += 1
    log('%d of %d manifest files are identical' % (checked, n))
    if res.problems:
        if len(res.problems) > 25:
            more = len(res.problems) - 25
            res.problems = res.problems[:25] + ['... and %d more' % more]
        return res
    res.ok, res.route = True, 'extracted folder: %d files identical to the manifest' % checked
    return res


# ------------------------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('disc', nargs='?', help='.cue / .gdi / volume .iso of YOUR dump')
    ap.add_argument('--extracted', metavar='DIR', help='check a folder of extracted files against the manifest instead of a disc')
    ap.add_argument('--manifest', default=MANIFEST, help='file manifest (default l10n/disc-files.tsv)')
    ap.add_argument('--release-toml', default=RELEASE_TOML)
    ap.add_argument('--write-manifest', metavar='FILE', help='maintainer: write the file manifest from the disc (needs DISC)')
    a = ap.parse_args(argv)
    t0 = time.time()
    try:
        if a.extracted:
            res = verify_extracted(a.extracted, a.manifest)
        elif a.disc:
            res = verify_disc(a.disc, a.release_toml)
            if res.ok and a.write_manifest:
                d = SourceDisc(a.disc)
                rows = write_manifest(d, a.write_manifest)
                d.close()
                print('wrote %s (%d files)' % (a.write_manifest, len(rows)))
        else:
            ap.print_usage(sys.stderr)
            print('give a disc image or --extracted DIR', file=sys.stderr)
            return 2
    except VerifyError as e:
        print('error: %s' % e, file=sys.stderr)
        return 2
    print(res.text())
    print('(%.1f s)' % (time.time() - t0))
    return 0 if res.ok else 1


if __name__ == '__main__':
    sys.exit(main())
