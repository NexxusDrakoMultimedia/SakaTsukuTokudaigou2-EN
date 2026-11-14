"""ar6_tvext: ink extents (bright, opaque) of the Japanese heading text in the TV_EVENT originals."""
import os
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
D = os.path.join(ROOT, 'build', 'tex', 'ETC_DATA__TV_EVENT.ZAR')


def ext(fn, y0, y1, x0=0, x1=None):
    a = np.asarray(Image.open(os.path.join(D, fn)).convert('RGBA')).astype(int)
    x1 = x1 or a.shape[1]
    sub = a[y0:y1, x0:x1]
    m = (sub[..., 3] > 128) & (sub[..., :3].max(-1) > 170)
    ys, xs = np.nonzero(m)
    cols = np.nonzero(m.any(0))[0] + x0
    runs = []
    s = p = cols[0]
    for c in cols[1:]:
        if c > p + 6:
            runs.append((int(s), int(p)))
            s = c
        p = c
    runs.append((int(s), int(p)))
    return runs, int(ys.min() + y0), int(ys.max() + y0)


for fn, bands in (('04084_TV_E1.TBD_2.png', [(0, 41), (41, 83)]), ('04081_TV_EB.TBD_1.png', [(0, 41), (41, 83)]),
                  ('04080_TV_EB.TBD_0.png', [(146, 190), (190, 236)])):
    for b in bands:
        print(fn, b, ext(fn, *b))
