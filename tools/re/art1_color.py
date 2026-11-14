"""art1_color - top colours in a rect (non-black). python -I -X utf8 tools/re/art1_color.py IN.png x,y,w,h [more rects]"""
import sys
from collections import Counter
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGBA')
for a in sys.argv[2:]:
    x, y, w, h = map(int, a.split(','))
    c = Counter(p for p in im.crop((x, y, x + w, y + h)).getdata() if p[3] > 200 and sum(p[:3]) > 90)
    print(a, ['#%02x%02x%02x:%d' % (p[0], p[1], p[2], n) for p, n in c.most_common(6)])
