"""svfmt_gs2.py DUMP : (ptr, next word) pairs of the gsp section table, with sizes = next ptr - ptr."""
import sys, struct
d = open(sys.argv[1], 'rb').read(); B = 0x8c000000
w = lambda a: struct.unpack_from('<I', d, a - B)[0]
gsp = w(0x8c159220)
rows = []
for o in range(0x20, 0x100, 4):
    v = w(gsp + o)
    if 0x8ce4c000 <= v < 0x8ce5c000: rows.append((o, v))
for i, (o, v) in enumerate(rows):
    nxt = rows[i + 1][1] if i + 1 < len(rows) else None
    print('gsp+%03x  %08x  off %05x  next-delta %s   [+4]=%08x [-4]=%08x' % (o, v, v - 0x8ce4c000, hex(nxt - v) if nxt else '-', w(gsp + o + 4), w(gsp + o - 4)))
