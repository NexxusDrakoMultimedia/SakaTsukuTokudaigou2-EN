"""ar6_crop: crop a decoded original on magenta, scaled, with a 16 px tick grid: ar6_crop.py ID x y w h scale OUT"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import art7_lib as L
i, x, y, w, h, s = sys.argv[1], *[int(v) for v in sys.argv[2:7]]
out = sys.argv[7]
a = L.load(i)['arr'].astype(np.uint8)
im = Image.fromarray(a, 'RGBA')
b = Image.new('RGBA', im.size, (255, 0, 255, 255)); b.alpha_composite(im)
c = b.crop((x, y, x + w, y + h)).convert('RGB').resize((w * s, h * s), Image.NEAREST)
d = ImageDraw.Draw(c)
for gx in range((x + 15) // 16 * 16, x + w, 16):
    d.line([( (gx - x) * s, 0), ((gx - x) * s, 6)], fill=(255, 255, 0)); d.text(((gx - x) * s + 1, 6), str(gx), fill=(255, 255, 0))
for gy in range((y + 15) // 16 * 16, y + h, 16):
    d.line([(0, (gy - y) * s), (6, (gy - y) * s)], fill=(0, 255, 255)); d.text((8, (gy - y) * s - 5), str(gy), fill=(0, 255, 255))
c.save(out)
