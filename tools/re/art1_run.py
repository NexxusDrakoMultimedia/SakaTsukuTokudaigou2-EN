"""art1_run - repaint one group-1 texture and re-encode it.
python -I -X utf8 tools/re/art1_run.py ID [ID ...]
Reads tools/re/art1_spec/ID.json and build/art1/orig/ID.png|pvr, writes build/art1/new/ID.png, ID.pvr and
build/art1/new/ID.sheet.png (before|after, 3x)."""
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
    img = Image.open(os.path.join(B, 'orig', i + '.png')).convert('RGBA')
    for x, y, w, h, cx in spec.get('prefill', []):   # am2: row fill from column cx over (x, y, w, h)
        a = np.array(img)
        a[y:y + h, x:x + w] = a[y:y + h, cx:cx + 1]
        img = Image.fromarray(a, 'RGBA')
    pf = spec.get('polyfill')   # am2: rebuild a plate with a slanted bevelled left edge under an erased glyph
    if pf:
        a = np.array(img)
        for y in range(pf['y0'], pf['y1'] + 1):
            ex = int(round(pf['e0'] + (pf['e1'] - pf['e0']) * (y - pf['y0']) / float(pf['y1'] - pf['y0'])))
            a[y, ex:pf['xend']] = pf['body'] + [255]
            for k, c in enumerate(pf['edge']):
                a[y, ex + k] = c + [255]
        for x in range(pf['xstart'], pf['xend']):
            a[pf['y0'], x] = pf['top'] + [255] if a[pf['y0'], x, 3] else a[pf['y0'], x]
        img = Image.fromarray(a, 'RGBA')
    base = np.asarray(img).astype(np.float64)
    os.makedirs(os.path.join(B, 'masks'), exist_ok=True)
    for r in spec['regions']:
        hs = r.get('hsmooth')
        if hs:
            x, y, w, h = r['erase_rect']
            L = base[y:y + h, x - hs:x].mean(axis=1)
            R = base[y:y + h, x + w:x + w + hs].mean(axis=1)
            t = ((np.arange(w) + 0.5) / w)[None, :, None]
            pl = L[:, None, :] * (1 - t) + R[:, None, :] * t
            pth = os.path.join(B, 'masks', i + '_' + r['id'] + '.plate.png')
            Image.fromarray(np.clip(np.rint(pl), 0, 255).astype(np.uint8), 'RGBA').save(pth)
            r['erase'] = {'mode': 'plate', 'path': pth}
    out, rep = A.render_spec(spec, img, os.path.join(HERE, 'art1_spec'), gl, os.path.join(B, 'masks', i))
    for r in rep['regions']:
        if r.get('font'):
            print('  %-12s %-14r size=%s sx=%s block=%s' % (r['id'], r['text'], r['size'], r['squash'], r['block']))
    for w in rep['warnings']:
        print('  WARNING:', w)
    if spec.get('post'):   # am2: alpha repairs after the render
        a = np.array(out)
        for x, y, w, h in spec['post'].get('clear', []):
            a[y:y + h, x:x + w, 3] = 0
        e = spec['post'].get('edge')   # [xmin, y0, y1, e0, e1, xend]: left of the slanted edge transparent, right of it opaque up to xend
        if e:
            xmin, y0, y1, e0, e1, xend = e
            for y in range(y0, y1 + 1):
                ex = int(round(e0 + (e1 - e0) * (y - y0) / float(y1 - y0)))
                a[y, xmin:ex, 3] = 0
                a[y, ex:xend, 3] = 255
        out = Image.fromarray(a, 'RGBA')
    out.save(os.path.join(B, 'new', i + '.png'))
    A.before_after(img, out, os.path.join(B, 'new', i + '.sheet.png'), 3)
    orig = open(os.path.join(B, 'orig', i + '.pvr'), 'rb').read()
    enc = pvr.encode(np.asarray(out), original=orig)
    open(os.path.join(B, 'new', i + '.pvr'), 'wb').write(enc)
    # decoded check: what the hardware will show
    pvr.to_png(pvr.decode(enc), os.path.join(B, 'new', i + '.dec.png'))
    print(i, 'ok', len(enc))
