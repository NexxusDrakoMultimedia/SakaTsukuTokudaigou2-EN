"""pvr_scan - inventory every Dreamcast texture on the disc (read-only).

Usage (repo root):
    python -I -X utf8 tools/pvr_scan.py [--src extracted] [--out build/textures/inventory.tsv]

Walks extracted/, decodes ZSARC containers in memory (tools/bzlib.py), recurses into members,
container tails, CRC-valid embedded records, "ARC" file archives and texture tables found at
any 4-byte aligned offset of an otherwise unclassified blob, and records every texture it can prove
is one.  Texture carriers (see docs/textures.md):

  PVR     GBIX+PVRT (or bare PVRT) file / member; PVPL palette files ("PVP")
  TBD     "texture bundle" table: u32 count, count * 16-byte records
          {u8 pix, u8 dat, u8 0, u8 flags (0x80 bz, 0x40 bzw, 0 stored), u16 w, u16 h, u32 offset, u32 id},
          offsets relative to the table start, data = raw pixel payload (no PVRT header), each entry
          compressed on its own.  Found as members/files named *.tbd/*.dat, as the unparsed tail of *.ZAR
          files ("TBD-tail"), inside FACE/*DATA.BIN and ESTABLIS.ARC entries ("TBD-embedded").
  PVR-embedded  a PVRT chunk found inside another blob

Library use:  Scanner(on_texture=callback).walk(path, bytes)   -> callback(Tex) per texture.
extracted/ is only read.
"""
import os
import sys
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bzlib  # noqa: E402
import pvr    # noqa: E402

import numpy as np  # noqa: E402

KNOWN_PIX = {0, 1, 2, 3, 4, 5, 6}
KNOWN_DAT = {1, 2, 3, 4, 5, 6, 7, 8, 9, 0xA, 0xB, 0xD, 0x10, 0x11, 0x12}
SKIP = {'BCAST.BIN', '_filelist.tsv'}
_DAT_OK = np.zeros(256, bool)
for _d in KNOWN_DAT:
    _DAT_OK[_d] = True


def is_pow2(x):
    return x > 0 and (x & (x - 1)) == 0


class Tex:
    """One texture found on the disc."""
    __slots__ = ('path', 'kind', 'index', 'pix', 'dat', 'w', 'h', 'payload', 'blob', 'stored', 'ident', 'method',
                 'expected', 'note', 'dsize')

    def tsv(self):
        return '\t'.join(str(x) for x in (self.path, self.kind, self.index, self.pix, self.dat, self.w, self.h,
                                          self.stored, self.dsize,
                                          self.expected, self.ident, self.method, self.note))


HEAD = ['path', 'kind', 'index', 'pix', 'dat', 'w', 'h', 'stored', 'dsize', 'expected', 'ident', 'method', 'note']


def parse_pvrt_at(data, o):
    if data[o:o + 4] != b'PVRT' or o + 16 > len(data):
        return None
    size, pix, dat, _pad, w, h = struct.unpack_from('<IBBHHH', data, o + 4)
    if pix not in KNOWN_PIX or dat not in KNOWN_DAT or w == 0 or h == 0 or w > 2048 or h > 2048:
        return None
    return dict(size=size, pix=pix, dat=dat, w=w, h=h, data_off=o + 16)


def parse_tbd(data, base=0, strict=True):
    """Parse a texture bundle table at data[base:].  Returns list of record dicts or None.
    strict: first data offset must be 4 + 16 * count (true for every bundle on the disc)."""
    n = len(data) - base
    if n < 20:
        return None
    cnt = struct.unpack_from('<I', data, base)[0]
    if cnt == 0 or cnt > 1024 or 4 + 16 * cnt > n:
        return None
    recs = []
    prev = 4 + 16 * cnt
    for i in range(cnt):
        b0, b1, b2, b3, w, h, off, ident = struct.unpack_from('<BBBBHHII', data, base + 4 + 16 * i)
        if b0 not in KNOWN_PIX or b1 not in KNOWN_DAT or b2 != 0 or b3 not in (0, 0x40, 0x80):
            return None
        if w == 0 or h == 0 or w > 2048 or h > 2048 or off < prev or off > n:
            return None
        if strict and i == 0 and off != 4 + 16 * cnt:
            return None
        prev = off
        recs.append(dict(index=i, pix=b0, dat=b1, flags=b3, w=w, h=h, offset=off, ident=ident))
    return recs


