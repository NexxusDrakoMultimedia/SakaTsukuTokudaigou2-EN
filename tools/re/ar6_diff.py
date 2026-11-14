"""ar6_diff: compare two textures (.pvr or .png): prints the bbox of differing pixels and writes a before|after crop.
ar6_diff.py A B OUT.png [--scale 3] [--pad 6]   (magenta = transparent)"""
import os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr


def load(p):
    if p.lower().endswith('.pvr'):
        return np.asarray(pvr.decode(open(p, 'rb').read())).copy()
    return np.asarray(Image.open(p).convert('RGBA')).copy()


def flat(a, bg=(255, 0, 255)):
    im = Image.fromarray(a.astype(np.uint8), 'RGBA')
    b = Image.new('RGBA', im.size, bg + (255,))
    b.alpha_composite(im)
    return b.convert('RGB')


def main():
    a = sys.argv[1:]
    A, B = load(a[0]), load(a[1])
    sc = int(a[a.index('--scale') + 1]) if '--scale' in a else 3
    pad = int(a[a.index('--pad') + 1]) if '--pad' in a else 6
    if A.shape != B.shape:
        print('SHAPE DIFFERS', A.shape, B.shape)
        return
    d = np.any(A != B, axis=-1)
    if not d.any():
        print('identical')
        return
    ys, xs = np.nonzero(d)
    x0, x1, y0, y1 = max(0, xs.min() - pad), min(A.shape[1], xs.max() + 1 + pad), max(0, ys.min() - pad), min(A.shape[0], ys.max() + 1 + pad)
    print('diff bbox x=%d..%d y=%d..%d (%d px)' % (x0, x1, y0, y1, d.sum()))
    ca, cb = flat(A).crop((x0, y0, x1, y1)), flat(B).crop((x0, y0, x1, y1))
    w, h = ca.size
    o = Image.new('RGB', (w * sc * 2 + 6, h * sc), (40, 40, 40))
    o.paste(ca.resize((w * sc, h * sc), Image.NEAREST), (0, 0))
    o.paste(cb.resize((w * sc, h * sc), Image.NEAREST), (w * sc + 6, 0))
    o.save(a[2])


main()
