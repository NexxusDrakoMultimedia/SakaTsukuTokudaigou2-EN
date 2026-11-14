import sys
from PIL import Image
i, x0, y0, x1, y1 = sys.argv[1], *map(int, sys.argv[2:6])
im = Image.open(f'build/art1/new/{i}.dec.png').convert('RGBA')
for y in range(y0, y1):
    print(y, ' '.join('%02x%02x%02x%02x' % im.getpixel((x, y)) if im.getpixel((x,y))[3] else '........' for x in range(x0, x1)))