def find_tbd_candidates(data):
    """Aligned offsets that start something that looks like a texture table header (fast numpy filter)."""
    n4 = len(data) // 4
    if n4 < 6:
        return []
    u = np.frombuffer(data, '<u4', n4)
    cnt = u[:-1]
    rec = u[1:]
    ok = (cnt >= 1) & (cnt <= 1024)
    ok &= ((rec & 0xFF) <= 6) & ((rec >> 16) & 0xFF == 0)
    ok &= _DAT_OK[(rec >> 8) & 0xFF]
    b3 = rec >> 24
    ok &= (b3 == 0) | (b3 == 0x40) | (b3 == 0x80)
    return [int(i) * 4 for i in np.nonzero(ok)[0]]


def tbd_entries(data, base, recs):
    """Yield (rec, payload bytes | None, stored_len, method, err)."""
    n = len(data)
    for i, r in enumerate(recs):
        start = base + r['offset']
        end = base + recs[i + 1]['offset'] if i + 1 < len(recs) else n
        fl = r['flags']
        try:
            if fl == 0x80:
                plain, method = bzlib.decompress_bz(data[start:end], None), 'bz'
            elif fl == 0x40:
                plain, method = bzlib.decompress_bzw(data[start:end], None), 'bzw'
            else:
                method = 'raw'
                try:
                    need = pvr.data_size(r['pix'], r['dat'], r['w'], r['h'])
                except pvr.PVRError:
                    need = end - start
                plain = bytes(data[start:min(end, start + need)])
            err = None
        except Exception as e:  # noqa
            plain, method, err = None, {0x80: 'bz', 0x40: 'bzw', 0: 'raw'}[fl], str(e)
        yield r, plain, end - start, method, err


def parse_arc(data):
    """ETC_DATA/ESTABLIS.ARC style archive: u32 count, then count * (name NUL, u32 offset, u32 size).
    Returns [(name, offset, size)] or None."""
    if len(data) < 16:
        return None
    cnt = struct.unpack_from('<I', data, 0)[0]
    if cnt == 0 or cnt > 4096:
        return None
    o = 4
    out = []
    for _ in range(cnt):
        z = data.find(b'\0', o, o + 128)
        if z <= o:
            return None
        name = data[o:z]
        if not all(32 <= c < 127 for c in name) or z + 9 > len(data):
            return None
        off, size = struct.unpack_from('<II', data, z + 1)
        if off + size > len(data):
            return None
        out.append((name.decode('ascii'), off, size))
        o = z + 9
    return out


