"""art5_invest - INVEST.DAT #1 (02227) and #2 (02228)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import art5_lib as L


def hexc(c):
    return '#%02x%02x%02x' % tuple(int(v) for v in c[:3])


def sample_grad(img, rect):
    x, y, w, h = rect
    a = np.asarray(img.convert('RGBA'))[y:y + h, x:x + w].astype(float)
    luma = a[:, :, :3] @ np.array([0.299, 0.587, 0.114])
    thr = luma.max() * 0.8
    m = luma >= thr
    ys = np.where(m.any(1))[0]
    n = len(ys)
    top = a[ys[0]:ys[0] + max(1, n // 3)][m[ys[0]:ys[0] + max(1, n // 3)]][:, :3].mean(0)
    bot = a[ys[-1] - max(1, n // 3) + 1:ys[-1] + 1][m[ys[-1] - max(1, n // 3) + 1:ys[-1] + 1]][:, :3].mean(0)
    return [[0, hexc(top)], [1, hexc(bot)]]


UNIT_MK = {'mode': 'mask', 'ink': [{'luma_gt': 92}, {'luma_lt': 14}], 'dilate': 1, 'fill': 'hfill'}
CAP_MK = {'mode': 'mask', 'ink': [{'sat_lt': 0.3, 'luma_gt': 100}, {'luma_lt': 14}], 'dilate': 1, 'fill': 'diffuse'}


def box(img, cap, yc):
    g1 = sample_grad(img, (76, yc + 24, 30, 30))
    g2 = sample_grad(img, (204, yc + 24, 52, 30))
    base = {'font': ['arial-black'], 'outline': {'color': '#000000', 'width': 1.4}, 'size': 'auto', 'min_sx': 0.7,
            'valign': 'middle', 'pad': 0}
    c = dict(base, id='cap', text=cap, x=20, y=yc - 2, w=122, h=17, erase_rect=[20, yc - 2, 122, 18], erase=CAP_MK, font=['arial-bold'],
             gradient=[[0, '#ffffff'], [1, '#c8c8c8']], max_size=15, align='left',
             shadow={'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 0.8})
    u1 = dict(base, id='oku', text='oku', x=72, y=yc + 21, w=42, h=37, erase={'mode': 'hgrad'}, gradient=g1, max_size=19, align='center')
    u2 = dict(base, id='man', text='man', x=196, y=yc + 21, w=60, h=37, erase={'mode': 'hgrad'}, gradient=g2, max_size=22, align='center')
    return [c, u1, u2]


def linefix(im, ycs):
    for yc in ycs:
        for x in range(33, 141):
            im.putpixel((x, yc + 15), (236, 236, 248, 255))
            im.putpixel((x, yc + 16), (0, 0, 8, 255))


img = L.load('02227')
regs = box(img, 'Economy Investment', 333) + box(img, 'Housing Investment', 421)
SW = {'id': 'sw', 'text': 'Switch Total', 'x': 248, 'y': 84, 'w': 108, 'h': 24}
LBL = dict(erase={'mode': 'clear'}, font=['arial-bold'], gradient=[[0, '#ffffff'], [1, '#98c8f0']],
           outline={'color': '#000000', 'width': 1.0}, shadow={'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0},
           size='auto', max_size=24, min_sx=0.75, align='left', valign='middle', pad=0)
rows = [('Switch Total', 84, 24), ('Economy', 117, 25), ('Housing', 149, 25), ('Sports', 181, 25), ('Transport', 213, 25)]
for t, y, h in rows:
    regs.append(dict(LBL, id=t, text=t, x=248, y=y, w=108, h=h))
HEAD = dict(font=['arial-black'], gradient=[[0, '#fff200'], [0.5, '#ffc800'], [1, '#e08800']], outline={'color': '#000000', 'width': 2},
            shadow={'color': '#909090', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}, size='auto', max_size=34, min_sx=0.8, align='center',
            valign='middle', pad=0, erase=None)
regs.append(dict(HEAD, id='h1', text='Total to Date', x=10, y=0, w=304, h=44))
regs.append(dict(HEAD, id='h2', text="This Month's Total", x=10, y=44, w=214, h=38))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def replate(im, x1, lo, hi, bot, xa, xb, ytop, ybot):
    """rebuild a stepped brown plate: per-row colours from the clean right end, noise like the original"""
    a = np.array(im).astype(float)
    rng = np.random.RandomState(5)
    right = a[:, x1 - 8:x1 - 1]
    left = a[:, 0:8]
    rows = {}
    for y in range(hi, bot + 1):
        px = right[y]
        px = px[px[:, 3] > 200]
        rows[y] = (px.mean(0), px[:, :3].std(0) if len(px) > 1 else np.zeros(3))
    mid = np.mean([rows[y][0] for y in range(hi + 4, bot - 3)], 0)
    sd = np.mean([rows[y][1] for y in range(hi + 4, bot - 3)], 0)
    for x in range(9, x1 - 8):
        top = lo + (hi - lo) * smooth((x - xa) / float(xb - xa))
        top_i = int(round(top))
        for y in range(ytop, ybot + 1):
            if y < top_i or y > bot:
                a[y, x] = 0
                continue
            d = y - top_i
            if d < 3:
                base, s = rows[hi + d]
            elif y > bot - 3:
                base, s = rows[y]
            else:
                base, s = mid, sd
            c = base.copy()
            c[:3] += rng.normal(0, 1, 3).mean() * s[:3] * 0.9
            c[3] = 255
            a[y, x] = c
    return L.Image.fromarray(np.clip(np.rint(a), 0, 255).astype(np.uint8), 'RGBA')


img = replate(img, 319, 24, 9, 38, 215, 233, 0, 44)
img = replate(img, 222, 64, 48, 78, 193, 207, 44, 79)
out = L.render('02227', {'regions': regs}, img)
linefix(out, (333, 421))
L.finish('02227', out)

img = L.load('02228')
regs = box(img, 'Sports Investment', 21) + box(img, 'Transport Invest.', 109)
out = L.render('02228', {'regions': regs}, img)
linefix(out, (21, 109))
L.finish('02228', out)
