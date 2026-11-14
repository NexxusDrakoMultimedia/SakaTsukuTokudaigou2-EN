import sys
from PIL import Image
src, x0, y0, x1, y1, scale, out = sys.argv[1], *map(int, sys.argv[2:7]), sys.argv[7]
im = Image.open(src).convert("RGB").crop((x0, y0, x1, y1))
im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
im.save(out)