class Scanner:
    def __init__(self, on_texture=None, keep_rows=True):
        self.rows = []
        self.on_texture = on_texture
        self.keep_rows = keep_rows
        self.problems = []
        self.carriers = collections.Counter()     # kind -> textures

    def emit(self, path, kind, index, pix, dat, w, h, payload, blob, stored, ident, method, note=''):
        t = Tex()
        t.path, t.kind, t.index, t.pix, t.dat, t.w, t.h = path, kind, index, pix, dat, w, h
        t.payload, t.blob, t.stored, t.ident, t.method, t.note = payload, blob, stored, ident, method, note
        t.dsize = -1 if payload is None else len(payload)
        try:
            t.expected = pvr.data_size(pix, dat, w, h) if kind != 'PVP' else -1
        except pvr.PVRError:
            t.expected = -2
        self.carriers[kind] += 1
        if self.keep_rows:
            self.rows.append(t)
        if self.on_texture is not None:
            self.on_texture(t)
        if self.keep_rows:
            t.payload = None if kind != 'PVP' else t.payload   # do not hold the pixel data
            t.blob = None

    # ------------------------------------------------------------------
    def handle_tbd(self, path, data, base, kind):
        recs = parse_tbd(data, base)
        if recs is None:
            return False
        for r, plain, stored, method, err in tbd_entries(data, base, recs):
            if err:
                self.problems.append((path, r['index'], err))
            self.emit(path, kind, r['index'], r['pix'], r['dat'], r['w'], r['h'], plain, None, stored,
                      '%08x' % r['ident'], method, err or '')
        return True

    def walk(self, path, data, depth=0):
        """Examine one blob; True if it contributed textures."""
        found = False
        data = bytes(data)
        h4 = data[:4]
        if h4 in (b'GBIX', b'PVRT'):
            f = pvr.parse_file(data)
            if f is not None:
                self.emit(path, 'PVR', 0, f.pix, f.dat, f.w, f.h, data[f.data_off:f.data_off + f.data_len], data,
                          len(data), '%08x' % (f.gbix or 0), 'file', 'gbix' if f.gbix is not None else 'nogbix')
                return True
        if h4 == b'PVPL':
            ne = struct.unpack_from('<H', data, 14)[0]
            self.emit(path, 'PVP', 0, data[8], 0, ne, 1, data, data, len(data), '', 'file', 'palette')
            return True
        first = bzlib.parse_member(data, 0, with_data=False) if len(data) > 28 else None
        if first is not None:
            members, tail = bzlib.parse_archive(data)
            for idx, m in enumerate(members):
                try:
                    plain = m.extract()
                except Exception as e:  # noqa
                    self.problems.append((path, m.offset, 'member %s: %s' % (m.name, e)))
                    continue
                if self.walk('%s/%s' % (path, m.name), plain, depth + 1):
                    found = True
            if tail != len(data):
                if self.handle_tbd(path + '/@tail', data, tail, 'TBD-tail'):
                    found = True
                else:
                    found |= self.embedded(path, data, tail, depth)
            return found
        if self.handle_tbd(path, data, 0, 'TBD'):
            return True
        if path.upper().endswith('.ARC'):
            ents = parse_arc(data)
            if ents:
                for name, off, size in ents:
                    if self.walk('%s/%s' % (path, name), data[off:off + size], depth + 1):
                        found = True
                return found
        # tables at aligned offsets (FACE/*DATA.BIN, overlays, ...)
        covered = -1
        for o in find_tbd_candidates(data):
            if o < covered:
                continue
            recs = parse_tbd(data, o)
            if recs is None:
                continue
            if self.handle_tbd('%s@%x' % (path, o), data, o, 'TBD-embedded'):
                found = True
                covered = o + 4 + 16 * len(recs)
        # PVRT chunks anywhere
        o = data.find(b'PVRT')
        while o != -1:
            gb = o - 16 if o >= 16 and data[o - 16:o - 12] == b'GBIX' else None
            f = pvr.parse_file(data[gb:]) if gb is not None else pvr.parse_file(data[o:])
            if f is not None and parse_pvrt_at(data, o):
                base = gb if gb is not None else o
                self.emit('%s@%x' % (path, base), 'PVR-embedded', 0, f.pix, f.dat, f.w, f.h,
                          data[base + f.data_off:base + f.data_off + f.data_len], data[base:base + f.data_off + f.data_len],
                          f.data_off + f.data_len, '%08x' % (f.gbix or 0), 'raw', '')
                found = True
            o = data.find(b'PVRT', o + 4)
        if depth == 0:
            found |= self.embedded(path, data, 0, depth)
        return found

    def embedded(self, path, data, start, depth):
        import unpack_all
        found = False
        for o, ms in unpack_all.embedded_runs(data, start):
            for m in ms:
                try:
                    plain = m.extract()
                except Exception as e:  # noqa
                    self.problems.append((path, m.offset, 'embedded %s: %s' % (m.name, e)))
                    continue
                if self.walk('%s/@%x/%s' % (path, o, m.name), plain, depth + 1):
                    found = True
        return found


def iter_files(src):
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for fn in sorted(files):
            if fn in SKIP or fn.upper() == 'BCAST.BIN':
                continue
            p = os.path.join(root, fn)
            yield os.path.relpath(p, src).replace('\\', '/'), p


def scan_all(src='extracted', on_texture=None, keep_rows=True, only=None):
    """Scan every file; returns (Scanner, no_texture_files)."""
    sc = Scanner(on_texture, keep_rows)
    notex = []
    for rel, p in iter_files(src):
        if only and not any(s in rel for s in only):
            continue
        with open(p, 'rb') as f:
            data = f.read()
        if not sc.walk(rel, data):
            notex.append((rel, len(data)))
    return sc, notex


def main(argv):
    src = 'extracted'
    out = os.path.join('build', 'textures', 'inventory.tsv')
    it = iter(argv)
    for a in it:
        if a == '--src':
            src = next(it)
        elif a == '--out':
            out = next(it)
        else:
            print('unknown arg', a)
            return 2
    sc, notex = scan_all(src)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\t'.join(HEAD) + '\n')
        for r in sc.rows:
            f.write(r.tsv() + '\n')
    print('texture rows:', len(sc.rows))
    for k, v in sorted(sc.carriers.items()):
        print('  %-14s %d' % (k, v))
    print('problems:', len(sc.problems))
    for p in sc.problems[:20]:
        print('  PROBLEM', p)
    bad = [r for r in sc.rows if r.kind != 'PVP' and r.payload is None]
    print('files with no texture found:', len(notex))
    by = collections.defaultdict(list)
    for rel, n in notex:
        by[rel.split('/')[0] if '/' in rel else '.'].append((rel, n))
    for d, l in sorted(by.items()):
        print('  %-10s %4d files, %10d bytes' % (d, len(l), sum(n for _, n in l)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
