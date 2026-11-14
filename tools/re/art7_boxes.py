"""art7_boxes ID [--crop x y w h] [--thr N] [--gx N] [--gy N] [--bg r g b tol]: print ink boxes (global coords) and write
build/art7/boxes/ID.png (2x overlay)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import art7_lib as L

argv = sys.argv[1:]
id5 = argv[0]
opt = {}
i = 1
while i < len(argv):
    k = argv[i]
    n = {'--crop': 4, '--bg': 4}.get(k, 1)
    opt[k] = [int(v) for v in argv[i + 1:i + 1 + n]]
    i += 1 + n
t = L.load(id5)
arr = t['arr']
ox = oy = 0
if '--crop' in opt:
    ox, oy, w, h = opt['--crop']
    sub = np.zeros_like(arr)
    sub[oy:oy + h, ox:ox + w] = arr[oy:oy + h, ox:ox + w]
    arr = sub
kw = dict(thr=opt.get('--thr', [24])[0], gx=opt.get('--gx', [5])[0], gy=opt.get('--gy', [2])[0])
if '--bg' in opt:
    kw['bgdist'] = tuple(opt['--bg'])
b = L.components(arr, **kw)
os.makedirs(os.path.join(L.OUT, 'boxes'), exist_ok=True)
L.overlay(arr, b, os.path.join(L.OUT, 'boxes', id5 + '.png'))
print(t['src'], repr(t['tid']), t['arr'].shape)
for i, x in enumerate(b):
    print(i, tuple(int(v) for v in x))
