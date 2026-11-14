"""ar5_blackscan: look in every repainted texture for NEW opaque near-black rectangles (the original there was not opaque black),
and for NEW transparent holes in an opaque-plate texture.  Prints file, bbox and size.
    python -I -X utf8 tools/re/ar5_blackscan.py [min_w] [min_h]"""
import os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, ar5_dump, ar5_view  # noqa


FILL = 0.9


def blobs(m, minw, minh):
    """Axis-aligned boxes of connected components of mask m (simple flood fill via runs)."""
    H, W = m.shape
    seen = np.zeros_like(m)
    out = []
    ys, xs = np.nonzero(m)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        st = [(y0, x0)]
        seen[y0, x0] = True
        mnx = mxx = x0; mny = mxy = y0; n = 0
        while st:
            y, x = st.pop(); n += 1
            mnx = min(mnx, x); mxx = max(mxx, x); mny = min(mny, y); mxy = max(mxy, y)
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True; st.append((yy, xx))
        w, h = mxx - mnx + 1, mxy - mny + 1
        if w >= minw and h >= minh and n >= FILL * w * h:
            out.append((mnx, mny, w, h, n))
    return out


def main():
    minw = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    minh = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    for dp, _, fns in os.walk(ar5_view.TEXDIR):
        for fn in sorted(fns):
            f = os.path.join(dp, fn)
            src, tid = ar5_view.split(f)
            if not src:
                continue
            with open(f, 'rb') as fh:
                new = np.asarray(pvr.decode(fh.read())).copy()
            old = ar5_dump.get(src, tid)
            dark = lambda a: (a[..., 3] > 200) & (a[..., :3].max(-1) < 40)
            m = dark(new) & ~dark(old)
            for b in blobs(m, minw, minh):
                print('BLACK  %-28s %-14s x=%d y=%d w=%d h=%d' % (src, tid, b[0], b[1], b[2], b[3]))
            hole = (new[..., 3] < 40) & (old[..., 3] > 200)
            for b in blobs(hole, minw, minh):
                print('HOLE   %-28s %-14s x=%d y=%d w=%d h=%d' % (src, tid, b[0], b[1], b[2], b[3]))


main()
