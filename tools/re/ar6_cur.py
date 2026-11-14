"""ar6_cur: montage of installed (translation/textures) textures, before|after.  ar6_cur.py OUT.png substr [substr...] [--scale 1] [--cols 2] [--bg 60,60,90]
A texture is shown as original (extracted/, left) and installed (right); label = path."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr, texinject
TEX = os.path.join(ROOT, 'translation', 'textures')


def flat(a, bg):
    im = Image.fromarray(a.astype(np.uint8), 'RGBA')
    b = Image.new('RGBA', im.size, bg + (255,))
    b.alpha_composite(im)
    return b.convert('RGB')


def main():
    a = sys.argv[1:]
    out = a[0]
    sc = 1; cols = 2; bg = (60, 60, 90); subs = []
    i = 1
    while i < len(a):
        if a[i] == '--scale': sc = float(a[i + 1]); i += 2
        elif a[i] == '--cols': cols = int(a[i + 1]); i += 2
        elif a[i] == '--bg': bg = tuple(int(x) for x in a[i + 1].split(',')); i += 2
        else: subs.append(a[i]); i += 1
    files = []
    for dp, _, fn in os.walk(TEX):
        for f in fn:
            p = os.path.join(dp, f)
            r = os.path.relpath(p, TEX).replace(os.sep, '/')
            if all(s in r for s in subs[:1]) and all(s in r for s in subs[1:]):
                files.append(r)
    files.sort()
    cells = []
    cache = {}
    for r in files:
        cur = np.asarray(pvr.decode(open(os.path.join(TEX, r), 'rb').read())).copy()
        parts = r.split('/')
        cont = tid = None
        for k in range(len(parts) - 1, 0, -1):
            if os.path.isfile(os.path.join(ROOT, 'extracted', *parts[:k])):
                cont, tid = '/'.join(parts[:k]), '/'.join(parts[k:])[:-4]
                break
        data = open(os.path.join(ROOT, 'extracted', *cont.split('/')), 'rb').read()
        try:
            org = np.asarray(pvr.decode(texinject.extract_pvr(data, tid))).copy()
        except Exception as e:
            org = np.zeros_like(cur)
        A, B = flat(org, bg), flat(cur, bg)
        if sc != 1:
            A = A.resize((int(A.width * sc), int(A.height * sc)), Image.NEAREST); B = B.resize((int(B.width * sc), int(B.height * sc)), Image.NEAREST)
        W = A.width + B.width + 12
        c = Image.new('RGB', (W, A.height + 14), (20, 20, 20))
        c.paste(A, (0, 14)); c.paste(B, (A.width + 12, 14))
        ImageDraw.Draw(c).text((2, 1), r, fill=(255, 255, 0))
        cells.append(c)
    if not cells:
        print('no match'); return
    cw = max(c.width for c in cells); rows = (len(cells) + cols - 1) // cols
    rh = [max(c.height for c in cells[k * cols:(k + 1) * cols]) for k in range(rows)]
    S = Image.new('RGB', (cw * cols + 4 * cols, sum(rh) + 4 * rows), (0, 0, 0))
    y = 0
    for k in range(rows):
        for j, c in enumerate(cells[k * cols:(k + 1) * cols]):
            S.paste(c, (j * (cw + 4), y))
        y += rh[k] + 4
    S.save(out)
    print(len(cells), S.size)

main()
