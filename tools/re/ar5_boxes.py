"""ar5_boxes SRC TID x y w h [gx gy]: ink boxes (alpha > 24, clustered) of an ORIGINAL texture inside a rect, and the same for the
repainted file under translation/textures if --new is given.  Prints x0..x1, y0..y1 (inclusive)."""
import os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L, ar5_dump  # noqa


def main():
    a = sys.argv[1:]
    new = '--new' in a
    if new:
        a.remove('--new')
    src, tid = a[0], a[1]
    x, y, w, h = [int(v) for v in a[2:6]]
    gx = int(a[6]) if len(a) > 6 else 5
    gy = int(a[7]) if len(a) > 7 else 2
    if new:
        import pvr
        with open(os.path.join(L.TEXDIR, *src.split('/'), tid + '.pvr'), 'rb') as f:
            arr = np.asarray(pvr.decode(f.read())).copy()
    else:
        arr = ar5_dump.get(src, tid)
    sub = np.zeros_like(arr)
    sub[y:y + h, x:x + w] = arr[y:y + h, x:x + w]
    for b in L.components(sub, gx=gx, gy=gy):
        print('x %d..%d  y %d..%d  (w %d h %d)' % (b[0], b[0] + b[2] - 1, b[1], b[1] + b[3] - 1, b[2], b[3]))


main()
