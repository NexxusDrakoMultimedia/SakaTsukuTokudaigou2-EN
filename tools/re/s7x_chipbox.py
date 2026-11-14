"""s7x_chipbox: bounding boxes of bright/dark ink of the 37285 category chips (cells 104x32)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import art7_lib as L
t = L.load('37285')
a = t['arr'].astype(float)
luma = a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114
mx = a[..., :3].max(-1); mn = a[..., :3].min(-1)
sat = (mx - mn) / np.maximum(mx, 1)
for r in range(7):
    for c, x0 in enumerate((96, 208, 320)):
        y0 = 288 + 32 * r
        sub = (luma > 175) & (sat < 0.45) & (a[..., 3] > 200)
        # light-cyan/yellow text for rows 5/6
        ys, xs = np.nonzero(sub[y0:y0 + 26, x0:x0 + 108])
        if len(xs) < 20:
            continue
        print(r, c, 'x', x0 + xs.min(), x0 + xs.max(), 'y', y0 + ys.min(), y0 + ys.max(), 'n', len(xs))
