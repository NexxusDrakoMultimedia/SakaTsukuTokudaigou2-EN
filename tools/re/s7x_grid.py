"""s7x_grid IMG.png OUT.png x y w h scale: crop with a 16 px grid (labelled every 32) on grey-purple."""
import sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]).convert('RGBA')
out = sys.argv[2]
x, y, w, h, sc = [int(v) for v in sys.argv[3:8]]
c = im.crop((x, y, x + w, y + h))
bg = Image.new('RGBA', c.size, (110, 70, 110, 255)); bg.alpha_composite(c)
bg = bg.resize((w * sc, h * sc), Image.NEAREST).convert('RGB')
d = ImageDraw.Draw(bg)
for gx in range((x + 15) // 16 * 16, x + w, 16):
    px = (gx - x) * sc
    d.line([px, 0, px, h * sc], fill=(255, 255, 255) if gx % 32 == 0 else (90, 90, 110))
    if gx % 32 == 0: d.text((px + 1, 1), str(gx), fill=(255, 255, 0))
for gy in range((y + 15) // 16 * 16, y + h, 16):
    py = (gy - y) * sc
    d.line([0, py, w * sc, py], fill=(255, 255, 255) if gy % 32 == 0 else (90, 90, 110))
    if gy % 32 == 0: d.text((1, py + 1), str(gy), fill=(0, 255, 255))
bg.save(out)
