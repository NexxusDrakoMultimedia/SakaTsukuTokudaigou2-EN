import sys, numpy as np
from PIL import Image
p = sys.argv[1]
a = np.asarray(Image.open(p).convert('RGBA')).astype(int)
H, W = a.shape[:2]
y0, y1 = int(sys.argv[2]), int(sys.argv[3])
for y in range(y0, y1):
    r = a[y]
    white = (r[:, 3] > 200) & (r[:, :3].sum(1) > 450)
    xs = np.nonzero(white)[0]
    sat = (r[:, 3] > 200) & ((r[:, :3].max(1) - r[:, :3].min(1)) > 60)
    print(y, int(white.sum()), (int(xs.min()), int(xs.max())) if len(xs) else '', 'sat', int(sat.sum()), tuple(r[W // 2]))
