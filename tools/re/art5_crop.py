"""art5_crop IMG x y w h scale OUT : crop on grey, nearest scale, with a 10px tick grid label every 20px"""
import sys
from PIL import Image, ImageDraw
p, x, y, w, h, s, out = sys.argv[1], *map(int, sys.argv[2:7]), sys.argv[7]
im = Image.open(p).convert('RGBA').crop((x, y, x + w, y + h))
bg = Image.new('RGBA', im.size, (90, 90, 90, 255)); bg.alpha_composite(im)
bg = bg.resize((w * s, h * s), Image.NEAREST).convert('RGB')
d = ImageDraw.Draw(bg)
for gx in range((x + 19) // 20 * 20, x + w, 20):
    d.line([((gx - x) * s, 0), ((gx - x) * s, 6)], fill=(255, 255, 0)); d.text(((gx - x) * s + 2, 6), str(gx), fill=(255, 255, 0))
for gy in range((y + 19) // 20 * 20, y + h, 20):
    d.line([(0, (gy - y) * s), (6, (gy - y) * s)], fill=(255, 255, 0)); d.text((8, (gy - y) * s - 5), str(gy), fill=(255, 255, 0))
bg.save(out)
