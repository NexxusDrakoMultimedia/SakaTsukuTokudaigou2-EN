"""ar6_cpink: ink extents (bright pixels) per row band of the CPNAMEB / CPNAMES originals."""
import os, glob
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for pat in ('ETC_DATA__CPNAMEB.TBD/*.png', 'ETC_DATA__CPNAMES.TBD/*.png'):
    for p in sorted(glob.glob(os.path.join(ROOT, 'build', 'tex', pat))):
        a = np.asarray(Image.open(p).convert('RGBA')).astype(int)
        m = (a[..., 3] > 128) & (a[..., :3].min(-1) > 200)
        out = []
        for y0 in (4, 35, 67, 99):
            sub = m[y0:y0 + 26]
            xs = np.nonzero(sub.any(0))[0]
            out.append((int(xs.min()), int(xs.max())) if len(xs) else None)
        print(os.path.basename(p)[:5], a.shape[:2], out)
