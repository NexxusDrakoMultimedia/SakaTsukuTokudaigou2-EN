import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, art7_lib as L
a = L.load('36921')['arr'].astype(int)
for name, (x, py, srcx) in {'g_dim': (10, 64, 8), 'y_dim': (131, 64, 128), 'r_dim': (10, 96, 8), 'b_dim': (131, 96, 128), 'g_br': (10, 0, 8), 'b_br': (131, 32, 128)}.items():
    reg = a[py + 3:py + 27, x:x + 98, :3]
    prof = a[py + 3:py + 27, srcx:srcx + 1, :3]
    d = (reg - prof)
    lum = d.mean(-1)
    for tag, m in (('lighter', lum > 25), ('darker', lum < -25)):
        if m.sum() > 20:
            print(name, tag, m.sum(), np.median(reg[m], 0).astype(int), 'p90', np.percentile(reg[m], 90, axis=0).astype(int), 'p10', np.percentile(reg[m], 10, axis=0).astype(int))
