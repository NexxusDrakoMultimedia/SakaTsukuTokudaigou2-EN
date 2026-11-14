"""sk6_prev: compare ink x extents of the installed texture with the ar6-start snapshot (build/ar6/texbak). sk6_prev.py FILTER"""
import os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr
A = os.path.join(ROOT, 'build', 'ar6', 'texbak'); B = os.path.join(ROOT, 'translation', 'textures')
flt = sys.argv[1]
for dp, dn, fn in os.walk(B):
    for f in sorted(fn):
        p = os.path.join(dp, f); r = os.path.relpath(p, B).replace(os.sep, '/'); q = os.path.join(A, *r.split('/'))
        if flt not in r or not os.path.exists(q): continue
        a = np.asarray(pvr.decode(open(q, 'rb').read())); b = np.asarray(pvr.decode(open(p, 'rb').read()))
        if (a == b).all(): continue
        def ext(im):
            m = im[..., 3] > 40; xs = np.where(m.any(0))[0]; ys = np.where(m.any(1))[0]
            return (xs[0], xs[-1], ys[0], ys[-1]) if len(xs) else None
        print(r, 'prev', ext(a), 'now', ext(b))
