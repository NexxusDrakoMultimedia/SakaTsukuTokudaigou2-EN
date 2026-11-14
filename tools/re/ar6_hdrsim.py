"""ar6_hdrsim: simulate the header composition: digit sprites right-aligned against the old kanji's left ink edge (the Japanese
layout's anchor), unit cells from the old / new BAR texture.  Reports ink overlap (px) digit-vs-unit for months 1-12 and weeks 1-4,
and writes build/ar6/hdrsim.png.   ar6_hdrsim.py [NEW.png]"""
import os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OLD = np.asarray(Image.open(os.path.join(ROOT, 'build', 'art1', 'orig', '00002.png')).convert('RGBA')).astype(int)
NEWP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'build', 'art1', 'new', '00002.png')
NEW = np.asarray(Image.open(NEWP).convert('RGBA')).astype(int)
PREV = np.asarray(Image.open(os.path.join(ROOT, 'build', 'ar6', 'art1_new_before', '00002.png')).convert('RGBA')).astype(int)
# digit sprites: the white row 1234567890 of the sheet (x 305..462, y 428..458), cell pitch 15.7
DX0, DW, DY0, DY1 = 305, 15.7, 428, 458
def digit(d):
    k = (d - 1) % 10
    x0 = int(round(DX0 + k * DW)); x1 = int(round(DX0 + (k + 1) * DW))
    return OLD[DY0:DY1, x0:x1].copy()
UNITS = {'mo': (264, 36, 66), 'wk': (300, 36, 66), 'yr': (201, 36, 66)}   # old kanji left edge, rows
def unit_ink(img, name):
    x, y0, y1 = UNITS[name]
    reg = {'mo': (258, 290), 'wk': (294, 330), 'yr': (196, 240)}[name]
    sub = img[y0:y1, reg[0]:reg[1]]
    m = (sub[..., 3] > 128) & (sub[..., :3].min(-1) > 200)
    return m, reg
def overlap(img, name, dgt, gap=1):
    m, reg = unit_ink(img, name)
    anchor = UNITS[name][0] - gap     # digit sprite right edge (exclusive)
    d = digit(dgt)
    dm = (d[..., 3] > 128) & (d[..., :3].min(-1) > 200)
    dw = d.shape[1]
    # digit ink mask placed at anchor-dw .. anchor on the same rows as unit (rows y0..y1 height 30; digit height 30)
    h = min(dm.shape[0], m.shape[0])
    tot = 0
    for r in range(h):
        for c in range(dw):
            if dm[r, c]:
                x = anchor - dw + c - reg[0]
                if 0 <= x < m.shape[1] and m[r, x]:
                    tot += 1
    return tot
for nm, img in (('old kanji', OLD), ('previous', PREV), ('new', NEW)):
    res = []
    for name, ds in (('mo', range(1, 10)), ('wk', range(1, 5))):
        res.append('%s %d' % (name, sum(overlap(img, name, d) for d in ds)))
    print('%-10s overlap px (digit ink over unit ink): %s' % (nm, ', '.join(res)))
# picture: rows of 'N yr M mo W wk' for old/prev/new, digits right-aligned at the anchors, month 12 and week 4
def compose(img, mo, wk):
    out = img[30:70, 190:345].copy()
    for name, ds in (('mo', [int(c) for c in str(mo)]), ('wk', [wk])):
        a = UNITS[name][0] - 1
        for d in reversed(ds):
            g = digit(d)
            gw = g.shape[1]
            x = a - gw - 190
            for r in range(min(g.shape[0], 40)):
                for c in range(gw):
                    if g[r, c, 3] > 100 and 0 <= x + c < out.shape[1] and r + 4 < out.shape[0]:
                        out[r + 4, x + c] = g[r, c]
            a -= gw
    return out
rows = []
for img in (OLD, PREV, NEW):
    for mo, wk in ((12, 4), (2, 3)):
        c = compose(img, mo, wk)
        b = Image.new('RGBA', (c.shape[1], c.shape[0]), (120, 0, 120, 255))
        b.alpha_composite(Image.fromarray(c.astype(np.uint8), 'RGBA'))
        rows.append(b.convert('RGB').resize((c.shape[1] * 4, c.shape[0] * 4), Image.NEAREST))
H = sum(r.height + 3 for r in rows)
o = Image.new('RGB', (rows[0].width, H), (20, 20, 20))
y = 0
for r in rows:
    o.paste(r, (0, y)); y += r.height + 3
o.save(os.path.join(ROOT, 'build', 'ar6', 'hdrsim.png'))
