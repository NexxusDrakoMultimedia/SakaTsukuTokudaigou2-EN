"""s7r_ext ID x,y,w,h : ink (alpha>=128) bounding boxes of the ORIGINAL texture within a rect, by row bands (gap rows split)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import art7_lib as L
i = sys.argv[1]
x, y, w, h = [int(v) for v in sys.argv[2].split(',')]
t = L.load(i)
a = t['arr'][y:y + h, x:x + w, 3] >= 128
rows = a.any(1)
yy = 0
while yy < h:
    if rows[yy]:
        y1 = yy
        while y1 < h and rows[y1]:
            y1 += 1
        cols = np.nonzero(a[yy:y1].any(0))[0]
        print('rows %d..%d  x %d..%d (w=%d)' % (y + yy, y + y1 - 1, x + cols.min(), x + cols.max(), cols.max() - cols.min() + 1))
        yy = y1
    else:
        yy += 1
