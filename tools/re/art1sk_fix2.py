"""art1sk_fix2 - remove leftover specks in repainted group-1 textures, then re-encode (writes build/art1/new/ID.*)."""
import os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr
B = os.path.join(ROOT, 'build', 'art1')
def clear(a, x0, x1, y0, y1):
    t = a[y0:y1, x0:x1]
    t[...] = 0
def rowcopy(a, x0, x1, y0, y1, xr):
    for y in range(y0, y1):
        a[y, x0:x1] = a[y, xr]
EDITS = {
    '10470': [(clear, 160, 250, 232, 234)],
    '07332': [(rowcopy, 195, 330, 31, 34, 160)],
    '10469': [(rowcopy, 195, 330, 31, 34, 160)],
    '10474': [(rowcopy, 80, 125, 63, 67, 75)],
    '00088': [(clear, 152, 158, 165, 190)],
    '37285': [(clear, 358, 363, 116, 121)],
}
for i, eds in EDITS.items():
    a = np.asarray(Image.open(os.path.join(B, 'new', i + '.png')).convert('RGBA')).copy()
    for e in eds:
        e[0](a, *e[1:])
    Image.fromarray(a, 'RGBA').save(os.path.join(B, 'new', i + '.png'))
    orig = open(os.path.join(B, 'orig', i + '.pvr'), 'rb').read()
    enc = pvr.encode(a, original=orig)
    open(os.path.join(B, 'new', i + '.pvr'), 'wb').write(enc)
    pvr.to_png(pvr.decode(enc), os.path.join(B, 'new', i + '.dec.png'))
    print(i, 'ok')
