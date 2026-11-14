"""s7x_bbox ID x y w h [x y w h ...]: alpha>40 ink bounding box inside each band (original texture)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import art7_lib as L
t = L.load(sys.argv[1])
v = [int(a) for a in sys.argv[2:]]
for k in range(0, len(v), 4):
    x, y, w, h = v[k:k + 4]
    m = t['arr'][y:y + h, x:x + w, 3] > 40
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        print((x, y, w, h), 'empty'); continue
    print((x, y, w, h), '->', (x + int(xs.min()), y + int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)))
