"""sk6_bbox: skeptic check. For every installed texture (from ar6_changed list or all under translation/textures), find row bands of
old ink (alpha>40) and flag new ink that lies outside the old band's x extent (+TOL) or outside any old band's rows.
Usage: sk6_bbox.py [--tol 2] [--filter substr] [--skip substr] """
import os, sys, argparse
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, ar5_dump, ar5_view  # noqa
ap = argparse.ArgumentParser(); ap.add_argument('--tol', type=int, default=2); ap.add_argument('--filter', default=''); ap.add_argument('--skip', default='ALLLOGOS,BINDLOGO,BINDNAME,STAFFLST')
ap.add_argument('--changed', action='store_true')
a = ap.parse_args()
TEX = ar5_view.TEXDIR
skip = [s for s in a.skip.split(',') if s]
def bands(m):
    rows = m.any(1); out = []; y = 0; H = len(rows)
    while y < H:
        if rows[y]:
            y0 = y
            while y < H and rows[y]: y += 1
            out.append((y0, y))
        else: y += 1
    return out
n = 0
for dp, dn, fn in os.walk(TEX):
    for f in sorted(fn):
        p = os.path.join(dp, f); rel = os.path.relpath(p, TEX).replace(os.sep, '/')
        if a.filter not in rel or any(s in rel for s in skip): continue
        src, tid = ar5_view.split(p)
        if not src: continue
        try:
            old = ar5_dump.get(src, tid); new = np.asarray(pvr.decode(open(p, 'rb').read()))
        except Exception as e:
            print('ERR', rel, e); continue
        if old.shape != new.shape: print('SHAPE', rel, old.shape, new.shape); continue
        if (old == new).all(): continue
        n += 1
        om = old[..., 3] > 40; nm = new[..., 3] > 40
        # new ink outside old ink columns-in-band
        flags = []
        for y0, y1 in bands(om | nm):
            ob = om[y0:y1]; nb = nm[y0:y1]
            if not ob.any():
                flags.append('band y%d-%d new only' % (y0, y1)); continue
            ox = np.where(ob.any(0))[0]; nx = np.where(nb.any(0))[0] if nb.any() else []
            if len(nx) == 0: continue
            if nx[-1] > ox[-1] + a.tol: flags.append('y%d-%d right +%d (old %d..%d new %d..%d)' % (y0, y1, nx[-1] - ox[-1], ox[0], ox[-1], nx[0], nx[-1]))
            if nx[0] < ox[0] - a.tol: flags.append('y%d-%d left +%d (old %d..%d new %d..%d)' % (y0, y1, ox[0] - nx[0], ox[0], ox[-1], nx[0], nx[-1]))
        if flags: print(rel, '|', '; '.join(flags[:4]))
print('changed textures checked', n)
