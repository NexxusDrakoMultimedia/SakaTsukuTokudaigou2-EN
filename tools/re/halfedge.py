"""Tick-mark hunt: report half-width glyphs (original FONT.BIN) that have ink in the outer columns/rows or are not blank when they
should be (0x20 space, and 0xA0 region).  python -I -X utf8 tools/re/halfedge.py [path]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import font as F

path = sys.argv[1] if len(sys.argv) > 1 else None
f = F.Font.load(path)
H = f.half()


def px(g, x, y):
    b = g[y * 6 + x // 2]
    return (b >> 4) if x % 2 == 0 else (b & 15)


def ink(v):
    return v != 15


print('half glyphs:', len(H))
for i, g in enumerate(H):
    cnt = sum(1 for y in range(24) for x in range(12) if ink(px(g, x, y)))
    col0 = sum(1 for y in range(24) if ink(px(g, 0, y)))
    col11 = sum(1 for y in range(24) if ink(px(g, 11, y)))
    row0 = sum(1 for x in range(12) if ink(px(g, x, 0)))
    row23 = sum(1 for x in range(12) if ink(px(g, x, 23)))
    code = F.half_byte(i)
    ch = chr(code) if 0x20 <= code < 0x7f else '.'
    flag = ''
    if col0 or col11 or row0 or row23:
        flag = 'EDGE col0=%d col11=%d row0=%d row23=%d' % (col0, col11, row0, row23)
    if i == 0 or flag:
        print('%3d 0x%02x %s ink=%3d %s' % (i, code, ch, cnt, flag))
