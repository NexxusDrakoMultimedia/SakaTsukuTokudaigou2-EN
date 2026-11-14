"""FONT.BIN reader / glyph renderer (textengine agent).
Layout (PROVEN by code FUN_8c15e72c + data):
  u32 nglyph(3648), u32 tab_off(0x10), u32 data_off(0x3910), u32 hw_off(0x9c51c)
  tab: nglyph u32 offsets relative to data_off; each glyph = -bz-- stream (bzlib.decompress_bz) -> 288 bytes (24x24, 4bpp)
  hw area at hw_off: 160 raw glyphs * 144 bytes (12x24, 4bpp)
"""
import struct, sys
sys.path.insert(0, 'tools')
import bzlib
F = open('extracted/FONT.BIN', 'rb').read()
N, TO, DO, HW = struct.unpack_from('<4I', F, 0)
TAB = struct.unpack_from('<%dI' % N, F, TO)
def glyph(i):
    o = DO + TAB[i]; e = DO + TAB[i + 1] if i + 1 < N else HW
    return bzlib.decompress_bz(F[o:e])
def hwglyph(i):
    return F[HW + i * 144: HW + (i + 1) * 144]
def render(g, w, h, order='lo'):
    rows = []
    bpr = w // 2
    for y in range(h):
        s = ''
        for x in range(bpr):
            b = g[y * bpr + x]
            lo, hi = b & 15, b >> 4
            for p in ((lo, hi) if order == 'lo' else (hi, lo)):
                s += ' .:-=+*#%@'[min(p, 9)] if p else ' '
        rows.append(s)
    return '\n'.join(rows)
if __name__ == '__main__':
    kind = sys.argv[1]; i = int(sys.argv[2], 0)
    if kind == 'f': print(render(glyph(i), 24, 24))
    else: print(render(hwglyph(i), 12, 24))
