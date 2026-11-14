"""Statistics of TBD texture-bundle layout (alignment, padding, sharing) over the whole disc.

    python -I -X utf8 tools/re/texinject/analyze_tbd.py

For every TBD table found (whole files, tails of ZAR files, tables embedded in overlays/other blobs) it records, per record,
the byte range [off_i, off_{i+1}) and how many bytes the decoder really consumes (stream length up to and including the
end token).  Output: summary on stdout.
"""
import os
import sys
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import bzlib      # noqa: E402
import census     # noqa: E402


def consumed_bz(src):
    """number of packed bytes the -bz-- decoder reads (through the end token); None on error"""
    i = 0
    n = len(src)
    try:
        while True:
            fl = src[i]
            i += 1
            for _ in range(8):
                if fl & 1:
                    i += 1
                else:
                    b = src[i]
                    i += 1
                    if b & 0x80:
                        pass
                    else:
                        b2 = src[i]
                        i += 1
                        if b2 == 0:
                            return i
                fl >>= 1
    except IndexError:
        return None


def consumed_bzw(src):
    i = 0
    try:
        while True:
            fl = (src[i] << 8) | src[i + 1]
            i += 2
            for _ in range(16):
                if fl & 1:
                    i += 2
                    if i > len(src):
                        return None
                else:
                    hi = src[i + 1]
                    i += 2
                    if hi == 0:
                        return i
                fl >>= 1
    except IndexError:
        return None


def tables(d):
    """yield (base, nrec) for each TBD table in d (offset 0, tail of archive, or embedded)"""
    seen = set()
    n = census.tbd_ok(d)
    if n:
        seen.add(0)
        yield 0, n
    first = bzlib.parse_member(d, 0, with_data=False)
    start = 4
    if first is not None:
        members, tail = bzlib.parse_archive(d)
        start = tail
    for p in census.scan_tbd_tables(d, start):
        if p not in seen:
            seen.add(p)
            yield p, census.tbd_ok(d, p)


def main():
    ext = os.path.join(ROOT, 'extracted')
    st = collections.Counter()
    align = collections.Counter()
    align_raw = collections.Counter()
    slack = collections.Counter()
    slack_by = collections.defaultdict(list)
    where = collections.Counter()
    shared = 0
    bad = []
    for root, dirs, files in os.walk(ext):
        dirs.sort()
        for fn in sorted(files):
            if fn in ('BCAST.BIN', '_filelist.tsv'):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, ext).replace('\\', '/')
            d = open(path, 'rb').read()
            if d[:4] in (b'GBIX', b'PVRT'):
                continue
            for base, n in tables(d):
                kind = 'file' if base == 0 and census.tbd_ok(d) else ('tail' if bzlib.parse_member(d, 0, with_data=False) else 'embedded')
                where[kind] += 1
                recs = []
                for i in range(n):
                    f, wh, off, stp = struct.unpack_from('<IIII', d, base + 4 + 16 * i)
                    recs.append((f, wh & 0xffff, wh >> 16, off, stp))
                # end of table: next table start / file end is unknown for embedded tables -> bound by next record offset only,
                # for the last record bound by the file end (upper bound; real slack unknown)
                offs = [r[3] for r in recs]
                for i, (f, w, h, off, stp) in enumerate(recs):
                    st['records'] += 1
                    comp = f >> 30
                    st['comp%d' % comp] += 1
                    align[off % 32 == 0, off % 4 == 0] += 1
                    if comp == 0:
                        align_raw[(off % 32 == 0, off % 4 == 0)] += 1
                    if i + 1 < n:
                        end = offs[i + 1]
                        if end == off:
                            shared += 1
                            continue
                    else:
                        end = None
                    blk = d[base + off:base + end] if end is not None else None
                    if blk is None:
                        st['last-record'] += 1
                        if kind == 'file':
                            blk = d[base + off:]
                        else:
                            continue
                    if comp == 1:
                        c = consumed_bzw(blk)
                    elif comp == 2:
                        c = consumed_bz(blk)
                    else:
                        c = len(blk)
                    if c is None:
                        st['consume-error'] += 1
                        bad.append((rel, base, i))
                        continue
                    gap = len(blk) - c
                    slack[min(gap, 64) if comp else -1] += 1
                    if comp:
                        slack_by[kind].append(gap)
                st['tables'] += 1
    print('tables by kind', dict(where))
    print('records', st['records'], {k: v for k, v in st.items() if k.startswith('comp')})
    print('records sharing an offset with the next one (dedup):', shared)
    print('offset alignment (32-aligned, 4-aligned):', dict(align))
    print('raw (comp0) offset alignment:', dict(align_raw))
    print('compressed record: bytes between end token and next record (cap 64):')
    for k in sorted(slack):
        if k >= 0:
            print('   gap %2d : %d' % (k, slack[k]))
    print('last-record (unbounded)', st['last-record'], 'consume-errors', st['consume-error'], bad[:5])
    for k, v in slack_by.items():
        print(k, 'n=%d zero-gap=%d mean-gap=%.2f max=%d' % (len(v), sum(1 for g in v if g == 0), sum(v) / max(1, len(v)), max(v)))


if __name__ == '__main__':
    main()
