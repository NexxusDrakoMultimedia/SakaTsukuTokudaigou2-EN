"""Montage of unique BINDUNIF bdyf.bin (kit front) textures. usage: cw_kitsheet.py OUTPREFIX COLS ROWS SCALE [member=bdyf.bin]"""
import sys, csv, glob, os
from PIL import Image, ImageDraw
pre, cols, rows, sc = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
mem = sys.argv[5] if len(sys.argv) > 5 else 'bdyf.bin'
ids = []
for l in open('build/tex/index.tsv', encoding='utf8'):
    f = l.rstrip('\n').split('\t')
    if f[1] == 'GAME/BINDUNIF.BIN' and f[0].split('_', 1)[1].rsplit('_', 1)[0] == mem and not f[10]:
        ids.append(f[0])
print(len(ids), 'unique', mem)
per = cols*rows
for p in range(0, len(ids), per):
    chunk = ids[p:p+per]
    cell = 128*sc
    sh = Image.new('RGB', (cols*(cell+2), rows*(cell+14)), (50, 50, 60))
    d = ImageDraw.Draw(sh)
    for k, name in enumerate(chunk):
        g = glob.glob(f'build/tex/GAME__BINDUNIF.BIN/{name}.png')
        if not g: continue
        im = Image.open(g[0]).convert('RGB').resize((cell, cell), Image.LANCZOS if sc > 1 else Image.NEAREST)
        x, y = (k % cols)*(cell+2), (k//cols)*(cell+14)
        d.text((x+2, y+1), name.split('_')[0], fill=(255, 255, 0))
        sh.paste(im, (x, y+13))
    fn = f'{pre}_{p//per+1:02d}.png'
    sh.save(fn); print(fn, sh.size)
