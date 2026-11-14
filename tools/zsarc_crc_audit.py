# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""zsarc_crc_audit: read-only audit of every ZSARC member of a BUILT disc image (stale member CRCs).

    python -I -X utf8 tools/zsarc_crc_audit.py DISC [--all] [--originals DIR] [--quiet]

DISC is a .gdi / .cue (raw 2352-byte tracks, as written by tools/build_patch.py) or a volume .iso (2048-byte sectors, LBA 45000 at sector 0).

Why: the game's member walker (FUN_8c15a45a and its callers) rejects a ZSARC member whose header CRC or payload CRC16 does not match; a texture or text edit
that rewrites bytes inside a stored (-nc--) or packed member without rebuilding the header leaves a STALE member, and the game hangs or skips the file
(docs/scdrf-texture-hang.md).  The build guards this when it injects (texinject.stale_stored_members); this tool checks the finished DISC, whatever made it.

What it checks, for every file of the disc that differs from its original in extracted/ (default) or for every file (--all):
  * the member offsets come from the ORIGINAL file (every CRC-valid ZSARC header found by texinject.scan_run_starts: the container chain AND the runs embedded
    in blobs such as GAME/GAMEETC.ZAR and ATFIRST/FACEMDUL.DAT); a file that is not in extracted/ (added to the disc) is audited with its own chain instead;
  * at each such offset of the built file: a member header must still parse, its header CRC (bzlib.header_crc over the header with the CRC bytes zeroed) must
    be right, and the CRC16 of the decoded payload (bzlib.decompress; for -nc-- members the bytes themselves) must equal the stored crc16.
A member that already fails the same check in the ORIGINAL file is counted as "bad in the original" and is not a regression.  A member whose header
no longer parses at its original offset is reported as MOVED (a grown or relocated container; the chain walk of the built file then covers it).
Exit code: 0 = no stale member, 1 = at least one regression, 2 = usage / unreadable disc.  Nothing is written.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bzlib                  # noqa: E402
import discbuild as D         # noqa: E402
import discformat as DF       # noqa: E402
import texinject              # noqa: E402

USER = 2048
SS = 2352


