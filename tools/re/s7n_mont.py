"""s7n: labelled montage of decoded textures.  usage: s7n_mont.py out.png cols first last [scale]
Reads build/tex/index.tsv, writes build/tex/classify/<out>."""
import os, sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEX = os.path.join(ROOT, 'build', 'tex')
out, cols, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
scale = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
idx = {}
for ln in open(os.path.join(TEX, 'index.tsv'), encoding='utf8'):
    c = ln.split('\t')
    if not c[0][:5].isdigit():
        continue
    idx[int(c[0][:5])] = os.path.join(TEX, c[1].replace('/', '__'), c[0] + '.png')
ims = []
for i in range(a, b + 1):
    im = Image.open(idx[i]).convert('RGBA')
    bg = Image.new('RGBA', im.size, (110, 110, 110, 255))
    bg.alpha_composite(im)
    if scale != 1:
        bg = bg.resize((int(bg.width * scale), int(bg.height * scale)), Image.LANCZOS)
    ims.append((i, bg))
cw = max(im.width for _i, im in ims) + 4
ch = max(im.height for _i, im in ims) + 14
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cw * cols, ch * rows), (40, 40, 40))
d = ImageDraw.Draw(sheet)
for k, (i, im) in enumerate(ims):
    x, y = (k % cols) * cw, (k // cols) * ch
    d.text((x + 2, y + 1), str(i), fill=(255, 255, 0))
    sheet.paste(im.convert('RGB'), (x, y + 13))
sheet.save(os.path.join(TEX, 'classify', out))
print(out, sheet.size)
