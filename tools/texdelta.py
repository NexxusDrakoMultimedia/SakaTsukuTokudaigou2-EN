# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""texdelta - ship the repainted (English) textures as VCDIFF deltas against the player's own original textures.

The working form of a repainted texture is  translation/textures/<iso path>/<texture id>.pvr  (a full PVR file, mostly
Sega's pixels).  The public repository must not hold those pixels.  This tool turns each one into
l10n/textures/<same relative path>.vcdiff  = a VCDIFF (RFC 3284) delta of the repaint against the ORIGINAL texture
bytes, and turns the deltas back into the .pvr working files, using the original texture read out of the player's own
extracted disc (extracted/, made by tools/extract.py after tools/verify_source_disc.py accepted the disc).

    python -I -X utf8 tools/texdelta.py make     [--textures-dir D] [--extracted D] [--out DIR]
    python -I -X utf8 tools/texdelta.py apply    DELTA.vcdiff ORIGINAL.pvr OUT.pvr
    python -I -X utf8 tools/texdelta.py apply-all [--delta-dir D] [--extracted D] --out DIR
    python -I -X utf8 tools/texdelta.py verify   [--textures-dir D] [--extracted D] [--work DIR]
    python -I -X utf8 tools/texdelta.py stats    [--delta-dir D] [--extracted D]
    python -I -X utf8 tools/texdelta.py analyze  [--delta-dir D] [--extracted D]     # original-equal bytes inside the deltas

Format and legal reasoning: docs/texture-delta.md.  Pure standard library.

What a delta contains (see encode_delta): the target is walked once; every stretch that equals the source (at the same
offset, or at any other offset when it is at least MIN_FAR bytes long) is a COPY instruction (an address and a length, no
pixels); everything else is ADD (our new bytes) or RUN (one byte repeated).  Equal stretches of fewer than MIN_NEAR bytes
sit between two changes and are cheaper to add than to copy; they are the only original bytes that can end up in a delta
and `analyze` measures them.
"""
import argparse
import hashlib
import lzma
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import vcdiff as V        # noqa: E402
import texinject          # noqa: E402

MANIFEST = 'MANIFEST.tsv'
DELTA_EXT = '.vcdiff'
MIN_NEAR = 6        # an equal stretch at the same offset shorter than this is folded into the surrounding ADD
MIN_FAR = 10        # an equal stretch found at ANOTHER offset must be at least this long to become a COPY
MAX_CAND = 16       # candidate positions tried per 'far' lookup

DEF_TEXTURES = os.path.join(ROOT, 'translation', 'textures')
DEF_DELTAS = os.path.join(ROOT, 'l10n', 'textures')
DEF_EXTRACTED = os.path.join(ROOT, 'extracted')
DEF_WORK = os.path.join(ROOT, 'build', 'l10n_tex')


class TexDeltaError(Exception):
    pass


MAX_TARGET = 64 * 1024 * 1024     # a texture file is a few MB at most; a delta that claims more is damaged or hostile


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def write_atomic(path, data):
    """Write data to path through a temporary file in the same directory, then os.replace: a crash or Ctrl-C leaves
    the old file or no file, never a half-written one."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = '%s.tmp%d' % (path, os.getpid())
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def safe_rel(rel):
    """A manifest path must be a relative '/'-separated path below the output directory ending in .pvr."""
    parts = rel.split('/')
    if (not rel.lower().endswith('.pvr') or '\\' in rel or ':' in rel or rel.startswith('/') or
            any(p in ('', '.', '..') for p in parts)):
        raise TexDeltaError('unsafe or malformed path in the manifest: %r' % rel)
    return rel


# =============================================================== encoder / decoder
def _opcode_add(n):
    """Default code table: ADD with the size in the opcode (1..17) or ADD + varint size."""
    if 1 <= n <= 17:
        return bytes([1 + n])
    return bytes([V.ADD_SIZE0]) + V.put_int(n)


def _opcode_copy(n):
    """COPY, VCD_SELF addressing: size 4..18 in the opcode, else opcode 19 + varint size."""
    if 4 <= n <= 18:
        return bytes([19 + n - 3])
    return bytes([V.COPY_SELF_SIZE0]) + V.put_int(n)


def _literal(tgt, a, b, data, inst):
    """ADD tgt[a:b] (runs of one byte of at least RUN_MIN become RUN)."""
    cur = a
    if b - a >= V.RUN_MIN:
        for m in V._RUN.finditer(tgt, a, b):
            s, e = m.span()
            if s > cur:
                inst += _opcode_add(s - cur)
                data += tgt[cur:s]
            inst += bytes([V.RUN_SIZE0]) + V.put_int(e - s)
            data.append(tgt[s])
            cur = e
    if cur < b:
        inst += _opcode_add(b - cur)
        data += tgt[cur:b]


def _near_ranges(src, tgt):
    """[(a, b)] of tgt that differs from src at the same offset; equal gaps shorter than MIN_NEAR are folded in."""
    out = []
    n = len(tgt)
    common = min(len(src), n)

    def add(i, j):
        if out and i - out[-1][1] < MIN_NEAR:
            out[-1] = (out[-1][0], j)
        else:
            out.append((i, j))

    if common and src[:common] != tgt[:common]:
        V._diff(src, tgt, 0, common, add)
    if n > common:
        add(common, n)
    return out


class _Far:
    """Index of every MIN_FAR-byte substring of the source, for copies from another offset."""

    def __init__(self, src):
        self.src = src
        self.idx = {}
        for i in range(len(src) - MIN_FAR + 1):
            self.idx.setdefault(src[i:i + MIN_FAR], []).append(i)

    def best(self, tgt, p, end):
        cands = self.idx.get(tgt[p:p + MIN_FAR])
        if not cands:
            return None
        best = (0, 0)
        for c in cands[:MAX_CAND]:
            n = MIN_FAR
            while p + n < end and c + n < len(self.src) and tgt[p + n] == self.src[c + n]:
                n += 1
            if n > best[0]:
                best = (n, c)
        return best


def encode_delta(src, tgt, secondary=False):
    """VCDIFF (one window, source segment = the whole source, default code table, no checksum) that rebuilds tgt from
    src.  secondary=False: plain RFC 3284, readable by any decoder.  secondary=True: the ADD / instruction / address
    sections are xz-compressed as xdelta3's "-S lzma" does (flag VCD_DECOMPRESS, secondary id 2); xdelta3 and
    tools/vcdiff.py read it, a strictly RFC-only decoder does not."""
    src, tgt = bytes(src), bytes(tgt)
    data, inst, addr = bytearray(), bytearray(), bytearray()
    far = _Far(src) if src and len(tgt) > MIN_FAR else None
    pos = 0
    for a, b in _near_ranges(src, tgt):
        if a > pos:                                   # unchanged stretch at the same offset: COPY from src[pos:a]
            inst += _opcode_copy(a - pos)
            addr += V.put_int(pos)
        # inside the changed range: copy from elsewhere in the source wherever a long match exists
        p, lit = a, a
        while far is not None and p + MIN_FAR <= b:
            m = far.best(tgt, p, b)
            if m is None:
                p += 1
                continue
            n, c = m
            if p > lit:
                _literal(tgt, lit, p, data, inst)
            inst += _opcode_copy(n)
            addr += V.put_int(c)
            p += n
            lit = p
        if lit < b:
            _literal(tgt, lit, b, data, inst)
        pos = b
    if pos < len(tgt):
        inst += _opcode_copy(len(tgt) - pos)
        addr += V.put_int(pos)
    secs, flags = [bytes(data), bytes(inst), bytes(addr)], 0
    if secondary:
        import lzma
        for k, s in enumerate(secs):
            if len(s) < 16:
                continue                              # an empty section cannot be coded, a tiny one does not pay
            c = lzma.compress(s, format=lzma.FORMAT_XZ, check=lzma.CHECK_NONE, preset=9 | lzma.PRESET_EXTREME)
            # xdelta3 writes each section as an xz stream that is flushed, not finished (LZMA_SYNC_FLUSH) and its
            # decoder treats a stream end as an error: cut the xz index and footer off (stream footer = last 12
            # bytes, its backward-size field gives the index length), keeping header + block, which decode as is.
            index = (int.from_bytes(c[-8:-4], 'little') + 1) * 4
            c = V.put_int(len(s)) + c[:len(c) - 12 - index]
            if len(c) < len(s):
                secs[k], flags = c, flags | V.SECTION_BITS[k]
    body = (V.put_int(len(tgt)) + bytes([flags]) + V.put_int(len(secs[0])) + V.put_int(len(secs[1])) +
            V.put_int(len(secs[2])) + secs[0] + secs[1] + secs[2])
    head = bytes([V.VCD_SOURCE]) + V.put_int(len(src)) + V.put_int(0) if src else b'\x00'
    if flags:
        return V.MAGIC + bytes([V.VCD_DECOMPRESS, V.SEC_LZMA]) + head + V.put_int(len(body)) + body
    return V.MAGIC + b'\x00' + head + V.put_int(len(body)) + body


def decode_delta(delta, src):
    """Apply a VCDIFF made by encode_delta (or any plain single-source VCDIFF) to src; return the target bytes."""
    try:
        _, windows = V.parse(delta)
        out = bytearray()
        for w in windows:
            if w.indicator & V.VCD_TARGET:
                raise TexDeltaError('VCD_TARGET windows are not used by texture deltas')
            if w.tgt_len > MAX_TARGET or len(out) + w.tgt_len > MAX_TARGET:
                raise TexDeltaError('delta claims a result of %d bytes: damaged delta' % w.tgt_len)
            seg = b''
            if w.indicator & V.VCD_SOURCE:
                seg = bytes(src[w.seg_pos:w.seg_pos + w.seg_len])
                if len(seg) != w.seg_len:
                    raise TexDeltaError('original texture is shorter than the delta expects (wrong disc revision?)')
            out += V.decode_window(w, seg)
        return bytes(out)
    except TexDeltaError:
        raise
    except (ValueError, IndexError, EOFError, OverflowError, MemoryError, lzma.LZMAError) as e:
        # vcdiff.py and the xz decoder raise their own types on damaged input: always report them as ours
        raise TexDeltaError('damaged delta (%s: %s)' % (type(e).__name__, e))


# =============================================================== locating the original texture
def split_container(parts, extracted):
    """['ATFIRST', 'SHTEX0.ZAR', 'mon.tbd#0'] -> ('ATFIRST/SHTEX0.ZAR', 'mon.tbd#0'): the longest leading directory
    chain that names a file below extracted/ is the container, the rest is the texture id (same rule as
    texinject.load_textures_dir)."""
    for i in range(len(parts) - 1, 0, -1):
        if os.path.isfile(os.path.join(extracted, *parts[:i])):
            return '/'.join(parts[:i]), '/'.join(parts[i:])
    return None, None


class Originals:
    """Reads container files of the player's extracted disc once and extracts original textures from them."""

    def __init__(self, extracted):
        self.extracted = extracted
        self._cache = {}

    def container(self, cont):
        if cont not in self._cache:
            if len(self._cache) > 8:
                self._cache.clear()
            with open(os.path.join(self.extracted, *cont.split('/')), 'rb') as f:
                self._cache[cont] = f.read()
        return self._cache[cont]

    def texture(self, cont, tid):
        """The ORIGINAL texture as a PVR file (texinject.extract_pvr: a TBD record gets a synthesised GBIX+PVRT)."""
        return texinject.extract_pvr(self.container(cont), tid)


def _walk(root, ext):
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            if fn.lower().endswith(ext):
                yield os.path.join(dp, fn)


def _rel(full, root):
    return os.path.relpath(full, root).replace(os.sep, '/')


# =============================================================== make
def make(textures_dir=DEF_TEXTURES, extracted=DEF_EXTRACTED, out_dir=DEF_DELTAS, log=None, secondary=True):
    """For every repainted texture write <out_dir>/<rel>.vcdiff and the MANIFEST.tsv; return the manifest rows
    [(rel .pvr path, repaint sha256, original sha256, delta bytes)]."""
    orig = Originals(extracted)
    rows, problems = [], []
    for full in _walk(textures_dir, '.pvr'):
        rel = _rel(full, textures_dir)
        cont, tid = split_container(rel.split('/'), extracted)
        if cont is None:
            problems.append('%s: no container file in extracted/ matches' % rel)
            continue
        tid = tid[:-4]
        try:
            src = orig.texture(cont, tid)
        except (texinject.TexInjectError, OSError, KeyError, ValueError, IndexError) as e:
            problems.append('%s: original texture not found (%s: %s)' % (rel, type(e).__name__, e))
            continue
        with open(full, 'rb') as f:
            tgt = f.read()
        delta = encode_delta(src, tgt, secondary)
        if decode_delta(delta, src) != tgt:
            raise TexDeltaError('%s: internal round trip failed' % rel)
        dst = os.path.join(out_dir, *rel[:-4].split('/')) + DELTA_EXT
        write_atomic(dst, delta)
        rows.append((rel, sha256(tgt), sha256(src), len(delta)))
        if log:
            log('%-60s %6d -> %5d bytes' % (rel, len(tgt), len(delta)))
    write_manifest(os.path.join(out_dir, MANIFEST), rows)
    if not problems:
        _prune(out_dir, rows)
    if problems:
        raise TexDeltaError('%d texture(s) could not be processed:\n  ' % len(problems) + '\n  '.join(problems))
    return rows


def _prune(out_dir, rows):
    """Remove .vcdiff files below out_dir that no manifest row names (a texture that was deleted or renamed since an
    earlier make); a stale delta would otherwise ship with the next release."""
    keep = {os.path.normpath(os.path.join(out_dir, *r[0][:-4].split('/')) + DELTA_EXT) for r in rows}
    for full in list(_walk(out_dir, DELTA_EXT)):
        if os.path.normpath(full) not in keep:
            os.remove(full)
    for dp, dns, fns in os.walk(out_dir, topdown=False):
        if dp != out_dir and not os.listdir(dp):
            os.rmdir(dp)


def write_manifest(path, rows):
    text = ('# texdelta manifest (docs/texture-delta.md). Columns, tab separated:\n'
            '# path (working file below translation/textures/) | sha256 of the repainted PVR | '
            'sha256 of the ORIGINAL texture (PVR bytes as tools/texinject.py extract_pvr gives them) | delta bytes\n')
    text += ''.join('%s\t%s\t%s\t%d\n' % r for r in sorted(rows))
    write_atomic(path, text.encode('utf-8'))


def read_manifest(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            p = line.split('\t')
            if len(p) != 4 or len(p[1]) != 64 or len(p[2]) != 64:
                raise TexDeltaError('%s:%d: malformed manifest line' % (path, n))
            try:
                n_bytes = int(p[3])
            except ValueError:
                raise TexDeltaError('%s:%d: malformed manifest line' % (path, n))
            rows.append((safe_rel(p[0]), p[1], p[2], n_bytes))
    if len({r[0] for r in rows}) != len(rows):
        raise TexDeltaError('%s: a path is listed twice' % path)
    return rows


# =============================================================== apply
def apply_bytes(delta, original, want_repaint_sha=None, want_original_sha=None, what=''):
    """delta + original texture bytes -> repainted PVR bytes, with the manifest checks."""
    if want_original_sha and sha256(original) != want_original_sha:
        raise TexDeltaError('%s: original texture differs from the one the patch was made for (other disc revision or '
                            'damaged dump): sha256 %s, expected %s' % (what, sha256(original)[:16], want_original_sha[:16]))
    out = decode_delta(delta, original)
    if want_repaint_sha and sha256(out) != want_repaint_sha:
        raise TexDeltaError('%s: result differs from the shipped repaint (sha256 %s, expected %s)'
                            % (what, sha256(out)[:16], want_repaint_sha[:16]))
    return out


def apply_all(delta_dir=DEF_DELTAS, extracted_dir=DEF_EXTRACTED, out_dir=DEF_WORK, log=None):
    """Rebuild every .pvr working file below out_dir from the deltas and the player's extracted disc.
    Returns (written paths, problems); every failing texture is named in problems, nothing is skipped silently."""
    orig = Originals(extracted_dir)
    rows = read_manifest(os.path.join(delta_dir, MANIFEST))
    done, problems = [], []
    for rel, want_out, want_in, _ in rows:
        dpath = os.path.join(delta_dir, *rel[:-4].split('/')) + DELTA_EXT
        cont, tid = split_container(rel.split('/'), extracted_dir)
        if cont is None:
            problems.append('%s: container file not found in the extracted disc' % rel)
            continue
        try:
            with open(dpath, 'rb') as f:
                delta = f.read()
            src = orig.texture(cont, tid[:-4])
            out = apply_bytes(delta, src, want_out, want_in, rel)
        except (TexDeltaError, texinject.TexInjectError, OSError, ValueError, KeyError, IndexError) as e:
            msg = str(e) if isinstance(e, TexDeltaError) else '%s: %s' % (type(e).__name__, e)
            problems.append(msg if msg.startswith(rel + ':') else '%s: %s' % (rel, msg))
            continue
        write_atomic(os.path.join(out_dir, *rel.split('/')), out)
        done.append(rel)
        if log:
            log('ok %s' % rel)
    listed = {os.path.normpath(os.path.join(delta_dir, *r[0][:-4].split('/')) + DELTA_EXT) for r in rows}
    for full in _walk(delta_dir, DELTA_EXT):
        if os.path.normpath(full) not in listed:
            problems.append('%s: delta file is not listed in %s (stale or foreign file; it was not applied)'
                            % (_rel(full, delta_dir), MANIFEST))
    return done, problems


# =============================================================== verify / stats / analyze
def verify(textures_dir=DEF_TEXTURES, extracted=DEF_EXTRACTED, work=DEF_WORK, log=None):
    """make -> apply_all into work/{delta,pvr}, then compare every rebuilt file byte for byte with textures_dir.
    Reads textures_dir only; writes below work.  Returns (count, problems)."""
    ddir, pdir = os.path.join(work, 'delta'), os.path.join(work, 'pvr')
    rows = make(textures_dir, extracted, ddir)
    done, problems = apply_all(ddir, extracted, pdir)
    problems = list(problems)
    for rel in done:
        with open(os.path.join(pdir, *rel.split('/')), 'rb') as a, open(os.path.join(textures_dir, *rel.split('/')), 'rb') as b:
            if a.read() != b.read():
                problems.append('%s: rebuilt file differs from the working file' % rel)
    have = {r[0] for r in rows}
    for full in _walk(textures_dir, '.pvr'):
        if _rel(full, textures_dir) not in have:
            problems.append('%s: no delta made' % _rel(full, textures_dir))
    return len(rows), problems


def stats(delta_dir=DEF_DELTAS):
    rows = read_manifest(os.path.join(delta_dir, MANIFEST))
    sizes = sorted(r[3] for r in rows)
    on_disk = sum(os.path.getsize(os.path.join(delta_dir, *r[0][:-4].split('/')) + DELTA_EXT) for r in rows)
    n = len(sizes)
    return dict(count=n, total=sum(sizes), on_disk=on_disk, smallest=sizes[0] if n else 0,
                median=sizes[n // 2] if n else 0, largest=sizes[-1] if n else 0)


def delta_pieces(delta):
    """[(kind, bytes_or_len)] of the instructions of one delta (kind 'add' with the bytes, 'run' with the length, 'copy' with the length)."""
    _, wins = V.parse(delta)
    pieces = []
    for w in wins:
        data, inst, addr = V.Reader(w.data), V.Reader(w.inst), V.Reader(w.addr)
        while inst.pos < len(w.inst):
            code = V.CODE_TABLE[inst.byte()]
            for kind, size, mode in (code[0:3], code[3:6]):
                if kind == V.NOOP:
                    continue
                if size == 0:
                    size = inst.int()
                if kind == V.ADD:
                    pieces.append(('add', data.take(size)))
                elif kind == V.RUN:
                    data.byte()
                    pieces.append(('run', size))
                else:
                    if mode != 0:
                        raise TexDeltaError('unexpected COPY address mode %d' % mode)
                    addr.int()
                    pieces.append(('copy', size))
    return pieces


def gram_index(src, k=4):
    idx = {}
    for i in range(len(src) - k + 1):
        idx.setdefault(src[i:i + k], []).append(i)
    return idx


def longest_common_run(piece, src, idx=None, cap=64):
    """Length of the longest substring of `piece` that also occurs in `src` (anywhere).  Candidate start offsets come
    from a 4-byte index; a 4-gram with more than `cap` occurrences (zero fill, flat colour) is checked at `cap`
    positions, so the result is exact except inside such degenerate runs, where it is a lower bound."""
    idx = idx if idx is not None else gram_index(src)
    best = 0
    for i in range(len(piece) - 3):
        if len(piece) - i <= best:
            break
        cands = idx.get(piece[i:i + 4])
        if not cands:
            continue
        for c in cands[:cap]:
            n = 4
            lim = min(len(piece) - i, len(src) - c)
            while n < lim and piece[i + n] == src[c + n]:
                n += 1
            if n > best:
                best = n
    return best


def analyze(delta_dir=DEF_DELTAS, extracted=DEF_EXTRACTED, log=None):
    """For every delta: the ADD bytes that equal original bytes. Returns a dict with the largest run of
    original-equal bytes stored in any ADD instruction, the per-delta numbers and the distribution."""
    orig = Originals(extracted)
    rows = read_manifest(os.path.join(delta_dir, MANIFEST))
    res = []
    for rel, _, _, _ in rows:
        cont, tid = split_container(rel.split('/'), extracted)
        src = orig.texture(cont, tid[:-4])
        with open(os.path.join(delta_dir, *rel[:-4].split('/')) + DELTA_EXT, 'rb') as f:
            delta = f.read()
        pcs = delta_pieces(delta)
        add_total = sum(len(p[1]) for p in pcs if p[0] == 'add')
        run_total = sum(p[1] for p in pcs if p[0] == 'run')
        copy_total = sum(p[1] for p in pcs if p[0] == 'copy')
        longest = 0
        idx = gram_index(src) if add_total else None
        eq_at_same = 0       # ADD bytes equal to the original byte at the position the ADD rebuilds
        pos = 0
        for kind, v in pcs:
            if kind == 'add':
                longest = max(longest, longest_common_run(v, src, idx))
                eq_at_same += sum(1 for k in range(len(v)) if pos + k < len(src) and v[k] == src[pos + k])
                pos += len(v)
            else:
                pos += v
        hdr = texinject.parse_pvr(src)
        res.append(dict(rel=rel, fmt=hdr.fmt, dt=hdr.dt, payload=len(hdr.payload), add=add_total, run=run_total, copy=copy_total, longest=longest, equal_same=eq_at_same,
                        n_add=sum(1 for p in pcs if p[0] == 'add'), size=len(delta)))
        if log:
            log('%-56s add=%5d copy=%5d longest-original-run=%3d' % (rel, add_total, copy_total, longest))
    return res


# =============================================================== command line
def _log(s):
    print(s, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('make')
    p.add_argument('--textures-dir', default=DEF_TEXTURES)
    p.add_argument('--extracted', default=DEF_EXTRACTED)
    p.add_argument('--out', default=DEF_DELTAS)
    p.add_argument('--plain', action='store_true', help='no LZMA secondary compression (plain RFC 3284, larger)')
    p = sub.add_parser('apply')
    p.add_argument('delta')
    p.add_argument('original')
    p.add_argument('out')
    p = sub.add_parser('apply-all')
    p.add_argument('--delta-dir', default=DEF_DELTAS)
    p.add_argument('--extracted', default=DEF_EXTRACTED)
    p.add_argument('--out', required=True)
    p = sub.add_parser('verify')
    p.add_argument('--textures-dir', default=DEF_TEXTURES)
    p.add_argument('--extracted', default=DEF_EXTRACTED)
    p.add_argument('--work', default=DEF_WORK)
    for name in ('stats', 'analyze'):
        p = sub.add_parser(name)
        p.add_argument('--delta-dir', default=DEF_DELTAS)
        p.add_argument('--extracted', default=DEF_EXTRACTED)
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.cmd == 'make':
        rows = make(a.textures_dir, a.extracted, a.out, _log, not a.plain)
        _log('%d deltas, %d bytes, manifest %s' % (len(rows), sum(r[3] for r in rows), os.path.join(a.out, MANIFEST)))
    elif a.cmd == 'apply':
        with open(a.delta, 'rb') as f:
            d = f.read()
        with open(a.original, 'rb') as f:
            o = f.read()
        out = apply_bytes(d, o, what=a.delta)
        write_atomic(a.out, out)
        _log('wrote %s (%d bytes, sha256 %s)' % (a.out, len(out), sha256(out)))
    elif a.cmd == 'apply-all':
        done, problems = apply_all(a.delta_dir, a.extracted, a.out)
        for pr in problems:
            _log('MISMATCH ' + pr)
        _log('%d textures rebuilt, %d problems' % (len(done), len(problems)))
        return 1 if problems else 0
    elif a.cmd == 'verify':
        n, problems = verify(a.textures_dir, a.extracted, a.work)
        for pr in problems:
            _log('PROBLEM ' + pr)
        _log('%d textures round-tripped, %d problems (%.0fs)' % (n, len(problems), time.time() - t0))
        return 1 if problems else 0
    elif a.cmd == 'stats':
        s = stats(a.delta_dir)
        _log('deltas %(count)d  total %(total)d bytes (files on disk %(on_disk)d)  smallest %(smallest)d  median %(median)d  largest %(largest)d' % s)
    elif a.cmd == 'analyze':
        res = analyze(a.delta_dir, a.extracted)
        top = sorted(res, key=lambda r: -r['longest'])[:10]
        _log('largest run of original-equal bytes in any ADD: %d' % top[0]['longest'])
        for r in top:
            _log('  %-56s longest=%d add=%d copy=%d' % (r['rel'], r['longest'], r['add'], r['copy']))
        _log('ADD bytes total %d, RUN bytes %d, COPY bytes %d' % (sum(r['add'] for r in res), sum(r['run'] for r in res), sum(r['copy'] for r in res)))
        _log('ADD bytes equal to the original at the same offset: %d' % sum(r['equal_same'] for r in res))
        by = {}
        for r in res:
            k = (r['fmt'], r['dt'])
            e = by.setdefault(k, [0, 0, 0, 0])
            e[0] += 1
            e[1] += r['payload']
            e[2] += r['add']
            e[3] += r['size']
        _log('by pixel format / data type: textures, payload bytes, ADD bytes, delta bytes')
        for k in sorted(by):
            _log('  fmt %d dt %#04x  %4d textures  payload %9d  add %9d (%4.1f%%)  delta %9d' % (
                k[0], k[1], by[k][0], by[k][1], by[k][2], 100.0 * by[k][2] / by[k][1], by[k][3]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
