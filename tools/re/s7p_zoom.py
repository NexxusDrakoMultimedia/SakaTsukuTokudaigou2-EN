"""s7p_zoom FILE TID X Y W H SCALE OUT - crop of an original texture on a blue background, enlarged; prints a few pixel values."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import s7p_dump as D
f, t, x, y, w, h, sc, out = sys.argv[1:9]
x, y, w, h, sc = int(x), int(y), int(w), int(h), int(sc)
img = D.to_img(D.load(f, t))
c = img[y:y + h, x:x + w]
D.on_bg(c).resize((w * sc, h * sc), Image.NEAREST).save(out)
for r in range(min(h, 12)):
    print(' '.join('%02x%02x%02x/%x' % (p[0], p[1], p[2], p[3] >> 4) if p[3] else '....../0' for p in c[r][:12]))
