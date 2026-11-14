"""s7r_view OUT.png SCALE x,y,w,h A.png [B.png ...] : crop and stack PNG files side by side on a grey ground (alpha shown)."""
import sys
from PIL import Image
out, sc = sys.argv[1], int(sys.argv[2])
x, y, w, h = [int(v) for v in sys.argv[3].split(',')]
ims = []
for f in sys.argv[4:]:
    im = Image.open(f).convert('RGBA').crop((x, y, x + w, y + h))
    bg = Image.new('RGBA', im.size, (110, 110, 130, 255)); bg.alpha_composite(im)
    ims.append(bg.resize((w * sc, h * sc), Image.NEAREST).convert('RGB'))
c = Image.new('RGB', (sum(i.width for i in ims) + 6 * (len(ims) - 1), h * sc), (60, 0, 60))
xx = 0
for i in ims:
    c.paste(i, (xx, 0)); xx += i.width + 6
c.save(out); print(out, c.size)
