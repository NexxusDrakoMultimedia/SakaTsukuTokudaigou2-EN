"""s7m_bands SRC TID X0 X1 : print vertical bands (y ranges) of opaque pixels in columns X0..X1 and x-extent of each."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import s7m_lib as L
t = L.load(sys.argv[1], sys.argv[2]); a = t['arr']
x0, x1 = int(sys.argv[3]), int(sys.argv[4])
thr = int(sys.argv[5]) if len(sys.argv) > 5 else 40
op = a[:, x0:x1, 3] > thr
rows = op.any(1)
y = 0
while y < len(rows):
    if rows[y]:
        s = y
        while y < len(rows) and rows[y]:
            y += 1
        xs = np.nonzero(op[s:y].any(0))[0]
        print('y %d..%d (h %d)  x %d..%d' % (s, y - 1, y - s, x0 + xs.min(), x0 + xs.max()))
    y += 1
