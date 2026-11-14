"""s7bj_title: repaint of the title logo textures (package J).  Writes PNGs to build/s7/titles/new/ only.

  python -I -X utf8 tools/re/s7bj_title.py 00101 00109 00108 00110

Treatment (docs/title-logo.md): the brand is romanised (SakaTsuku), the pun 特大号 is romanised too (Tokudaigou, one
syllable group per hexagon / tile: TOKU DAI GOU), the tagline is translated, SEGA / Smilebit / J.LEAGUE stay.
"""
import os
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7bj_lib as L

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SRC = {
    '00101': 'build/tex/ATFIRST__TITLE.DAT/00101_TITLE.DAT_9.png',
    '00108': 'build/tex/ATFIRST__TITLEM.DAT/00108_TITLEM.DAT_6.png',
    '00109': 'build/tex/ATFIRST__TITLEM.DAT/00109_TITLEM.DAT_7.png',
    '00110': 'build/tex/ATFIRST__TITLEM.DAT/00110_TITLEM.DAT_8.png',
}
OUT = os.path.join(ROOT, 'build', 's7', 'titles', 'new')
TAGLINE = "Let's Make a Pro Soccer Club!"
RED_G = [(0, '#ff3a3a'), (0.55, '#e81818'), (1, '#b80c0c')]


def load(i):
    return np.asarray(Image.open(os.path.join(ROOT, SRC[i])).convert('RGBA')).copy()


def do_00101():
    a = load('00101')
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    # 1. kana: erase the red ink (and its dark-red rim) inside the four tiles
    tiles = {'SA': (92, 38, 80, 74), 'KA': (92, 120, 80, 76), 'TSU': (342, 40, 74, 64), 'KU': (342, 124, 70, 68)}
    red = (r - g > 45) & (r - b > 45) & (a[..., 3] > 0)
    mask = np.zeros(red.shape, bool)
    for k, (x, y, w, h) in tiles.items():
        mask[y:y + h, x:x + w] = red[y:y + h, x:x + w]
    mask = L.dilate(mask, 3)
    # 2. hexagon kanji: dark ink inside the three hex interiors
    hexes = [(205, 33, 28, 26), (243, 33, 27, 26), (281, 33, 26, 26)]
    lum = (r + g + b) // 3
    hm = np.zeros(red.shape, bool)
    for (x, y, w, h) in hexes:
        hm[y:y + h, x:x + w] = lum[y:y + h, x:x + w] < 150
    hm = L.dilate(hm, 1)
    # 3. tagline: katakana part of the strip (J.LEAGUE stays)
    tm = np.zeros(red.shape, bool)
    sx0, sx1, sy0, sy1 = 210, 404, 207, 225
    tm[sy0:sy1, sx0:sx1] = lum[sy0:sy1, sx0:sx1] < 130
    tm = L.dilate(tm, 1)
    full = mask | hm | tm
    a = L.inpaint(a, full, iters=300)
    img = Image.fromarray(a, 'RGBA')
    # draw kana replacements
    txt = {'SA': 'SA', 'KA': 'KA', 'TSU': 'TSU', 'KU': 'KU'}
    for k, (x, y, w, h) in tiles.items():
        # box = the old ink extents, a bit larger
        box = {'SA': (94, 40, 76, 70), 'KA': (94, 124, 76, 70), 'TSU': (342, 42, 76, 64), 'KU': (342, 126, 76, 66)}[k]
        L.paste_text(img, box, txt[k], font='impact', gradient=RED_G, outlines=[('#5a0606', 1.5)], shadow=('#1a0000', 1, 2),
                     shear=0.0, min_sx=0.8, max_h=58)
    # hexagon text
    for (x, y, w, h), t in zip(hexes, ['TOKU', 'DAI', 'GOU']):
        L.paste_text(img, (x - 1, y + 5, w + 2, 15), t, font='arial-black', fill='#1c2a78', outlines=[], shadow=('#9aa4c8', 1, 1),
                     min_sx=0.6, max_h=9, valign='middle')
    # tagline text
    L.paste_text(img, (216, 207, 187, 17), TAGLINE, font='arial-black', fill='#141414', outlines=[], min_sx=0.55, align='left')
    return img


def do_00109():
    a = load('00109')
    a[:, 141:, :] = 0
    img = Image.fromarray(a, 'RGBA')
    L.paste_text(img, (142, 1, 368, 30), TAGLINE, font='arial-black', fill='#ffffff', outlines=[('#000000', 2)], min_sx=0.55, align='left')
    return img


def ink_bbox(a):
    ys, xs = np.nonzero(a[..., 3] > 8)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def do_00108():
    a = load('00108')
    x0, y0, x1, y1 = ink_bbox(a)
    img = Image.new('RGBA', (512, 256), (0, 0, 0, 0))
    L.paste_text(img, (x0, y0, x1 - x0, y1 - y0), 'SakaTsuku', font='impact', gradient=[(0, '#ff3355'), (0.5, '#d6102f'), (1, '#9c0a22')],
                 outlines=[('#c9ccd2', 3), ('#1c1c20', 5)], shadow=None, shear=0.22, min_sx=0.7)
    return img


def do_00110():
    a = load('00110')
    x0, y0, x1, y1 = ink_bbox(a)
    img = Image.new('RGBA', (512, 128), (0, 0, 0, 0))
    L.paste_text(img, (x0, y0, x1 - x0, y1 - y0), 'SakaTsuku', font='impact', fill='#000000', outlines=[('#000000', 4)], shear=0.22, min_sx=0.7)
    return img


FUNCS = {'00101': do_00101, '00109': do_00109, '00108': do_00108, '00110': do_00110}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for i in sys.argv[1:]:
        im = FUNCS[i]()
        im.save(os.path.join(OUT, i + '.png'))
        print(i, im.size)
