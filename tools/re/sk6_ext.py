"""sk6_ext: print old/new ink bands and x extents for one installed texture. sk6_ext.py PATH.pvr"""
import os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, ar5_dump, ar5_view  # noqa
def bands(m):
    rows = m.any(1); out = []; y = 0; H = len(rows)
    while y < H:
        if rows[y]:
            y0 = y
            while y < H and rows[y]: y += 1
            out.append((y0, y))
        else: y += 1
    return out
for p in sys.argv[1:]:
    src, tid = ar5_view.split(p)
    old = ar5_dump.get(src, tid); new = np.asarray(pvr.decode(open(p, 'rb').read()))
    print(p, old.shape)
    for nm, im in (('old', old), ('new', new)):
        m = im[..., 3] > 40
        for y0, y1 in bands(m):
            xs = np.where(m[y0:y1].any(0))[0]
            print('  %s y%d-%d x%d..%d' % (nm, y0, y1, xs[0], xs[-1]))
