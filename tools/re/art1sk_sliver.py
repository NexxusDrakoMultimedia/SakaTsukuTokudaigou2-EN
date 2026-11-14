import sys, numpy as np
from PIL import Image
i = sys.argv[1]; x0, x1, y0, y1, xr = map(int, sys.argv[2:7])
a = np.asarray(Image.open(f'build/art1/new/{i}.dec.png').convert('RGBA')).astype(int)
o = np.asarray(Image.open(f'build/art1/orig/{i}.png').convert('RGBA')).astype(int)
for y in range(y0, y1):
    d = np.abs(a[y, x0:x1, :3] - a[y, xr, :3]).sum(1)
    xs = [x0 + k for k in np.nonzero(d > 45)[0]]
    d2 = np.abs(o[y, x0:x1, :3] - o[y, xr, :3]).sum(1)
    xo = [x0 + k for k in np.nonzero(d2 > 45)[0]]
    print(y, 'new', len(xs), xs[:8], '| orig', len(xo))
