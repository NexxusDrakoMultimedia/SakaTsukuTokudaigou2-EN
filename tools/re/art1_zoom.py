"""art1_zoom - crop+zoom views. python -I -X utf8 tools/re/art1_zoom.py IN.png OUT.png scale x,y,w,h [x,y,w,h ...]  (crops stacked vertically)"""
import sys
from PIL import Image
src, out, sc = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(src).convert('RGBA')
crops = []
for a in sys.argv[4:]:
    x, y, w, h = map(int, a.split(','))
    c = im.crop((x, y, x + w, y + h)).resize((w * sc, h * sc), Image.NEAREST)
    bg = Image.new('RGBA', c.size, (255, 0, 255, 255)); bg.alpha_composite(c); crops.append(bg)
W = max(c.width for c in crops); H = sum(c.height + 4 for c in crops)
o = Image.new('RGB', (W, H), (40, 40, 40)); y = 0
for c in crops:
    o.paste(c.convert('RGB'), (0, y)); y += c.height + 4
o.save(out)
