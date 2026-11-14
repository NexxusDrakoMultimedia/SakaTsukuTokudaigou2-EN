"""s7r_menu ID OLDTEXT NEWTEXT [--write] : re-render tools/re/art6/<ID>.json (37292 / 37293) with one label replaced.
Source = decoded ORIGINAL texture (extracted/), output PNG build/s7/r/menu_<ID>.png, --write encodes + writes the texture file."""
import sys, os, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import arttext, pvr, texinject
import art7_lib as L
tid_id, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
write = '--write' in sys.argv
t = L.load(tid_id)
spec = json.load(open(os.path.join(ROOT, 'tools', 're', 'art6', tid_id + '.json'), encoding='utf8'))
hit = 0
for r in spec['regions']:
    if r['text'] == old:
        r['text'] = new; hit += 1
assert hit == 1, hit
img = Image.fromarray(t['arr'].astype(np.uint8), 'RGBA')
out, rep = arttext.render_spec(spec, img, base_dir=os.path.join(ROOT, 'tools', 're', 'art6'))
for w in rep['warnings']:
    print('WARN', w)
out.save(os.path.join(ROOT, 'build', 's7', 'r', 'menu_%s.png' % tid_id))
if write:
    nb = pvr.encode(np.asarray(out.convert('RGBA')), original=t['pvr'])
    bad = [r for r in L.fit_report(nb, t) if not r[2]]
    assert not bad, bad
    p = L.tex_path(t['src'], t['tid'])
    open(p, 'wb').write(nb)
    print('wrote', p, len(nb))
