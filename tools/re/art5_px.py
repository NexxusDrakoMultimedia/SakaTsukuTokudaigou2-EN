"""art5_px: print pixel rows. art5_px.py IMG x0 y0 x1 y1"""
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGBA')
x0, y0, x1, y1 = map(int, sys.argv[2:6])
for y in range(y0, y1):
    print(y, ' '.join('%02x%02x%02x%02x' % im.getpixel((x, y)) for x in range(x0, x1)))
