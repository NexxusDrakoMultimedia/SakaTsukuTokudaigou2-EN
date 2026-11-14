"""s7e_view: before | current (translation/textures if present) of one 5-digit id on a magenta/grey backdrop.
    python -I -X utf8 tools/re/s7e_view.py ID OUT.png [--scale N] [--crop x,y,w,h] [--bg r,g,b] [--file PATH.pvr]
--file compares with that PVR file instead of the installed copy."""
import os, sys, argparse
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art7_lib as L  # noqa
import pvr  # noqa


def comp(arr, bg):
    im = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    b = Image.new('RGBA', im.size, bg + (255,))
    b.alpha_composite(im)
    return b.convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('id'); ap.add_argument('out')
    ap.add_argument('--scale', type=int, default=1)
    ap.add_argument('--crop', default='')
    ap.add_argument('--bg', default='110,110,130')
    ap.add_argument('--file', default='')
    ap.add_argument('--only', action='store_true', help='show only the current/new image')
    a = ap.parse_args()
    bg = tuple(int(v) for v in a.bg.split(','))
    t = L.load(a.id)
    ims = [t['arr']]
    p = a.file or L.tex_path(t['src'], t['tid'])
    if os.path.isfile(p):
        ims.append(np.asarray(pvr.decode(open(p, 'rb').read())).copy())
    else:
        print('no installed file', p)
    if a.only:
        ims = ims[-1:]
    if a.crop:
        x, y, w, h = [int(v) for v in a.crop.split(',')]
        ims = [i[y:y + h, x:x + w] for i in ims]
    ims = [comp(i, bg) for i in ims]
    W = sum(i.width for i in ims) + 4 * (len(ims) - 1)
    c = Image.new('RGB', (W, max(i.height for i in ims)), (60, 0, 60))
    x = 0
    for i in ims:
        c.paste(i, (x, 0)); x += i.width + 4
    if a.scale != 1:
        c = c.resize((c.width * a.scale, c.height * a.scale), Image.NEAREST)
    c.save(a.out)
    print(a.out, c.size, t['src'], t['tid'], t['info'].get('format'))


if __name__ == '__main__':
    main()
