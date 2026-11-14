import sys
from PIL import Image
f, x0, y0, x1, y1, s, out = sys.argv[1:8]
im = Image.open(f).convert('RGBA')
bg = Image.new('RGBA', im.size, (90, 90, 120, 255)); bg.alpha_composite(im)
c = bg.crop((int(x0), int(y0), int(x1), int(y1)))
c = c.resize((c.width * int(s), c.height * int(s)), Image.NEAREST); c.save(out)
