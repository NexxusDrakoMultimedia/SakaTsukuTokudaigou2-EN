"""am2_crop - zoomed before|after crops. python -I -X utf8 tools/re/am2_crop.py OUT.png SCALE  DIR:ID:x:y:w:h ...
DIR is a build dir containing orig/ID.png (before) and new/ID.dec.png (after), e.g. build/art1 or build/art5."""
import sys, os
from PIL import Image
out, scale = sys.argv[1], int(sys.argv[2])
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
rows = []
for a in sys.argv[3:]:
    d, i, x, y, w, h = a.split(':')
    x, y, w, h = int(x), int(y), int(w), int(h)
    base = os.path.join(ROOT, d)
    b = Image.open(os.path.join(base, 'orig', i + '.png')).convert('RGBA').crop((x, y, x + w, y + h))
    n = Image.open(os.path.join(base, 'new', i + '.dec.png')).convert('RGBA').crop((x, y, x + w, y + h))
    row = Image.new('RGBA', (w * 2 * scale + 8, h * scale), (255, 0, 255, 255))
    for k, im in enumerate((b, n)):
        bg = Image.new('RGBA', im.size, (90, 90, 90, 255))
        bg.alpha_composite(im)
        row.paste(bg.resize((w * scale, h * scale), Image.NEAREST), (k * (w * scale + 8), 0))
    rows.append(row)
W = max(r.width for r in rows)
H = sum(r.height + 6 for r in rows)
sheet = Image.new('RGBA', (W, H), (40, 40, 40, 255))
y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.height + 6
sheet.save(out)
print(out, sheet.size)
