"""art1sk_run - like art1_run but the base image is build/art1sk/ID_clean.png (already erased) and the spec erase steps are skipped.
python -I -X utf8 tools/re/art1sk_run.py ID [ID ...]   (writes build/art1/new/ID.png|pvr|dec.png|sheet.png)"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import arttext as A, pvr
from PIL import Image
import numpy as np
B = os.path.join(ROOT, 'build', 'art1')
gl = A.load_glossary(os.path.join(ROOT, 'translation', 'glossary.tsv'))
for i in sys.argv[1:]:
    spec = json.load(open(os.path.join(HERE, 'art1_spec', i + '.json'), encoding='utf8'))
    orig_img = Image.open(os.path.join(B, 'orig', i + '.png')).convert('RGBA')
    img = Image.open(os.path.join(ROOT, 'build', 'art1sk', i + '_clean.png')).convert('RGBA')
    for r in spec['regions']:
        r['erase'] = {'mode': 'mask', 'ink': {'luma_gt': 9999}}
    out, rep = A.render_spec(spec, img, os.path.join(HERE, 'art1_spec'), gl, None)
    for r in rep['regions']:
        if r.get('font'):
            print('  %-12s %-14r size=%s sx=%s block=%s' % (r['id'], r['text'], r['size'], r['squash'], r['block']))
    out.save(os.path.join(B, 'new', i + '.png'))
    A.before_after(orig_img, out, os.path.join(B, 'new', i + '.sheet.png'), 3)
    orig = open(os.path.join(B, 'orig', i + '.pvr'), 'rb').read()
    enc = pvr.encode(np.asarray(out), original=orig)
    open(os.path.join(B, 'new', i + '.pvr'), 'wb').write(enc)
    pvr.to_png(pvr.decode(enc), os.path.join(B, 'new', i + '.dec.png'))
    print(i, 'ok', len(enc))
