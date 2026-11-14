"""s7x_yel IMG x0 x1 y0 y1: rows (runs) of yellow ink (R,G>180, B<120) in the column band; prints bbox per vertical run."""
import sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert('RGBA')).astype(int)
x0, x1, y0, y1 = [int(v) for v in sys.argv[2:6]]
m = (a[..., 0] > 180) & (a[..., 1] > 180) & (a[..., 2] < 120) & (a[..., 3] > 200)
sub = m[y0:y1, x0:x1]
rows = sub.sum(1) > 0
y = 0
while y < len(rows):
    if rows[y]:
        s = y
        while y < len(rows) and rows[y]: y += 1
        cols = np.nonzero(sub[s:y].sum(0))[0]
        print('y', y0 + s, y0 + y - 1, 'x', x0 + cols.min(), x0 + cols.max(), 'h', y - s, 'w', cols.max() - cols.min() + 1)
    else:
        y += 1
