"""s7c_zoom OUT.png SCALE member [member...] : crop top 72 rows of the original textures, RGB over dark grey, scaled."""
import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7c_dump as D
import numpy as np
from PIL import Image
out, sc = sys.argv[1], int(sys.argv[2])
rows = []
for m in sys.argv[3:]:
    if m.endswith('.png'):
        a = np.asarray(Image.open(m).convert('RGBA'))
    else:
        a = D.load(m)[1]
    im = Image.fromarray(a[:72].astype(np.uint8), 'RGBA')
    bg = Image.new('RGBA', im.size, (90, 90, 110, 255)); bg.alpha_composite(im)
    rows.append(bg.convert('RGB').resize((im.width * sc, im.height * sc), Image.NEAREST))
c = Image.new('RGB', (rows[0].width, sum(r.height + 4 for r in rows)), (40, 0, 40))
y = 0
for r in rows:
    c.paste(r, (0, y)); y += r.height + 4
c.save(out)
