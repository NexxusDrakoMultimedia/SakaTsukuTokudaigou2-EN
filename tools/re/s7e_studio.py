"""s7e_studio: montage of NEWSOPED.ZAR studioN.tbd #0 / #2 (originals, or --cur installed)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import art7_lib as L
import pvr, texinject
data = open(os.path.join(L.ROOT, 'extracted', 'ETC_DATA', 'NEWSOPED.ZAR'), 'rb').read()
cur = '--cur' in sys.argv
W = 128
c = Image.new('RGB', (W * 6 * 2 + 20, W * 2 + 4), (60, 0, 60))
for n in range(6):
    for j, k in enumerate((0, 2)):
        tid = 'studio%d.tbd#%d' % (n, k)
        pv = texinject.extract_pvr(data, tid)
        p = L.tex_path('ETC_DATA/NEWSOPED.ZAR', tid)
        if cur and os.path.isfile(p):
            pv = open(p, 'rb').read()
        a = np.asarray(pvr.decode(pv)).copy()
        im = Image.fromarray(a.astype(np.uint8), 'RGBA')
        b = Image.new('RGBA', im.size, (110, 110, 130, 255)); b.alpha_composite(im)
        c.paste(b.convert('RGB'), (n * 2 * (W + 2) + j * (W + 1), 0))
c = c.crop((0, 0, c.width, W))
c = c.resize((c.width * 2 // 2 * 1, c.height), Image.NEAREST)
c.save(os.path.join(L.ROOT, 'build', 's7', 'e', 'studio%s.png' % ('_cur' if cur else '')))
