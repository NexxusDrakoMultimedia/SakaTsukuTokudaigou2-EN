import sys, numpy as np
from PIL import Image
# art4_bands.py png [gap_x] [x y w h]  -> row bands and word boxes of opaque pixels (alpha>100)
p = sys.argv[1]
gx = int(sys.argv[2]) if len(sys.argv) > 2 else 8
a = np.asarray(Image.open(p).convert('RGBA'))
X0 = Y0 = 0
if len(sys.argv) > 6:
    X0, Y0, w, h = map(int, sys.argv[3:7]); a = a[Y0:Y0 + h, X0:X0 + w]
m = a[:, :, 3] > 100
rows = m.any(1)
y = 0
H = len(rows)
while y < H:
    if rows[y]:
        y1 = y
        while y1 < H and rows[y1]:
            y1 += 1
        cols = m[y:y1].any(0)
        xs = np.nonzero(cols)[0]
        words = []
        s = xs[0]; prev = xs[0]
        for x in xs[1:]:
            if x - prev > gx:
                words.append((s + X0, prev + X0)); s = x
            prev = x
        words.append((s + X0, prev + X0))
        print('rows %d-%d  words %s' % (y + Y0, y1 - 1 + Y0, words))
        y = y1
    else:
        y += 1
