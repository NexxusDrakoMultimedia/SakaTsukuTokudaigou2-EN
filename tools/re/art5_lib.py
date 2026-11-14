"""art5_lib - helpers for the group-5 art pass (arttext render + pvr encode + write to translation/textures)."""
import os, sys, json
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import arttext, pvr, texinject
ART = os.path.join(ROOT, 'build', 'art5')
MAN = json.load(open(os.path.join(ART, 'manifest.json')))
MAN.update(json.load(open(os.path.join(ART, 'manifest_extra.json'))) if os.path.exists(os.path.join(ART, 'manifest_extra.json')) else {})
TEXDIR = os.path.join(ROOT, 'translation', 'textures')


def load(i):
    return Image.open(os.path.join(ART, 'orig', i + '.png')).convert('RGBA')


def render(i, spec, img=None):
    img = img or load(i)
    spec = dict(spec)
    spec.setdefault('supersample', 4)
    out, rep = arttext.render_spec(spec, img, base_dir=ART)
    for w in rep['warnings']:
        print('  WARN', i, w)
    return out


def finish(i, img, write=True):
    """encode img as texture i, write to every copy, save PNGs (new/<i>.png = painted, new/<i>.dec.png = decoded back)."""
    img.save(os.path.join(ART, 'new', i + '.png'))
    orig = open(os.path.join(ART, 'orig', i + '.pvr'), 'rb').read()
    out = pvr.encode(np.asarray(img.convert('RGBA')), original=orig)
    dec = pvr.decode(out)
    pvr.to_png(dec, os.path.join(ART, 'new', i + '.dec.png'))
    if write:
        m = MAN[i]
        for f, tid in m['copies']:
            p = os.path.join(TEXDIR, *f.split('/'), tid + '.pvr')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(out)
    return out


def over(i, img):
    """bytes over the slot (<= 0 fits) for every copy; encodes img the way finish() does"""
    orig = open(os.path.join(ART, 'orig', i + '.pvr'), 'rb').read()
    out = pvr.encode(np.asarray(img.convert('RGBA')), original=orig)
    worst = -10 ** 9
    for f, tid in MAN[i]['copies']:
        src = open(os.path.join(ROOT, 'extracted', *f.split('/')), 'rb').read()
        r = texinject.fit_check(src, tid, out)
        worst = max(worst, r.get('over', 0) if not r['fits'] else 0)
    return worst
