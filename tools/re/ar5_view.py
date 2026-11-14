"""ar5_view: decode .pvr files (repainted) to one PNG, optionally next to the original.
    python -I -X utf8 tools/re/ar5_view.py OUT.png [--scale N] [--crop x,y,w,h] FILE.pvr [FILE.pvr ...]
A file path under translation/textures/ is also compared with the original texture (before | after)."""
import os, sys, argparse
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, ar5_dump  # noqa

TEXDIR = os.path.join(ROOT, 'translation', 'textures')


def split(path):
    rel = os.path.relpath(os.path.abspath(path), TEXDIR).replace(os.sep, '/').split('/')
    for i in range(len(rel) - 1, 0, -1):
        if os.path.isfile(os.path.join(ROOT, 'extracted', *rel[:i])):
            return '/'.join(rel[:i]), '/'.join(rel[i:])[:-4]
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--scale', type=int, default=1); ap.add_argument('--crop', default='')
    ap.add_argument('--nobefore', action='store_true')
    ap.add_argument('files', nargs='+')
    a = ap.parse_args()
    rows = []
    for f in a.files:
        with open(f, 'rb') as fh:
            new = np.asarray(pvr.decode(fh.read())).copy()
        ims = []
        src, tid = split(f)
        if src and not a.nobefore:
            ims.append(ar5_dump.get(src, tid))
        ims.append(new)
        if a.crop:
            x, y, w, h = [int(v) for v in a.crop.split(',')]
            ims = [i[y:y + h, x:x + w] for i in ims]
        ims = [ar5_dump.bg(i) for i in ims]
        W = sum(i.width for i in ims) + 4 * (len(ims) - 1)
        row = Image.new('RGB', (W, max(i.height for i in ims)), (60, 0, 60))
        x = 0
        for i in ims:
            row.paste(i, (x, 0)); x += i.width + 4
        rows.append(row)
    W = max(r.width for r in rows)
    H = sum(r.height for r in rows) + 4 * (len(rows) - 1)
    c = Image.new('RGB', (W, H), (60, 0, 60))
    y = 0
    for r in rows:
        c.paste(r, (0, y)); y += r.height + 4
    if a.scale != 1:
        c = c.resize((c.width * a.scale, c.height * a.scale), Image.NEAREST)
    c.save(a.out)
    print(a.out, c.size)


if __name__ == '__main__':
    main()
