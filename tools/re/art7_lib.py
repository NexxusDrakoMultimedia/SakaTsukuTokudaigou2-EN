"""art7_lib: helpers for the group-7 art pass (hometown, supporters, data room, challenge, system menus).
Uses tools/arttext.py (render) and tools/pvr.py / tools/texinject.py (codec, injection).  Not a shared tool."""
import os, sys, collections
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import arttext, pvr, texinject  # noqa: E402,E401

TEXIDX = os.path.join(ROOT, 'build', 'texindex.tsv')
SHEETIDX = os.path.join(ROOT, 'build', 'tex', 'index.tsv')
OUT = os.path.join(ROOT, 'build', 'art7')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')


def resolve(id5):
    """5-digit id -> (iso file, texinject id, sheet-index row dict)."""
    hdr = None
    d = None
    with open(SHEETIDX, encoding='utf8') as f:
        hdr = f.readline().rstrip('\n').split('\t')
        for l in f:
            p = l.rstrip('\n').split('\t')
            if p[0][:5] == id5:
                d = dict(zip(hdr, p))
                break
    if d is None:
        raise KeyError(id5)
    src, member, rec, w, h = d['source'], d['member'], d['rec'], d['width'], d['height']
    cands = []
    with open(TEXIDX, encoding='utf8') as f:
        f.readline()
        for l in f:
            p = l.rstrip('\n').split('\t')
            if p[0] != src or p[5] != w or p[6] != h:
                continue
            tid = p[1]
            if d['kind'] == 'PVR' and tid == '':
                cands.append(tid)
            elif tid.endswith('#' + rec):
                if member and not tid.startswith(member + '#'):
                    continue
                cands.append(tid)
    if len(cands) != 1:
        raise KeyError('%s -> %s candidates %r' % (id5, src, cands))
    return src, cands[0], d


def load(id5):
    src, tid, d = resolve(id5)
    with open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb') as f:
        data = f.read()
    pv = texinject.extract_pvr(data, tid)
    arr = np.asarray(pvr.decode(pv)).copy()
    return dict(id=id5, src=src, tid=tid, pvr=pv, arr=arr, info=d)


def dups(src, tid):
    return [(r[0], r[1]) for r in texinject.find_copies(TEXIDX, src, tid)]


def tex_path(src, tid):
    return os.path.join(TEXDIR, *src.split('/'), tid + '.pvr')


