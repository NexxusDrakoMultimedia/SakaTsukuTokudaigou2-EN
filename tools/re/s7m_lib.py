"""s7m_lib: helpers of the s7 'menus' package (Office personnel plates, Hometown town menu, economy words, Step Up tags).
Texture picked by (iso file, texinject id); every same-payload copy (texinject.find_copies) gets its own .pvr file under
translation/textures.  Not a shared tool."""
import os, sys, shutil
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import arttext, pvr, texinject  # noqa: E402,E401

TEXIDX = os.path.join(ROOT, 'build', 'texindex.tsv')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')
OUT = os.path.join(ROOT, 'build', 's7', 'm')
BAK = os.path.join(ROOT, 'build', 's7', 'bak')


def load(src, tid):
    with open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb') as f:
        data = f.read()
    pv = texinject.extract_pvr(data, tid)
    return dict(src=src, tid=tid, pvr=pv, arr=np.asarray(pvr.decode(pv)).copy())


def copies(src, tid):
    return [(r[0], r[1]) for r in texinject.find_copies(TEXIDX, src, tid)]


def tex_path(src, tid):
    return os.path.join(TEXDIR, *src.split('/'), tid + '.pvr')


def render(t, regions, styles, fmt, pre=None, ss=4):
    """regions: arttext region dicts; pre: list of (fn(arr)) pixel pre-processors run on a copy of the array."""
    arr = t['arr'].copy()
    for fn in (pre or []):
        fn(arr)
    spec = {'supersample': ss, 'quantize': fmt, 'styles': styles, 'defaults': {}, 'regions': regions}
    img = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    out, rep = arttext.render_spec(spec, img)
    return out, rep


def fit(new, t):
    res = []
    for src, tid in copies(t['src'], t['tid']):
        with open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb') as f:
            data = f.read()
        try:
            texinject.inject(data, tid, new, 'exact')
            res.append((src, tid, True, ''))
        except texinject.TexInjectError as e:
            res.append((src, tid, False, str(e)[:140]))
    return res


def write(t, img, dry=False):
    arr = np.asarray(img.convert('RGBA'))
    new = pvr.encode(arr, original=t['pvr'])
    dec = np.asarray(pvr.decode(new))
    assert dec.shape == arr.shape
    bad = [r for r in fit(new, t) if not r[2]]
    paths = []
    if dry:
        return new, paths, bad
    for src, tid in copies(t['src'], t['tid']):
        p = tex_path(src, tid)
        if os.path.exists(p):
            b = os.path.join(BAK, os.path.relpath(p, TEXDIR))
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(p, b)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(new)
        paths.append(p)
    return new, paths, bad


def sheet(before, after, path, scale=3, rect=None, bg=(255, 0, 255)):
    ims = []
    for a in (before, after):
        im = a if isinstance(a, Image.Image) else Image.fromarray(np.asarray(a).astype(np.uint8), 'RGBA')
        if rect:
            im = im.crop(rect)
        b = Image.new('RGBA', im.size, bg + (255,)); b.alpha_composite(im.convert('RGBA'))
        ims.append(b.convert('RGB'))
    w, h = ims[0].size
    c = Image.new('RGB', (w * 2 + 4, h), (30, 30, 30))
    c.paste(ims[0], (0, 0)); c.paste(ims[1], (w + 4, 0))
    c = c.resize((c.width * scale, c.height * scale), Image.NEAREST)
    c.save(path)
