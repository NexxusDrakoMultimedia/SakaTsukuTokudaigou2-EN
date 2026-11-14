"""skm_render.py OUT.png : render money phrases with the PATCHED proportional half-width font (advance table of fontpatch), 3x, to judge 'O' versus '0'.
Read-only on the project; writes only the PNG given."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import font as F
import fontpatch as FPT
raw = open(os.path.join(os.path.dirname(os.path.dirname(HERE)), 'extracted', 'FONT.BIN'), 'rb').read()
nb, table = FPT.proportional_font(raw)
f = F.Font(nb)
half = f.half()
lines = ['1 Oku 8500 Man', '10 Oku 8500 Man', '1 oku 8500 man', '1 Oku 300M', '13 Oku 1500M', '15 Oku 0000 Man', '100 Oku', '1000 Man  Oku  OO 00']
SC = 3
W = 330
H = 30 * len(lines) + 8
img = [bytearray([255]) * (W * SC) for _ in range(H * SC)]
for li, s in enumerate(lines):
    x, y = 6, 4 + li * 30
    for ch in s:
        i = F.half_index(ord(ch))
        nib = F.nibbles(half[i])
        for yy in range(24):
            for xx in range(12):
                v = nib[yy * 12 + xx] * 17
                for sy in range(SC):
                    for sx in range(SC):
                        px = (x + xx) * SC + sx
                        if px < W * SC:
                            r = img[(y + yy) * SC + sy]
                            if v < r[px]:
                                r[px] = v
        x += table[ord(ch)] or 12
F.write_png(sys.argv[1], W * SC, H * SC, img)
print('written', sys.argv[1], [ (c, table[ord(c)]) for c in '0O1oMmk '])
