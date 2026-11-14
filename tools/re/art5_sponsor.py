"""art5_sponsor - SPONSOR.DAT #0 (03816), ARGB1555 (1-bit alpha)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L

CLR = {'mode': 'clear'}
HG = {'mode': 'hgrad'}


def r(i, t, x, y, w, h, erase, size, align='center', **kw):
    d = {'id': i, 'text': t, 'x': x, 'y': y, 'w': w, 'h': h, 'erase': erase, 'font': ['arial-black'],
         'size': 'auto', 'max_size': size, 'min_sx': 0.7, 'align': align, 'valign': 'middle', 'pad': 0}
    d.update(kw)
    return d


YEL = {'gradient': [[0, '#f8f8a0'], [1, '#c8b820']], 'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0},
       'outline': {'color': '#202000', 'width': 0.9}}
regs = [
    r('title', 'New Sponsor List', 1, 0, 276, 23, CLR, 22, 'left', aa=False,
      gradient=[[0, '#ffb060'], [1, '#e05818']], shadow={'color': '#101870', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}),
    r('income', 'Annual Income', 33, 27, 118, 19, HG, 16, **YEL),
    r('term', 'Term', 6, 51, 90, 26, None, 20, **YEL),
    r('capital', 'Capital', 6, 83, 54, 26, None, 16, **YEL),
    r('emp', 'Employees', 6, 115, 90, 26, None, 20, **YEL),
    r('cond', 'Conditions', 6, 147, 90, 26, None, 20, **YEL),
    r('newsp', 'New Sponsor', 306, 26, 122, 19,
      {'mode': 'mask', 'ink': [{'color': [56, 72, 168], 'tol': 90}, {'luma_lt': 70}], 'dilate': 1, 'fill': 'hfill'}, 15,
      fill='#3848a8', shadow={'color': '#f0f090', 'dx': 1, 'dy': 1, 'alpha': 0.9}),
    r('cur', 'Current Sponsor', 3, 181, 121, 18, None, 13,
      fill='#583880', shadow={'color': '#f0e080', 'dx': 1, 'dy': 1, 'alpha': 0.9}),
    r('exit', 'Exit', 20, 203, 92, 27, HG, 24,
      gradient=[[0, '#fff0a0'], [1, '#b08020']], shadow={'color': '#302010', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}),
    r('curlist', 'Current Sponsor List', 130, 192, 272, 26, CLR, 21, 'left', aa=False,
      gradient=[[0, '#f8ffb0'], [1, '#c8e868']], shadow={'color': '#303888', 'dx': 2, 'dy': 2, 'alpha': 1.0}),
    r('status', 'Sponsor Status', 130, 218, 224, 22, CLR, 21, 'left', aa=False,
      gradient=[[0, '#f8ffb0'], [1, '#c8e868']], shadow={'color': '#303888', 'dx': 2, 'dy': 2, 'alpha': 1.0}),
]
im = L.load('03816')
for y0, xc, xe in ((51, 97, 95), (83, 58, 59), (115, 97, 95), (147, 97, 95)):
    for y in range(y0, y0 + 26):
        px = im.getpixel((xc, y))
        for x in range(6, xe + 1):
            im.putpixel((x, y), px)
for y in range(181, 199):
    yel = im.getpixel((2, y)); grn = im.getpixel((124, y))
    for x in range(3, 125):
        green = x >= 80 and y < 177 + 0.467 * (x - 80)
        im.putpixel((x, y), grn if green else yel)
L.finish('03816', L.render('03816', {'regions': regs}, im))
