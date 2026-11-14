"""Census of every place in extracted/ that holds PowerVR textures, by container kind.

    python -I -X utf8 tools/re/texinject/census.py [--out tools/re/texinject/census.tsv]

Kinds (file level):
  pvr      file starts with GBIX/PVRT
  tbd      file is a texture bundle (u32 count, 16-byte records, first offset == 4+16*count)
  zsarc    member archive at offset 0; per member: pvr / tbd / other (plain text taken from build/unpacked)
  other    none of the above; scanned for (a) TBD-shaped tables at 4-aligned offsets (numpy), (b) GBIX/PVRT magics
Writes one row per (file, sub-kind) with counts, and prints a summary.  Read-only on extracted/ and build/unpacked/.
"""
import os
import sys
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 're', 'datatext'))
import bzlib      # noqa: E402
import pvr        # noqa: E402

try:
    import numpy as np
except ImportError:
    np = None

SKIP = {'BCAST.BIN', '_filelist.tsv'}


def tbd_ok(d, base=0):
    """Strict structural check of a TBD at d[base:]: returns record count or 0."""
    if len(d) - base < 20:
        return 0
    n = struct.unpack_from('<I', d, base)[0]
    if not 0 < n < 4096 or base + 4 + 16 * n > len(d):
        return 0
    prev = 4 + 16 * n
    for i in range(n):
        f, wh, off, st = struct.unpack_from('<IIII', d, base + 4 + 16 * i)
        w, h = wh & 0xffff, wh >> 16
        if (f & 0xff) > 6 or w == 0 or h == 0 or w > 2048 or h > 2048:
            return 0
        if i == 0 and off != prev:
            return 0
        if off < prev or base + off > len(d):
            return 0
        prev = off
    return n


def scan_tbd_tables(d, start=0):
    """4-aligned offsets >= start where a TBD-shaped table starts (numpy vectorised pre-filter)."""
    if np is None or len(d) < 24:
        return []
    n4 = (len(d) - start) // 4
    a = np.frombuffer(d, dtype='<u4', count=n4, offset=start)
    cnt = a[:-4]
    cand = np.nonzero((cnt > 0) & (cnt < 4096) & (a[3:-1] == 4 + 16 * cnt.astype(np.uint64).astype(np.uint32)))[0]
    out = []
    for i in cand:
        p = start + int(i) * 4
        if tbd_ok(d, p):
            out.append(p)
    return out


def main(argv):
    out = os.path.join(HERE, 'census.tsv')
    if '--out' in argv:
        out = argv[argv.index('--out') + 1]
    ext = os.path.join(ROOT, 'extracted')
    unp = os.path.join(ROOT, 'build', 'unpacked')
    rows = []
    summ = collections.Counter()
    for root, dirs, files in os.walk(ext):
        dirs.sort()
        for fn in sorted(files):
            if fn in SKIP:
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, ext).replace('\\', '/')
            d = open(path, 'rb').read()
            if d[:4] in (b'GBIX', b'PVRT'):
                rows.append((rel, 'pvr-file', 1, ''))
                summ['pvr-file'] += 1
                continue
            n = tbd_ok(d)
            if n:
                tail = ''
                recs = pvr.parse_tbd(d)
                comp = collections.Counter(r['comp'] for r in recs) if recs else {}
                rows.append((rel, 'tbd-file', n, 'comp=' + ','.join('%d:%d' % kv for kv in sorted(comp.items()))))
                summ['tbd-file'] += 1
                summ['tbd-file textures'] += n
                continue
            first = bzlib.parse_member(d, 0, with_data=False)
            if first is not None:
                members, tail = bzlib.parse_archive(d)
                kinds = collections.Counter()
                ud = os.path.join(unp, rel.replace('/', os.sep))
                names = {}
                if os.path.isdir(ud):
                    for fn2 in os.listdir(ud):
                        names[fn2.lower()] = fn2
                for m in members:
                    nm = (m.name or '').lower()
                    p = names.get(nm)
                    kind = 'other'
                    if nm.endswith('.pvr'):
                        kind = 'pvr-member'
                    elif p is not None:
                        pd = open(os.path.join(ud, p), 'rb').read(64 * 1024 * 1024)
                        if pd[:4] in (b'GBIX', b'PVRT'):
                            kind = 'pvr-member'
                        elif tbd_ok(pd):
                            kind = 'tbd-member'
                    kinds[kind + ' ' + m.method] += 1
                tailinfo = ''
                if tail != len(d):
                    tt = scan_tbd_tables(d, tail)
                    tailinfo = 'tail@%#x len=%d tbd_tables_in_tail=%s' % (tail, len(d) - tail, [hex(x) for x in tt[:4]])
                    summ['zsarc-with-tail'] += 1
                    if tt:
                        summ['zsarc-tail-with-tbd'] += 1
                if any(k.startswith(('pvr', 'tbd')) for k in kinds) or tailinfo:
                    rows.append((rel, 'zsarc', len(members), ' '.join('%s=%d' % kv for kv in sorted(kinds.items())) + ' ' + tailinfo))
                for k, v in kinds.items():
                    summ['zsarc member ' + k] += v
                summ['zsarc'] += 1
                continue
            # other
            info = []
            tt = scan_tbd_tables(d, 4)
            if tt:
                info.append('tbd-tables@' + ','.join(hex(x) for x in tt[:6]))
            gb = d.count(b'GBIX')
            pv = d.count(b'PVRT')
            if gb or pv:
                info.append('GBIX=%d PVRT=%d' % (gb, pv))
            if info:
                rows.append((rel, 'other', 0, ' '.join(info)))
                summ['other-with-tex'] += 1
    with open(out, 'w', encoding='utf8') as f:
        f.write('file\tkind\tcount\tdetail\n')
        for r in rows:
            f.write('\t'.join(map(str, r)) + '\n')
    for k in sorted(summ):
        print('%-40s %d' % (k, summ[k]))
    print('rows', len(rows), '->', out)


if __name__ == '__main__':
    main(sys.argv[1:])
