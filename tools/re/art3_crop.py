"""art3_crop.py IN.png OUT.png x y w h scale [bg] - crop, flatten on grey, enlarge nearest, draw a pixel ruler every 10px."""
import sys
import numpy as np
from PIL import Image, ImageDraw

src, dst = sys.argv[1], sys.argv[2]
x, y, w, h, s = [int(v) for v in sys.argv[3:8]]
bg = int(sys.argv[8]) if len(sys.argv) > 8 else 90
a = np.asarray(Image.open(src).convert('RGBA').crop((x, y, x + w, y + h))).astype(float)
al = a[:, :, 3:4] / 255
rgb = a[:, :, :3] * al + bg * (1 - al)
im = Image.fromarray(rgb.astype(np.uint8)).resize((w * s, h * s), Image.NEAREST)
d = ImageDraw.Draw(im)
for gx in range((-x) % 10, w, 10):
    d.line([(gx * s, 0), (gx * s, 5)], fill=(255, 0, 0))
    if (gx + x) % 50 == 0:
        d.text((gx * s + 2, 6), str(gx + x), fill=(255, 255, 0))
for gy in range((-y) % 10, h, 10):
    d.line([(0, gy * s), (5, gy * s)], fill=(255, 0, 0))
    if (gy + y) % 50 == 0:
        d.text((7, gy * s), str(gy + y), fill=(255, 255, 0))
im.save(dst)
