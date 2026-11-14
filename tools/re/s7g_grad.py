"""s7g_grad ID Y0 Y1 [X0 X1]: per-row median colour of bright opaque ink in the band (reads build/s7g/orig/ID.png)"""
import sys, numpy as np
from PIL import Image
a = np.asarray(Image.open('build/s7g/orig/%s.png' % sys.argv[1]).convert('RGBA')).astype(int)
y0, y1 = int(sys.argv[2]), int(sys.argv[3]); x0, x1 = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (0, a.shape[1])
for y in range(y0, y1):
    r = a[y, x0:x1]; m = (r[:, 3] > 200) & (r[:, :3].sum(axis=1) > 250)
    if m.sum() > 2: print(y, np.median(r[m][:, :3], axis=0).astype(int), m.sum())
    else:
        d = (r[:, 3] > 200)
        print(y, 'dark' if d.sum() else '-', np.median(r[d][:, :3], axis=0).astype(int) if d.sum() else '')
