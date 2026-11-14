"""art4sk_hobby8: Masumi Yamasaki plate (SS_PR1 #8): hobby value was clipped at the right edge; redraw it shorter."""
import os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import pvr, texinject, arttext, art4_specs
tid = 'SS_PR1.TBD#8'
p = os.path.join(ROOT, 'translation', 'textures', 'ETC_DATA', 'SS_TEX.ZAR', tid + '.pvr')
orig_b = texinject.extract_pvr('ETC_DATA/SS_TEX.ZAR', tid)
cur = np.asarray(pvr.decode(open(p, 'rb').read()), np.uint8).copy()
cur[159:184, 96:249] = (0, 0, 0, 187)
job = art4_specs.JOBS['pr8']
spec = copy.deepcopy(job['spec'])
reg = [r for r in spec['regions'] if r['id'] == 'val3'][0]
reg['text'] = sys.argv[1]
reg['erase'] = None
reg['w'] = 148
spec['regions'] = [reg]
out, rep = arttext.render_spec(spec, Image.fromarray(cur, 'RGBA'), HERE, {}, None)
for w in rep['warnings']:
    print('WARN', w)
print(rep['regions'][0].get('size'), rep['regions'][0].get('squash'), rep['regions'][0].get('block'))
arr = np.asarray(out, np.uint8)
enc = pvr.encode_ex(arr, original=orig_b)
texinject.replace_texture('ETC_DATA/SS_TEX.ZAR', tid, enc.data, 'exact')
open(p, 'wb').write(enc.data)
print('written', len(enc.data))
