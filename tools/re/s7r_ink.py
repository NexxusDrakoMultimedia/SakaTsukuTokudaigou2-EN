"""s7r_ink ID x,y,w,h [...] : white-ish (luma>200) ink x extents per rect of the ORIGINAL texture (the label glyphs; outline/plate ignored)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import art7_lib as L
t = L.load(sys.argv[1]); a = t['arr'].astype(float)
lum = a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114
for r in sys.argv[2:]:
    x, y, w, h = [int(v) for v in r.split(',')]
    m = (lum[y:y + h, x:x + w] > 200) & (a[y:y + h, x:x + w, 3] > 200)
    if not m.any(): print(r, 'none'); continue
    ys, xs = np.nonzero(m)
    print(r, 'ink x %d..%d (w %d)  y %d..%d' % (x + xs.min(), x + xs.max(), xs.max() - xs.min() + 1, y + ys.min(), y + ys.max()))
