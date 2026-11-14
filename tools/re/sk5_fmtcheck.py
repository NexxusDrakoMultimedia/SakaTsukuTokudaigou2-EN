"""sk5_fmtcheck: for every installed repainted texture compare pixel format / data format / size / mip with the original,
and list pixels newly opaque where the original was fully transparent (and vice versa) as counts per file.
    python -I -X utf8 tools/re/sk5_fmtcheck.py"""
import os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, texinject, ar5_view  # noqa

n = bad = 0
for dp, _, fns in os.walk(ar5_view.TEXDIR):
    for fn in sorted(fns):
        if not fn.endswith('.pvr'):
            continue
        f = os.path.join(dp, fn)
        src, tid = ar5_view.split(f)
        if not src:
            print('NOSRC', f)
            continue
        with open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb') as fh:
            old = pvr.parse_file(texinject.extract_pvr(fh.read(), tid))
        with open(f, 'rb') as fh:
            new = pvr.parse_file(fh.read())
        n += 1
        if (old.pix, old.dat, old.w, old.h) != (new.pix, new.dat, new.w, new.h):
            bad += 1
            print('DIFF', src, tid, (old.pix, old.dat, old.w, old.h), (new.pix, new.dat, new.w, new.h))
print('checked', n, 'differing', bad)
