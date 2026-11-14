"""art5_sche - SCHE1 03589 / 03590 and MONTH 03323."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L

WHITE = {'gradient': [[0, '#ffffff'], [1, '#c8c8c8']], 'outline': {'color': '#000000', 'width': 0.8},
         'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}


def r(i, text, x, y, w, h, erase, size=20, wrap=False, **kw):
    d = {'id': i, 'text': text, 'x': x, 'y': y, 'w': w, 'h': h, 'erase': erase, 'font': ['arial-bold'],
         'size': 'auto', 'max_size': size, 'min_sx': 0.75, 'align': 'center', 'valign': 'middle', 'wrap': wrap,
         'line_spacing': 0.85, 'pad': 0}
    d.update(kw)
    return d


CLR = {'mode': 'clear'}
HG = {'mode': 'hgrad'}
regs = [
    r('b1', 'Back', 6, 222, 40, 28, HG, 20, fill='#000018'),
    r('b2', 'Back', 54, 222, 40, 28, HG, 20, fill='#001030'),
    r('bw', 'Back', 100, 214, 44, 24, CLR, 20, **WHITE),
]
L.finish('03589', L.render('03589', {'regions': regs}))

DK = {'mode': 'flat', 'color': [153, 0, 0, 255]}
regs = [
    r('prevA', 'Prev\nMonth', 216, 19, 32, 17, DK, 9, wrap=True, fill='#1c0000'),
    r('nextA', 'Next\nMonth', 216, 44, 32, 17, DK, 9, wrap=True, fill='#1c0000'),
    r('nextA2', None, 217, 60, 31, 3, DK, 9),
    r('nextA3', None, 220, 63, 22, 2, DK, 9),
    r('done1', 'Done', 168, 90, 34, 19, None, 15, fill='#001830'),
    r('done2', 'Done', 214, 90, 38, 19, None, 15, fill='#000820'),
    r('wprev', 'Prev\nMonth', 158, 120, 36, 22, CLR, 11, wrap=True, **WHITE),
    r('wdone', 'Done', 204, 120, 44, 22, CLR, 18, **WHITE),
    r('wnext', 'Next\nMonth', 176, 148, 36, 20, CLR, 11, wrap=True, **WHITE),
    r('w2nd', '2nd', 213, 148, 43, 20, CLR, 20, **WHITE),
    r('w1st', '1st', 182, 173, 46, 20, CLR, 20, **WHITE),
    r('wk1', 'Wk 1', 178, 199, 38, 26, CLR, 20, **WHITE),
    r('wk2', 'Wk 2', 218, 199, 38, 26, CLR, 20, **WHITE),
    r('wk3', 'Wk 3', 178, 231, 38, 25, CLR, 20, **WHITE),
    r('wk4', 'Wk 4', 218, 231, 38, 25, CLR, 20, **WHITE),
]
for d in regs:
    if d['text'] is None:
        del d['text']
im = L.load('03590')
for xa, xb, xc in ((165, 204, 164), (212, 253, 211)):
    for y in range(89, 110):
        px = im.getpixel((xc, y))
        for x in range(xa, xb + 1):
            im.putpixel((x, y), px)
L.finish('03590', L.render('03590', {'regions': regs}, im))

PK = {'gradient': None}
def pk(i, t, x, y, w, h):
    return r(i, t, x, y, w, h, {'mode': 'flat'}, 19, font=['arial-black'], fill='#ffff00',
             shadow={'color': '#666600', 'dx': 1, 'dy': 1, 'alpha': 1.0})
regs = [pk('et', 'ET', 134, 155, 52, 21), pk('first', '1st', 134, 179, 52, 21), pk('second', '2nd', 134, 203, 52, 20)]
L.finish('03323', L.render('03323', {'regions': regs}))
print('ok')
