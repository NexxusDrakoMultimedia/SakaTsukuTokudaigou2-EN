"""s7e_flash [--write]: 03342 (NEWSOPED studio*.tbd#0) = blurred black shadow/reflection of the 速報 glyphs of 03344.
Built from the alpha of the installed 03344 (FLASH): smear downwards with a fade, blur, rgb 0, alpha cap 0xCC like the original."""
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageFilter
import art7_lib as L
import pvr

write = '--write' in sys.argv
t44 = L.load('03344')
cur = np.asarray(pvr.decode(open(L.tex_path(t44['src'], t44['tid']), 'rb').read())).copy()
al = (cur[..., 3] >= 128).astype(float)
t = L.load('03342')
H, W = al.shape
sh = np.zeros((H, W))
for k in range(0, 20):
    f = 1.0 if k < 8 else max(0.0, 1 - (k - 7) / 13.0)
    s = np.zeros_like(al)
    s[k:] = al[:H - k]
    sh = np.maximum(sh, s * f)
img = Image.fromarray((sh * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(0.9))
a = np.asarray(img).astype(float) / 255.0
a = np.minimum(a * 204, 204).astype(np.uint8)
out = np.zeros((H, W, 4), np.uint8)
out[..., 3] = a
new = pvr.encode(out, original=t['pvr'])
dec = np.asarray(pvr.decode(new)).copy()
bg = Image.new('RGBA', (W, H), (110, 110, 130, 255))
bg.alpha_composite(Image.fromarray(dec.astype(np.uint8), 'RGBA'))
o44 = Image.fromarray(cur.astype(np.uint8), 'RGBA')
b2 = Image.new('RGBA', (W, H), (110, 110, 130, 255))
b2.alpha_composite(Image.fromarray(t['arr'].astype(np.uint8), 'RGBA'))
c = Image.new('RGB', (W * 3 + 8, H), (60, 0, 60))
c.paste(b2.convert('RGB'), (0, 0)); c.paste(bg.convert('RGB'), (W + 4, 0))
b3 = Image.new('RGBA', (W, H), (110, 110, 130, 255)); b3.alpha_composite(bg); b3.alpha_composite(o44)
c.paste(b3.convert('RGB'), (2 * W + 8, 0))
c = c.resize((c.width * 3, c.height * 3), Image.NEAREST)
c.save(os.path.join(L.ROOT, 'build', 's7', 'e', 'ba_03342.png'))
bad = [r for r in L.fit_report(new, t) if not r[2]]
print('fit problems', bad)
if write and not bad:
    for src, tid in L.dups(t['src'], t['tid']):
        p = L.tex_path(src, tid)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(L.ROOT, 'build', 's7', 'bak', src.replace('/', '__') + '__' + tid.replace('#', '_') + '.pvr'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p + '.s7e.tmp', 'wb').write(new)
        os.replace(p + '.s7e.tmp', p)
        print('wrote', p)
