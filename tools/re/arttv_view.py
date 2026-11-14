import sys, glob, os
from PIL import Image
ids = sys.argv[2:]
S = int(sys.argv[1])
rows = []
for t in ids:
    a = Image.open(glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/%s_*.png' % t)[0]).convert('RGBA')
    b = Image.open('build/art_tv/%s.dec.png' % t).convert('RGBA')
    rows.append((a, b))
W = sum(a.width for a, b in rows[:1]) * 2
import math
H = sum(a.height for a, b in rows)
m = Image.new('RGB', (rows[0][0].width * 2, H), (100, 100, 100))
y = 0
for a, b in rows:
    for i, im in enumerate((a, b)):
        bg = Image.new('RGBA', im.size, (100, 100, 100, 255)); bg.alpha_composite(im)
        m.paste(bg.convert('RGB'), (i * a.width, y))
    y += a.height
m = m.resize((m.width * S, m.height * S), Image.NEAREST)
m.save('build/art_tv/view.png')
