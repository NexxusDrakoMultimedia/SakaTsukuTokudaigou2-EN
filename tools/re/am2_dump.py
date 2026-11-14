"""am2_dump - print pixel info. python -I -X utf8 tools/re/am2_dump.py FILE.png x y w h [a|l|rgb]
a = alpha map (hex digit), l = luma map (hex digit), rgb = list rows"""
import sys
from PIL import Image
import numpy as np
im = np.asarray(Image.open(sys.argv[1]).convert('RGBA')).astype(int)
x, y, w, h = map(int, sys.argv[2:6])
m = sys.argv[6] if len(sys.argv) > 6 else 'a'
print('     ' + ''.join(str((x + i) % 10) for i in range(w)))
for j in range(h):
    r = im[y + j, x:x + w]
    if m == 'a':
        s = ''.join('%x' % (p[3] >> 4) for p in r)
    elif m == 'l':
        s = ''.join('%x' % (int(0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2]) >> 4) for p in r)
    else:
        s = ' '.join('%02x%02x%02x%x' % (p[0], p[1], p[2], p[3] >> 4) for p in r)
    print('%4d %s' % (y + j, s))
