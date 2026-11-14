"""art1_row - print pixel colours of a row segment. python -I -X utf8 tools/re/art1_row.py IN.png y x0 x1"""
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGBA'); y, a, b = map(int, sys.argv[2:5])
print(' '.join('%d:%02x%02x%02x%s' % (x, *im.getpixel((x, y))[:3], '' if im.getpixel((x, y))[3] > 200 else '*') for x in range(a, b)))
