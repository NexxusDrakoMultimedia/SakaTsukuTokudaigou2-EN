import sys
sys.path.insert(0, 'tools')
import numpy as np, texinject, pvr
d = pvr.decode(texinject.extract_pvr('ETC_DATA/PL_EDIT.ZAR', 'PL_PT3.TBD#0'))
for name, (x0, x1) in {'sense': (127, 188), 'tech': (192, 240), 'int': (248, 293), 'phys': (297, 378), 'ment': (385, 458)}.items():
    a = d[272:290, x0:x1].reshape(-1, 4)
    a = a[a[:, 3] > 200]
    l = a[:, :3].sum(1)
    hi = a[l >= np.percentile(l, 88)][:, :3].mean(0).astype(int)
    lo = a[l <= np.percentile(l, 8)][:, :3].mean(0).astype(int)
    bar = d[293:297, x0 + 4:x1 - 4].reshape(-1, 4)
    print(name, 'hi', hi, 'lo', lo, 'bar', bar[:, :3].mean(0).astype(int), 'alpha', bar[:, 3].mean())
# bar rows
col = d[270:302, 150]
for i, p in enumerate(col):
    print(270 + i, p)
