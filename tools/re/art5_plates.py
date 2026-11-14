"""art5_plates - PLATE.ZAR money plates (digits kept, unit repainted)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import art5_lib as L

UNIT_STYLE = {'font': ['arial-narrow-bold', 'arial-bold'],
              'gradient': [[0, '#ffffff'], [1, '#c8c8c8']],
              'shadow': {'color': '#202020', 'dx': 1, 'dy': 1, 'alpha': 1.0}}


VAR = [0]


def reg(text, x, y, w, h, size=22, align='center', valign='bottom'):
    d = {'id': 'unit', 'text': text, 'x': x, 'y': y, 'w': w, 'h': h, 'erase': None,
         'size': 'auto', 'max_size': size, 'min_sx': 0.8, 'align': align, 'valign': valign, 'pad': 0}
    d.update(UNIT_STYLE)
    if VAR[0] >= 1:
        d.pop('gradient')
        d['fill'] = '#e6e6e6'
    if VAR[0] >= 2:
        d['aa'] = False
    if VAR[0] >= 3:   # am2: no shadow either (the wider 'Yen' plates only fit this way)
        d.pop('shadow', None)
    return d


def fin(i, build):
    for v in (0, 1, 2, 3):
        VAR[0] = v
        img = build()
        if L.over(i, img) <= 0:
            break
    else:
        print('STILL OVER', i)
    L.finish(i, img)
    print(i, 'variant', v)


def shift_left(img, n, upto):
    a = np.array(img)
    out = np.zeros_like(a)
    out[:, :upto - n] = a[:, n:upto]
    return Image.fromarray(out, 'RGBA')


def clear_from(img, x0):
    a = np.array(img)
    a[:, x0:] = 0
    return Image.fromarray(a, 'RGBA')


T = {'03555': 1000, '03556': 2000, '03557': 3000, '03558': 4000, '03559': 5000, '03560': 8000}
P = {'03563': 1000, '03564': 2000, '03565': 3000, '03566': 4000, '03567': 5000, '03568': 8000}
for i in T:
    fin(i, lambda: L.render(i, {'regions': [reg('Yen', 97, 3, 28, 23, 18)]}, clear_from(L.load(i), 97)))
for i in P:
    fin(i, lambda: L.render(i, {'regions': [reg('man', 85, 8, 42, 20, 18, 'left')]}, shift_left(L.load(i), 12, 96)))
fin('03562', lambda: L.render('03562', {'regions': [reg('Yen', 97, 3, 28, 23, 18)]}, clear_from(L.load('03562'), 96)))


def one(i, txt):
    a = np.array(L.load(i)); a[:, 53:] = 0
    return L.render(i, {'regions': [reg(txt, 56, 8, 70, 20, 17, 'left')]}, Image.fromarray(a, 'RGBA'))


fin('03561', lambda: one('03561', 'man'))
fin('03569', lambda: one('03569', 'oku'))
