"""skart2_sheet - skeptic: before/after PNG per texture id (decoded from extracted/ and from translation/textures).
python -I -X utf8 tools/re/skart2_sheet.py OUTDIR ID [ID ...]
Writes OUTDIR/ID.png (before on top, after below, grey background, magnified so width ~ 900) and prints
the format, size and whether the repainted file exists / differs from the original."""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L
import pvr

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
for i in sys.argv[2:]:
    try:
        src, tid, d = L.resolve(i)
    except KeyError as e:
        print(i, 'UNRESOLVED', e)
        continue
    o = L.load(i)
    p = L.tex_path(src, tid)
    if not os.path.exists(p):
        print(i, src, tid, 'NO REPAINT FILE')
        continue
    newb = open(p, 'rb').read()
    new = np.asarray(pvr.decode(newb)).copy()
    h, w = o['arr'].shape[:2]
    same = (o['pvr'] == newb)
    print(i, src, tid, '%dx%d' % (w, h), 'new shape', new.shape[:2], 'IDENTICAL-TO-ORIG' if same else 'changed', 'bytes', len(o['pvr']), len(newb))
    sc = max(1, min(8, 900 // w))
    ims = []
    for a in (o['arr'], new):
        im = Image.fromarray(a.astype('uint8'), 'RGBA')
        bg = Image.new('RGBA', im.size, (110, 110, 110, 255))
        bg.alpha_composite(im)
        ims.append(bg.resize((w * sc, h * sc), Image.NEAREST))
    sheet = Image.new('RGBA', (w * sc, h * sc * 2 + 6), (255, 0, 255, 255))
    sheet.paste(ims[0], (0, 0))
    sheet.paste(ims[1], (0, h * sc + 6))
    sheet.convert('RGB').save(os.path.join(out, i + '.png'))
