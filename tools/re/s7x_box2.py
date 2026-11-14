"""s7x_box2 IMG.png mode x y w h [...]: mode 'a' alpha>40 bbox, 'l' luma>130 & sat<.4 bbox inside bands."""
import sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert('RGBA')).astype(float)
mode = sys.argv[2]
v = [int(q) for q in sys.argv[3:]]
luma = a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114
sat = (a[..., :3].max(-1) - a[..., :3].min(-1)) / np.maximum(a[..., :3].max(-1), 1)
for k in range(0, len(v), 4):
    x, y, w, h = v[k:k + 4]
    m = (a[..., 3] > 40) if mode == 'a' else ((luma > 130) & (sat < 0.4) & (a[..., 3] > 200))
    sub = m[y:y + h, x:x + w]
    ys, xs = np.nonzero(sub)
    if len(xs) == 0:
        print((x, y, w, h), 'empty'); continue
    print((x, y, w, h), '->', (x + int(xs.min()), y + int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)))