def components(arr, thr=24, gx=5, gy=2, min_area=10, bgdist=None):
    """Boxes (x,y,w,h) of ink clusters.  bgdist=(r,g,b,tol): ink = colour far from bg instead of alpha."""
    if bgdist:
        c = np.array(bgdist[:3], float)
        ink = (np.sqrt(((arr[..., :3].astype(float) - c) ** 2).sum(-1)) > bgdist[3]) & (arr[..., 3] > 0)
    else:
        ink = arr[..., 3] > thr
    H, W = ink.shape
    d = ink.copy()
    for s in range(1, gx + 1):
        d[:, s:] |= ink[:, :-s]
        d[:, :-s] |= ink[:, s:]
    e = d.copy()
    for s in range(1, gy + 1):
        e[s:] |= d[:-s]
        e[:-s] |= d[s:]
    lab = np.zeros((H, W), np.int32)
    boxes = []
    n = 0
    for y0 in range(H):
        xs = np.nonzero(e[y0] & (lab[y0] == 0))[0]
        for x0 in xs:
            if lab[y0, x0]:
                continue
            n += 1
            q = collections.deque([(y0, x0)])
            lab[y0, x0] = n
            mnx = mxx = x0
            mny = mxy = y0
            while q:
                y, x = q.popleft()
                if x < mnx: mnx = x
                if x > mxx: mxx = x
                if y > mxy: mxy = y
                for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= yy < H and 0 <= xx < W and e[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        q.append((yy, xx))
            sub = ink[mny:mxy + 1, mnx:mxx + 1] & (lab[mny:mxy + 1, mnx:mxx + 1] == n)
            if sub.sum() >= min_area:
                ys, xs2 = np.nonzero(sub)
                boxes.append((mnx + int(xs2.min()), mny + int(ys.min()), int(xs2.max() - xs2.min() + 1),
                              int(ys.max() - ys.min() + 1)))
    boxes.sort(key=lambda b: (b[1] // 14, b[0]))
    return boxes


def overlay(arr, boxes, path, scale=2, bg=(110, 110, 130)):
    im = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    b = Image.new('RGBA', im.size, bg + (255,))
    b.alpha_composite(im)
    b = b.resize((im.width * scale, im.height * scale), Image.NEAREST).convert('RGB')
    d = ImageDraw.Draw(b)
    for i, (x, y, w, h) in enumerate(boxes):
        d.rectangle([x * scale, y * scale, (x + w) * scale, (y + h) * scale], outline=(255, 0, 255))
        d.text((x * scale + 1, y * scale - 10 if y > 10 else y * scale + h * scale), str(i), fill=(255, 255, 0))
    b.save(path)


def _luma(c):
    return c[..., 0] * 0.299 + c[..., 1] * 0.587 + c[..., 2] * 0.114


def ink_of(arr, rect, erase):
    """Mask of the old ink inside rect: from the erase spec's ink conditions if it has some, else alpha >= 200."""
    x, y, w, h = rect
    if isinstance(erase, dict) and erase.get('mode') == 'mask':
        ink = erase.get('ink')
        conds = ink if isinstance(ink, list) else [ink or {}]
        fa = arr.astype(float)
        m = np.zeros((h, w), bool)
        for c in conds:
            m |= arttext._cond_mask(c, fa, rect, '.', arr.shape[1], arr.shape[0])
        return m
    return arr[y:y + h, x:x + w, 3] >= 200


def autostyle(arr, rect, dark_text=False, erase=None, mode='outline'):
    """Sample fill gradient / outline from the old ink inside rect (RGBA uint8 array)."""
    x, y, w, h = rect
    sub = arr[y:y + h, x:x + w].astype(float)
    m = ink_of(arr, rect, erase)
    if m.sum() < 6:
        return {}
    ys, xs = np.nonzero(m)
    Lm = _luma(sub[..., :3])
    lv = Lm[m]
    if dark_text:
        sel = Lm <= np.percentile(lv, 55)
    else:
        sel = Lm >= np.percentile(lv, 60)
    sel &= m
    rows = np.arange(h)[:, None]
    top = sel & (rows <= ys.min() + (ys.max() - ys.min()) * 0.4)
    bot = sel & (rows >= ys.min() + (ys.max() - ys.min()) * 0.6)

    def med(mm):
        if mm.sum() < 3:
            mm = sel
        return [int(v) for v in np.median(sub[..., :3][mm], axis=0)]
    ct, cb = med(top), med(bot)
    st = {'gradient': [[0, ct], [1, cb]]}
    if not dark_text:
        dk = m & (Lm <= np.percentile(lv, 18))
        if dk.sum() >= 3:
            dc = [int(v) for v in np.median(sub[..., :3][dk], axis=0)]
            if _luma(np.array(dc, float)) < 0.55 * _luma(np.array(ct, float)):
                if mode == 'shadow':
                    k = 2 if h >= 24 else 1
                    st['shadow'] = {'color': dc, 'dx': k, 'dy': k, 'blur': 0, 'alpha': 0.9}
                else:
                    st['outline'] = {'color': dc, 'width': 1}
                    st['shadow'] = {'color': dc, 'dx': 1, 'dy': 1, 'blur': 0, 'alpha': 0.9}
    return st


def rowfill(arr, rect, tol=40, dil=1, xr=None, minfrac=0.0):
    """Replace ink by the row's modal colour: for every row of rect take the most frequent colour (4 bit buckets) among the
    opaque pixels of xr=(x0,x1) (default the rect) as background; pixels further than tol from it (max channel) are ink and are
    set to that colour (+dil px).  For plates made of horizontal bands (stripes) under a glyph.  In place on RGBA uint8."""
    x, y, w, h = rect
    x0, x1 = xr if xr else (x, x + w)
    for yy in range(y, y + h):
        row = arr[yy]
        seg = row[x0:x1]
        op = seg[:, 3] >= 128
        if op.sum() < 8:
            continue
        q = (seg[op][:, :3] >> 4).astype(np.int32)
        key = (q[:, 0] << 8) | (q[:, 1] << 4) | q[:, 2]
        vals, cnt = np.unique(key, return_counts=True)
        best = vals[np.argmax(cnt)]
        sel = seg[op][key == best]
        bg = np.rint(sel[:, :3].mean(0)).astype(np.uint8)
        d = np.abs(row[x:x + w, :3].astype(int) - bg.astype(int)).max(-1)
        ink = (d > tol) & (row[x:x + w, 3] >= 128)
        if dil:
            k = ink.copy()
            for sft in range(1, dil + 1):
                k[sft:] |= ink[:-sft]
                k[:-sft] |= ink[sft:]
            ink = k & (row[x:x + w, 3] >= 128)
        row[x:x + w][ink, :3] = bg
        row[x:x + w][ink, 3] = 255


def grow(r, n, W, H):
    x, y, w, h = r
    x0, y0 = max(0, x - n), max(0, y - n)
    x1, y1 = min(W, x + w + n), min(H, y + h + n)
    return (x0, y0, x1 - x0, y1 - y0)


def _simplify(sty, level):
    """level 1: gradients -> 3 flat bands; 2: flat colour, no blur; 3: also 1-bit alpha."""
    sty = dict(sty)
    g = sty.get('gradient')
    if g and level >= 1:
        cols = [c for _, c in g]
        if level == 1:
            c0, c1, c2 = cols[0], cols[len(cols) // 2], cols[-1]
            sty['gradient'] = [[0, c0], [0.34, c0], [0.34, c1], [0.67, c1], [0.67, c2], [1, c2]]
        else:
            sty.pop('gradient')
            sty['fill'] = cols[len(cols) // 2]
    if level >= 2 and isinstance(sty.get('shadow'), dict):
        sty['shadow'] = dict(sty['shadow'], blur=0)
    if level >= 3:
        sty['aa'] = False
    return sty


def repaint(t, items, fmt='argb4444', level=0):
    """items: dicts with rect (x,y,w,h) = tight old-ink box, text; optional font, style (dict overrides), erase ('clear' default,
    or an arttext erase spec), pad, align, dark (dark text), erase_grow, dx, dy, size, max_size, min_sx, shear, bold."""
    arr = t['arr'].copy()
    for it in items:
        if it.get('rowfill'):
            rowfill(arr, tuple(it['rowfill']['rect']), it['rowfill'].get('tol', 40), it['rowfill'].get('dil', 1), it['rowfill'].get('xr'))
    H, W = arr.shape[:2]
    regs = []
    for k, it in enumerate(items):
        r = tuple(it['rect'])
        pr = grow(r, it.get('pad', 1), W, H)
        sty = autostyle(arr, r, dark_text=it.get('dark', False), erase=it.get('erase', {'mode': 'clear'}), mode=it.get('mode', 'outline')) if it.get('autostyle', True) else {}
        for kk, vv in (it.get('style') or {}).items():
            sty[kk] = vv
        if 'fill' in (it.get('style') or {}) and 'gradient' not in it['style']:
            sty.pop('gradient', None)
        reg = dict(id='r%d' % k, text=it.get('text'), x=pr[0], y=pr[1], w=pr[2], h=pr[3],
                   erase=it.get('erase', {'mode': 'clear'}), align=it.get('align', 'center'),
                   valign=it.get('valign', 'middle'), min_sx=it.get('min_sx', 0.55), font=it.get('font', 'arial-bold'),
                   size=it.get('size', 'auto'), max_size=it.get('max_size', 64), pad=0)
        if it.get('erase_grow') is not None:
            reg['erase_grow'] = it['erase_grow']
        for kk in ('dx', 'dy', 'wrap', 'line_spacing', 'bold', 'letter_spacing', 'shear', 'min_size'):
            if kk in it:
                reg[kk] = it[kk]
        if level:
            sty = _simplify(sty, level)
        if fmt == 'argb1555' and 'aa' not in sty:
            sty['aa'] = False
        reg['style'] = sty
        regs.append(reg)
    spec = {'supersample': 4, 'regions': regs, 'defaults': {}}
    if fmt:
        spec['quantize'] = fmt
    img = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    return arttext.render_spec(spec, img)


def save_png(img, id5, which='out'):
    d = os.path.join(OUT, which)
    os.makedirs(d, exist_ok=True)
    img.save(os.path.join(d, id5 + '.png'))


def encode_and_write(t, img):
    """Encode into the texture's own format, write translation/textures for every identical copy."""
    arr = np.asarray(img.convert('RGBA'))
    new = pvr.encode(arr, original=t['pvr'])
    dec = pvr.decode(new)
    assert dec.shape == arr.shape
    written = []
    for src, tid in dups(t['src'], t['tid']):
        p = tex_path(src, tid)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(new)
        written.append(p)
    return new, written


def fit_report(new, t):
    """For every identical copy: does `new` (PVR bytes) fit its slot with policy 'exact'?  -> [(src, tid, ok, msg)]"""
    res = []
    for src, tid in dups(t['src'], t['tid']):
        with open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb') as f:
            data = f.read()
        try:
            texinject.inject(data, tid, new, 'exact')
            res.append((src, tid, True, ''))
        except texinject.TexInjectError as e:
            res.append((src, tid, False, str(e)[:120]))
    return res
