"""sk6_specks: find small leftover fragments of old art: connected components (8-conn) of pixels that are UNCHANGED from the original,
bright (min rgb > 170, alpha > 200) and tiny (<= MAXN px), lying within 3 px of changed pixels, with at least 1 changed pixel on both
sides in the same row band.  Heuristic; lists candidates.  sk6_specks.py [--filter S] [--max 14]"""
import os, sys, argparse
from collections import deque
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, ar5_dump, ar5_view  # noqa
ap = argparse.ArgumentParser(); ap.add_argument('--filter', default=''); ap.add_argument('--max', type=int, default=14); ap.add_argument('--skip', default='ALLLOGOS,BINDLOGO,BINDNAME')
a = ap.parse_args()
skip = [s for s in a.skip.split(',') if s]
for dp, dn, fn in os.walk(ar5_view.TEXDIR):
    for f in sorted(fn):
        p = os.path.join(dp, f); rel = os.path.relpath(p, ar5_view.TEXDIR).replace(os.sep, '/')
        if a.filter not in rel or any(s in rel for s in skip): continue
        src, tid = ar5_view.split(p)
        if not src: continue
        try:
            old = ar5_dump.get(src, tid).astype(int); new = np.asarray(pvr.decode(open(p, 'rb').read())).astype(int)
        except Exception:
            continue
        if old.shape != new.shape: continue
        chg = (old != new).any(-1)
        if not chg.any(): continue
        H, W = chg.shape
        # dilate changed by 3
        dil = chg.copy()
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                dil |= np.roll(np.roll(chg, dy, 0), dx, 1)
        cand = (~chg) & (new[..., :3].min(-1) > 170) & (new[..., 3] > 200) & dil
        seen = np.zeros_like(cand); out = []
        ys, xs = np.where(cand)
        for y0, x0 in zip(ys, xs):
            if seen[y0, x0]: continue
            q = deque([(y0, x0)]); seen[y0, x0] = True; comp = []
            while q:
                y, x = q.popleft(); comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and cand[yy, xx] and not seen[yy, xx]:
                            seen[yy, xx] = True; q.append((yy, xx))
                if len(comp) > a.max: break
            if len(comp) <= a.max:
                # whole component (not just candidate part) must also be isolated: neighbours that are unchanged bright
                out.append((comp[0][1], comp[0][0], len(comp)))
        if 0 < len(out) <= 12:
            print(rel, out[:6])
