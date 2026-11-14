"""Montage helper: crop decoded texture PNGs to their ink bbox and tile them at Nx with labels.
usage: python -I -X utf8 tools/re/cw_zoom.py OUT.png SCALE COLS id1 id2 ...   (id = numeric texture id, e.g. 10824)
Looks the PNG up in build/tex/*/<id>_*.png."""
import sys, glob, os
from PIL import Image, ImageDraw
root = 'build/tex'
out, scale, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ids = sys.argv[4:]
tiles = []
for i in ids:
    g = glob.glob(f'{root}/*/{int(i):05d}_*.png')
    if not g:
        print('missing', i); continue
    im = Image.open(g[0]).convert('RGBA')
    a = im.split()[3]
    bb = a.getbbox() or (0, 0, im.width, im.height)
    pad = 4
    bb = (max(bb[0]-pad,0), max(bb[1]-pad,0), min(bb[2]+pad,im.width), min(bb[3]+pad,im.height))
    c = im.crop(bb)
    bg = Image.new('RGBA', c.size, (110, 110, 118, 255))
    bg.alpha_composite(c)
    bg = bg.resize((bg.width*scale, bg.height*scale), Image.NEAREST)
    tiles.append((i, bg))
if not tiles:
    sys.exit(1)
cw = max(t[1].width for t in tiles) + 8
ch = max(t[1].height for t in tiles) + 24
rows = (len(tiles)+cols-1)//cols
sheet = Image.new('RGB', (cw*cols, ch*rows), (60, 60, 70))
d = ImageDraw.Draw(sheet)
for k, (i, im) in enumerate(tiles):
    x, y = (k % cols)*cw, (k//cols)*ch
    d.text((x+4, y+4), str(i), fill=(255, 255, 0))
    sheet.paste(im.convert('RGB'), (x+4, y+20))
sheet.save(out)
print(out, sheet.size)
