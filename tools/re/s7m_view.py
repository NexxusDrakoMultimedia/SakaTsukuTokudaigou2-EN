"""s7m_view OUT.png SCALE src tid [src tid ...] : original | installed side by side (magenta = transparent)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7m_lib as L
import numpy as np
from PIL import Image
a = sys.argv[1:]
out, scale = a[0], int(a[1])
rest = a[2:]
rows = []
for i in range(0, len(rest), 2):
    src, tid = rest[i], rest[i + 1]
    t = L.load(src, tid)
    p = L.tex_path(src, tid)
    ims = [Image.fromarray(t['arr'].astype(np.uint8), 'RGBA')]
    if os.path.exists(p):
        with open(p, 'rb') as f:
            ims.append(Image.fromarray(np.asarray(L.pvr.decode(f.read())).astype(np.uint8), 'RGBA'))
    row = []
    for im in ims:
        b = Image.new('RGBA', im.size, (255, 0, 255, 255)); b.alpha_composite(im); row.append(b.convert('RGB'))
    rows.append(row)
W = max(sum(i.width + 4 for i in r) for r in rows); H = sum(max(i.height for i in r) + 4 for r in rows)
c = Image.new('RGB', (W, H), (40, 40, 40)); y = 0
for r in rows:
    x = 0
    for i in r:
        c.paste(i, (x, y)); x += i.width + 4
    y += max(i.height for i in r) + 4
c = c.resize((c.width * scale, c.height * scale), Image.NEAREST); c.save(out); print(out, c.size)
