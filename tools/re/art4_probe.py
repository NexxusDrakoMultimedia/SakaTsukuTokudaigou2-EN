import sys, numpy as np
from PIL import Image
# art4_probe.py png x y w h  -> prints unique colours (top 12) and a coarse map
p, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6])
a = np.asarray(Image.open(p).convert('RGBA'))[y:y+h, x:x+w]
f = a.reshape(-1, 4)
u, c = np.unique(f, axis=0, return_counts=True)
for i in np.argsort(-c)[:14]:
    print(tuple(u[i]), c[i])
