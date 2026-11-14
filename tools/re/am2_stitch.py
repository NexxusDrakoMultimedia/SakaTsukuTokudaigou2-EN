"""am2_stitch - view two tiles side by side: am2_stitch.py OUT.png DIR LEFT RIGHT x y w h scale  (new/dec and orig stacked)"""
import sys, os
from PIL import Image
out, d, a, b = sys.argv[1:5]
x, y, w, h, sc = map(int, sys.argv[5:10])
rows = []
for kind in ('orig', 'new'):
    ims = []
    for i in (a, b):
        p = os.path.join(d, kind, i + ('.png' if kind == 'orig' else '.dec.png'))
        ims.append(Image.open(p).convert('RGBA'))
    c = Image.new('RGBA', (ims[0].width + ims[1].width, ims[0].height))
    c.paste(ims[0], (0, 0)); c.paste(ims[1], (ims[0].width, 0))
    c = c.crop((x, y, x + w, y + h))
    bg = Image.new('RGBA', c.size, (90, 90, 90, 255)); bg.alpha_composite(c)
    rows.append(bg.resize((w * sc, h * sc), Image.NEAREST))
s = Image.new('RGBA', (rows[0].width, rows[0].height * 2 + 6), (255, 0, 255, 255))
s.paste(rows[0], (0, 0)); s.paste(rows[1], (0, rows[0].height + 6))
s.save(out)
