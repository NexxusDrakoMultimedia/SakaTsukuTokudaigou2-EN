"""art6_run - repaint one texture of group 6 from tools/re/art6/<id>.json and write all copies to translation/textures.
usage: art6_run.py ID [--no-write]   (ID = 5-digit number of build/tex/index.tsv)"""
import sys, os, json
sys.path.insert(0, 'tools')
import numpy as np
from PIL import Image
import arttext, pvr, texinject

ROOT = os.getcwd()
tid5 = sys.argv[1]
write = '--no-write' not in sys.argv
row = None
for line in open('build/tex/index.tsv', encoding='utf8'):
    p = line.rstrip('\n').split('\t')
    if p[0].startswith(tid5 + '_'):
        row = p; break
src, member, kind, rec = row[1], row[2], row[8], row[9]
tid = ('%s#%s' % (member, rec)) if member else '#%s' % rec
if kind == 'PVR':
    tid = member
data = open(os.path.join('extracted', src), 'rb').read()
orig = texinject.extract_pvr(data, tid)
rgba = pvr.decode(orig)
img = Image.fromarray(rgba, 'RGBA')
spec = json.load(open('tools/re/art6/%s.json' % (sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else tid5), encoding='utf8'))
spec['size'] = list(img.size)
gl = arttext.load_glossary('translation/glossary.tsv') if os.path.exists('translation/glossary.tsv') else None
out, rep = arttext.render_spec(spec, img, base_dir='tools/re/art6', glossary=None, debug_dir='build/art6/masks_' + tid5)
for w in rep['warnings']:
    print('WARN', w)
for r in rep['regions']:
    print('region', r['id'], r.get('text'), {k: v for k, v in r.items() if k not in ('id', 'text')})
arr = np.asarray(out).copy()
enc = pvr.encode_ex(arr, original=orig)
dec = pvr.decode(enc.data)
Image.fromarray(dec, 'RGBA').save('build/art6/n_%s.png' % tid5)
Image.fromarray(rgba, 'RGBA').save('build/art6/o_%s.png' % tid5)
print('encoded', len(enc.data), 'info', enc.info)
if write:
    copies = texinject.find_copies('build/texindex.tsv', src, tid)
    for c in copies:
        d2 = os.path.join('translation', 'textures', *c[0].split('/'))
        os.makedirs(d2, exist_ok=True)
        t2 = texinject.extract_pvr(open(os.path.join('extracted', c[0]), 'rb').read(), c[1])
        e2 = pvr.encode(arr, original=t2)
        fn = os.path.join(d2, c[1] + '.pvr')
        open(fn, 'wb').write(e2)
        print('wrote', fn)
try:
    ri = texinject.inject(data, tid, enc.data, policy='grow')
    print('FIT packed', ri.info.get('packed'), 'slot', ri.info.get('slot'), 'need', ri.info.get('need'))
except Exception as e:
    print('FIT?', str(e)[:150])
