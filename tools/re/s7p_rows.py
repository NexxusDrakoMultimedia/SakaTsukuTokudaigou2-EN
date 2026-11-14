"""s7p_rows FILE TID - per-row opaque pixel count and x extent of an original texture (to find line gaps)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import s7p_dump as D
img = D.to_img(D.load(sys.argv[1], sys.argv[2]))
for y in range(0, 70):
    a = np.where(img[y, :, 3] > 0)[0]
    print(y, len(a), (a[0], a[-1]) if len(a) else '')
