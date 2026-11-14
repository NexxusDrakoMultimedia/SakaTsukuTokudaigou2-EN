"""s7bi_run [--write] [--font F] [--size N] [member ...]: repaint the 41 STAFFLST staff-name textures (package I of groups_v3)
as romanised names (Given Family, from docs/credits-names.tsv) in the credits style of the s7c role titles.
Writes build/s7bi/out/<m>.png always; --write encodes into the texture's own format and writes
translation/textures/GAME/STAFFLST.ZAR/<m>.pvr.pvr (every dup copy) unless a file exists and --force is not given.
Always writes build/s7bi/ba_NN.png before/after montages (viewing aid)."""
import os, sys, csv
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7c_dump as D
ROOT = D.ROOT
import arttext, pvr, texinject  # noqa
TEXIDX = os.path.join(ROOT, 'build', 'texindex.tsv')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')
OUT = os.path.join(ROOT, 'build', 's7bi')
STYLE = {'gradient': [[0, '#f2f2f2'], [0.55, '#eeeeee'], [1, '#c8c8c8']],
         'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'blur': 0, 'alpha': 1.0, 'steps': 2}}
Y0, DY, LH = 3, 31, 26
ONE_LINE_MAX = 11


def names():
    out = {}
    with open(os.path.join(ROOT, 'docs', 'credits-names.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            out[r['member']] = r['romanisation']
    return out


def lines_for(name):
    if len(name) <= ONE_LINE_MAX:
        return [name]
    g, fam = name.split(' ', 1)
    return [g, fam]


def _simp(sty, level):
    sty = dict(sty)
    if level >= 1:
        sty['gradient'] = [[0, '#f0f0f0'], [0.6, '#f0f0f0'], [0.6, '#c8c8c8'], [1, '#c8c8c8']]
    if level >= 2:
        sty.pop('gradient'); sty['fill'] = '#eeeeee'
    if level >= 3:
        sty['aa'] = False
    if level >= 4:   # 1 px shadow offset (s_murayama: 'Sunao Murayama' only fits its 1400 byte slot this way)
        sty['shadow'] = dict(sty['shadow'], dx=1, dy=1)
    return sty


def spec_for(name, font, size, level=0):
    regs = []
    for k, t in enumerate(lines_for(name)):
        regs.append(dict(id='l%d' % k, text=t, x=2, y=Y0 + DY * k, w=123, h=LH, erase=None, align='left', valign='middle',
                         font=font, size='auto', max_size=size, min_sx=0.8, pad=0, dx=0, style=_simp(STYLE, level)))
    return {'supersample': 4, 'regions': regs, 'defaults': {}, 'quantize': 'argb4444'}


def main():
    args = sys.argv[1:]
    write = '--write' in args
    force = '--force' in args
    font, size = 'segoe-ui-bold', 22
    if '--font' in args:
        i = args.index('--font'); font = args[i + 1]; del args[i:i + 2]
    if '--size' in args:
        i = args.index('--size'); size = int(args[i + 1]); del args[i:i + 2]
    nm = names()
    ms = [a for a in args if not a.startswith('--')] or list(nm)
    os.makedirs(os.path.join(OUT, 'out'), exist_ok=True)
    with open(os.path.join(ROOT, 'extracted', 'GAME', 'STAFFLST.ZAR'), 'rb') as f:
        data = f.read()
    tiles = []
    for m in ms:
        pv, a = D.load(m)
        blank = a.copy(); blank[...] = 0
        img = Image.fromarray(blank.astype(np.uint8), 'RGBA')
        for level in range(5):
            out, rep = arttext.render_spec(spec_for(nm[m], font, size, level), img)
            arr = np.asarray(out.convert('RGBA'))
            new = pvr.encode(arr, original=pv, retrain=True)
            assert pvr.decode(new).shape == arr.shape
            try:
                texinject.inject(data, m + '.pvr', new, 'exact')
                break
            except texinject.TexInjectError as e:
                print(m, 'level', level, 'does not fit:', str(e)[:100])
        else:
            print(m, 'FAILED to fit'); continue
        for w in rep.get('warnings', []):
            print(m, 'WARN', w)
        dec = np.asarray(pvr.decode(new)).copy()
        ys, xs = np.nonzero(dec[..., 3] > 40)
        print(m, nm[m], 'level', level, len(new), 'bytes ink', xs.min(), ys.min(), xs.max(), ys.max())
        out.save(os.path.join(OUT, 'out', m + '.png'))
        t = Image.new('RGB', (264, 68), (40, 0, 40))
        for k, aa in enumerate((a, dec)):
            im = Image.fromarray(aa.astype(np.uint8), 'RGBA')
            bg = Image.new('RGBA', im.size, (90, 90, 110, 255)); bg.alpha_composite(im)
            t.paste(bg.convert('RGB').crop((0, 0, 128, 66)), (k * 136, 0))
        ImageDraw.Draw(t).text((2, 56), m, fill=(255, 255, 0))
        tiles.append(t)
        if write:
            for src, tid in [(r[0], r[1]) for r in texinject.find_copies(TEXIDX, 'GAME/STAFFLST.ZAR', m + '.pvr')]:
                p = os.path.join(TEXDIR, *src.split('/'), tid + '.pvr')
                if os.path.exists(p) and not force:
                    print(m, 'EXISTS, skipped:', p); continue
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'wb') as f:
                    f.write(new)
                print(m, 'wrote', os.path.relpath(p, ROOT))
    per = 8
    for n in range(0, len(tiles), per):
        ch = tiles[n:n + per]
        c = Image.new('RGB', (2 * 268, 4 * 70), (40, 0, 40))
        for i, t in enumerate(ch):
            c.paste(t, ((i % 2) * 268, (i // 2) * 70))
        c.resize((c.width * 2, c.height * 2), Image.NEAREST).save(os.path.join(OUT, 'ba_%02d.png' % (n // per)))


main()
