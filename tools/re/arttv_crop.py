import sys
from PIL import Image
f, x0, y0, x1, y1, s, out = sys.argv[1], *map(int, sys.argv[2:7]), sys.argv[7]
im = Image.open(f).convert('RGBA').crop((x0, y0, x1, y1))
b = Image.new('RGBA', im.size, (100, 100, 100, 255)); b.alpha_composite(im)
b.convert('RGB').resize((im.width * s, im.height * s), Image.NEAREST).save(out)
