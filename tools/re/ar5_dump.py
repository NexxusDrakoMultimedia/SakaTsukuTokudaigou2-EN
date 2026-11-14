"""ar5_dump: decode textures to PNG on a grey backdrop.
    python -I -X utf8 tools/re/ar5_dump.py OUT.png [--scale N] [--cur] SRC TID [SRC TID ...]
--cur reads from the built disc folder given by --root instead of extracted/ (not needed normally)."""
import os, sys, argparse
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr, texinject  # noqa


def get(src, tid, root=None):
    p = os.path.join(root or os.path.join(ROOT, 'extracted'), *src.split('/'))
    with open(p, 'rb') as f:
        d = f.read()
    return np.asarray(pvr.decode(texinject.extract_pvr(d, tid))).copy()


def bg(arr, col=(255, 0, 255)):
    im = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    b = Image.new('RGBA', im.size, col + (255,))
    b.alpha_composite(im)
    return b.convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--scale', type=int, default=1)
    ap.add_argument('--root', default=None)
    ap.add_argument('pairs', nargs='+')
    a = ap.parse_args()
    ims = []
    for i in range(0, len(a.pairs), 2):
        ims.append(bg(get(a.pairs[i], a.pairs[i + 1], a.root)))
    W = sum(i.width for i in ims) + 4 * (len(ims) - 1)
    H = max(i.height for i in ims)
    c = Image.new('RGB', (W, H), (60, 0, 60))
    x = 0
    for i in ims:
        c.paste(i, (x, 0))
        x += i.width + 4
    if a.scale != 1:
        c = c.resize((c.width * a.scale, c.height * a.scale), Image.NEAREST)
    c.save(a.out)
    print(a.out, c.size)


if __name__ == '__main__':
    main()
