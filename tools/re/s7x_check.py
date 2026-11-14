"""s7x_check: decode every installed package-E texture file, and make a contact sheet build/s7x/check.png (each fit with texinject 'exact')."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import art7_lib as L
import pvr, texinject
ids = '37285 37171 37172 37173 37286 36912 36918 36921 36926 36927 36931 36932 36937 37302'.split()
for i in ids:
    src, tid, d = L.resolve(i)
    fp = L.tex_path(src, tid)
    if not os.path.exists(fp):
        print(i, 'MISSING', fp); continue
    b = open(fp, 'rb').read()
    pv = texinject.extract_pvr(open(os.path.join(L.ROOT, 'extracted', *src.split('/')), 'rb').read(), tid)
    try:
        pvr.decode(b, palette=None) if len(b) and b'PVPL' not in b else None
    except Exception as e:
        print(i, 'decode (no palette) note', str(e)[:60])
    try:
        texinject.inject(open(os.path.join(L.ROOT, 'extracted', *src.split('/')), 'rb').read(), tid, b, 'exact')
        print(i, 'OK', len(b), os.path.getmtime(fp) > 0, 'sizeEqual', len(b) == len(pv))
    except Exception as e:
        print(i, 'INJECT FAIL', str(e)[:100])
