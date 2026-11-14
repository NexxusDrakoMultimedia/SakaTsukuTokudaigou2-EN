"""s7bj_sheet: side by side contact sheet of PNGs: s7bj_sheet.py OUT.png scale IN1.png IN2.png ..."""
import sys
from PIL import Image
out, sc = sys.argv[1], float(sys.argv[2])
ims = []
for p in sys.argv[3:]:
    im = Image.open(p).convert('RGBA')
    bg = Image.new('RGBA', im.size, (90, 160, 90, 255))
    bg.alpha_composite(im)
    if sc != 1:
        bg = bg.resize((int(bg.width * sc), int(bg.height * sc)), Image.NEAREST)
    ims.append(bg)
W = sum(i.width for i in ims) + 8 * (len(ims) - 1)
H = max(i.height for i in ims)
s = Image.new('RGBA', (W, H), (40, 40, 40, 255))
x = 0
for i in ims:
    s.paste(i, (x, 0))
    x += i.width + 8
s.save(out)
