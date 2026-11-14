"""svfmt_tail.py DUMP... : state of the 64KB save arena outside the registered sections (gaps and tail up to 0x10000)."""
import sys, struct
for fn in sys.argv[1:]:
    d = open(fn, 'rb').read(); B = 0x8c000000
    w = lambda a: struct.unpack_from('<I', d, a - B)[0]
    gsp = w(0x8c159220); secs = []
    for o in range(0x24, 0xa0, 8):
        p = w(gsp + o); sz = w(gsp + o + 4) & 0xffff
        if 0x8ce4c000 <= p < 0x8ce5c000: secs.append((p - 0x8ce4c000, sz))
    secs.sort(); cur = 0; out = []
    for p, sz in secs:
        if p > cur: out.append(('gap', cur, p))
        cur = max(cur, p + sz)
    out.append(('tail', cur, 0x10000))
    print(fn)
    for k, a, b in out:
        seg = d[0x8ce4c000 - B + a:0x8ce4c000 - B + b]
        print('  %s %05x-%05x len %05x nonzero bytes %d  distinct %d first-nonzero %s' % (k, a, b, b - a, sum(1 for x in seg if x), len(set(seg)), hex(next((i + a for i, x in enumerate(seg) if x), -1))))
