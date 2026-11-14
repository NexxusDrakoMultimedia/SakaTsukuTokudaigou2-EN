"""ar5_diff FILE.pvr [x y w h]: bounding boxes of the pixels that changed between the original texture and the repaint,
(alpha or colour), clustered; also reports transparent-in-new / opaque-in-old pixel counts per box."""
import os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, art7_lib as L, ar5_dump, ar5_view  # noqa

f = sys.argv[1]
src, tid = ar5_view.split(f)
with open(f, 'rb') as fh:
    new = np.asarray(pvr.decode(fh.read())).copy()
old = ar5_dump.get(src, tid)
ch = np.zeros(new.shape, np.uint8)
d = (np.abs(new.astype(int) - old.astype(int)).max(-1) > 16)
ch[..., 3] = d * 255
for b in L.components(ch, gx=6, gy=3, min_area=4):
    x, y, w, h = b
    sub_new = new[y:y + h, x:x + w]; sub_old = old[y:y + h, x:x + w]
    hole = int(((sub_new[..., 3] < 40) & (sub_old[..., 3] > 200)).sum())
    print('changed x=%d..%d y=%d..%d  newly-transparent px=%d of %d' % (x, x + w - 1, y, y + h - 1, hole, w * h))