class TrackSource:
    """LBA -> user data for a .gdi / .cue disc (the layout constants of discbuild.TRACK_LBA)."""

    def __init__(self, disc):
        self.fh = {t: open(p, 'rb') for t, p in disc.tracks.items()}
        self.nsec = {t: os.path.getsize(p) // SS for t, p in disc.tracks.items()}

    def close(self):
        for f in self.fh.values():
            f.close()

    def read(self, lba, size):
        out = bytearray()
        for i in range((size + USER - 1) // USER):
            for t, l in D.TRACK_LBA.items():
                if l <= lba + i < l + self.nsec[t]:
                    self.fh[t].seek((lba + i - l) * SS)
                    out += self.fh[t].read(SS)[16:16 + USER]
                    break
            else:
                raise IndexError('LBA %d is outside the tracks' % (lba + i))
        return bytes(out[:size])


class IsoSource:
    """LBA -> user data for a volume .iso (sector k = LBA 45000 + k)."""

    def __init__(self, path):
        self.f = open(path, 'rb')

    def close(self):
        self.f.close()

    def read(self, lba, size):
        self.f.seek((lba - D.HD_BASE) * USER)
        return self.f.read(size + (-size) % USER)[:size]


def open_source(path):
    disc = DF.open_disc(path)
    return IsoSource(disc.iso) if disc.kind == 'iso' else TrackSource(disc)


def member_state(d, off):
    """-> (state, name): 'ok' | 'nohdr' | 'hdrcrc' | 'payload' | 'decode'"""
    m = bzlib.parse_member(d, off, with_data=False)
    if m is None:
        return 'nohdr', None
    if m.hdr_crc_ok is False:
        return 'hdrcrc', m.name
    try:
        plain = bzlib.decompress(bytes(d[m.data_offset:m.end_offset]), m.orig_size, m.method)
    except Exception:       # noqa: BLE001  (bzlib.DecodeError, short data ...)
        return 'decode', m.name
    if len(plain) != m.orig_size or bzlib.crc16(plain) != m.crc16:
        return 'payload', m.name
    return 'ok', m.name


def own_offsets(d):
    """member offsets of a file with no original: the chain from offset 0 plus every CRC-valid header (texinject.scan_run_starts)"""
    offs = set(texinject.scan_run_starts(d, 0))
    o = 0
    while o < len(d):
        while o < len(d) and d[o] == 0:
            o += 1
        m = bzlib.parse_member(d, o, with_data=False) if o < len(d) else None
        if m is None:
            break
        offs.add(m.offset)
        o = m.end_offset
    return sorted(offs)


def audit(src, originals, everything=False, quiet=False, out=sys.stdout):
    """-> dict(files, members, stale: [(path, offset, name, state)], bad_orig, moved, skipped)"""
    _pvd, _rl, _rs, recs = D.read_filesystem(src)
    res = dict(files=0, members=0, stale=[], bad_orig=[], moved=[], same=0, nozsarc=0)
    for r in sorted((x for x in recs if not x.isdir), key=lambda x: x.path):
        p = r.path
        built = src.read(r.lba, r.size)
        op = os.path.join(originals, *p.lstrip('/').split('/'))
        orig = None
        if os.path.exists(op):
            with open(op, 'rb') as f:
                orig = f.read()
            if orig == built and not everything:
                res['same'] += 1
                continue
        ref = orig if orig is not None else built      # a built file that LOST every member marker must still be audited (reported as MOVED)
        if len(built) < 28 or (b'-nc--' not in ref and b'-bz--' not in ref and b'-bzw-' not in ref):
            res['nozsarc'] += 1
            continue
        offs = texinject.scan_run_starts(orig, 0) if orig is not None else own_offsets(built)
        if not offs:
            res['nozsarc'] += 1
            continue
        res['files'] += 1
        for off in offs:
            res['members'] += 1
            st, name = member_state(built, off)
            if st == 'ok':
                continue
            if orig is not None:
                st0, _ = member_state(orig, off)
                if st0 != 'ok':
                    res['bad_orig'].append((p, off, name, st))
                    continue
            if st == 'nohdr':
                res['moved'].append((p, off, name, st))
            else:
                res['stale'].append((p, off, name, st))
                if not quiet:
                    print('STALE %-30s @%#08x %-20s %s' % (p, off, name, {'hdrcrc': 'header CRC wrong', 'payload': 'payload CRC16 / size wrong',
                                                                     'decode': 'payload does not decode'}[st]), file=out)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('disc', help='.gdi / .cue / volume .iso')
    ap.add_argument('--all', action='store_true', help='audit every file, not only those that differ from extracted/')
    ap.add_argument('--originals', default=os.path.join(ROOT, 'extracted'), help='the original files (default extracted/)')
    ap.add_argument('--quiet', action='store_true', help='print only the totals')
    a = ap.parse_args(argv)
    try:
        src = open_source(a.disc)
    except (DF.DiscError, OSError) as e:
        print('ERROR: %s' % e, file=sys.stderr)
        return 2
    try:
        res = audit(src, a.originals, a.all, a.quiet)
    except (IndexError, AssertionError, struct.error) as e:
        print('ERROR: cannot read the ISO9660 volume of %s (%s)' % (a.disc, e), file=sys.stderr)
        return 2
    finally:
        src.close()
    for p, off, name, st in res['moved']:
        print('MOVED %-30s @%#08x %s (no member header at the original offset: grown / relocated container)' % (p, off, name))
    print('zsarc_crc_audit %s: %d file(s) with ZSARC members audited (%d identical to the original skipped, %d without ZSARC), %d member(s): '
          '%d STALE, %d bad in the original too, %d moved' % (os.path.basename(a.disc), res['files'], res['same'], res['nozsarc'], res['members'],
                                                              len(res['stale']), len(res['bad_orig']), len(res['moved'])))
    return 1 if res['stale'] else 0


if __name__ == '__main__':
    sys.exit(main())
