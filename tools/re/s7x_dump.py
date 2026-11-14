"""s7x_dump: dump original and current (translation/textures) PNGs of package E ids to build/s7x/o/."""
import sys, os
sys.path.insert(0, 'tools')
import numpy as np
from PIL import Image
import pvr, texinject
ids = sys.argv[1:] or '37285 37171 37172 37173 37286 36912 36918 36921 36926 36927 36931 36932 36937 37302'.split()
rows = {}
for line in open('build/tex/index.tsv', encoding='utf8'):
    p = line.rstrip('\n').split('\t')
    rows[p[0][:5]] = p
for i in ids:
    p = rows[i]
    src, member, kind, rec = p[1], p[2], p[8], p[9]
    tid = ('%s#%s' % (member, rec)) if member else '#%s' % rec
    if kind == 'PVR':
        tid = member
    data = open(os.path.join('extracted', src), 'rb').read()
    orig = texinject.extract_pvr(data, tid)
    Image.fromarray(np.asarray(pvr.decode(orig)).copy(), 'RGBA').save('build/s7x/o/%s_o.png' % i)
    fn = os.path.join('translation', 'textures', *src.split('/'), tid.replace('/', '_') + '.pvr')
    cur = os.path.exists(fn)
    if cur:
        Image.fromarray(np.asarray(pvr.decode(open(fn, 'rb').read())).copy(), 'RGBA').save('build/s7x/o/%s_c.png' % i)
    print(i, src, repr(tid), p[5], p[6], p[7], 'cur' if cur else '-', fn)
