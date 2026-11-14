"""art5_sheet - contact sheet of group-5 PNGs.  art5_sheet.py OUT.png SCALE COLS DIR id id ..."""
import sys
from PIL import Image, ImageDraw
out, scale, cols, d = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
ids = sys.argv[5:]
ims = []
for i in ids:
    im = Image.open('%s/%s.png' % (d, i)).convert('RGBA')
    bg = Image.new('RGBA', im.size, (90, 90, 90, 255))
    bg.alpha_composite(im)
    ims.append((i, bg.resize((im.width * scale, im.height * scale), Image.NEAREST)))
cw = max(m.width for _, m in ims) + 4
ch = max(m.height for _, m in ims) + 16
rows = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (cw * cols, ch * rows), (40, 40, 40))
dr = ImageDraw.Draw(S)
for k, (i, m) in enumerate(ims):
    x, y = (k % cols) * cw, (k // cols) * ch
    dr.text((x + 2, y + 1), i, fill=(255, 255, 0))
    S.paste(m.convert('RGB'), (x + 2, y + 14))
S.save(out)
