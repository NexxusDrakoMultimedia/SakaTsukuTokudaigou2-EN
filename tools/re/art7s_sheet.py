import sys
from PIL import Image, ImageDraw
W = 1100
ids = sys.argv[2:]
out = sys.argv[1]
items = [(i, Image.open('build/art7/v/%s_ba.png' % i).convert('RGB')) for i in ids]
rows = []; cur = []; cw = 0
for i, im in items:
    if im.width > W:
        im = im.resize((W, int(im.height * W / im.width)))
    if cw + im.width + 6 > W and cur:
        rows.append(cur); cur = []; cw = 0
    cur.append((i, im)); cw += im.width + 6
if cur: rows.append(cur)
H = sum(max(im.height for _, im in r) + 14 for r in rows)
sheet = Image.new('RGB', (W, H), (90, 90, 120)); d = ImageDraw.Draw(sheet)
y = 0
for r in rows:
    x = 0
    for i, im in r:
        d.text((x + 2, y), i, fill=(255, 255, 0)); sheet.paste(im, (x, y + 12)); x += im.width + 6
    y += max(im.height for _, im in r) + 14
sheet.save(out)
print(out, sheet.size)
