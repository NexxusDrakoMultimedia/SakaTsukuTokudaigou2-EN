"""s7c_run [--write] [--font F] [member ...] : repaint the 15 STAFFLST role-title textures (package H of groups_v3).
Clears the old katakana and sets English lines in the credits style (white->grey gradient, black shadow, as the English STAFF header).
Writes build/s7c/out/<m>.png and build/s7c/v/<m>_ba.png always; --write also encodes into the texture's own format and
writes translation/textures/GAME/STAFFLST.ZAR/<m>.pvr.pvr (every dup copy) unless a file already exists and --force is not given."""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7c_dump as D
ROOT = D.ROOT
import arttext, pvr, texinject  # noqa
TEXIDX = os.path.join(ROOT, 'build', 'texindex.tsv')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')
OUT = os.path.join(ROOT, 'build', 's7c')

LINES = {
    't_direc': ['Director'],
    't_tdirec': ['Technical', 'Director'],
    't_plan': ['Planner'],
    't_prog': ['Programmer'],
    't_npro': ['Network', 'Programmer'],
    't_design': ['Designer'],
    't_stdirec': ['Sound', 'Technical', 'Director'],
    't_kai': ['Commentary'],
    't_jikkyo': ['Play-by-play'],
    't_promo': ['Promotion'],
    't_pub': ['Publicity'],
    't_special': ['Special', 'Thanks'],
    't_assip': ['Assistant', 'Producer'],
    't_produ': ['Producer'],
    't_gene': ['General', 'Manager'],
}
STYLE = {'gradient': [[0, '#f2f2f2'], [0.55, '#eeeeee'], [1, '#c8c8c8']],
         'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'blur': 0, 'alpha': 1.0, 'steps': 2}}
Y0, DY, LH = 7, 31, 26


def _simp(sty, level):
    sty = dict(sty)
    if level >= 1:
        sty['gradient'] = [[0, '#f0f0f0'], [0.6, '#f0f0f0'], [0.6, '#c8c8c8'], [1, '#c8c8c8']]
    if level >= 2:
        sty.pop('gradient'); sty['fill'] = '#eeeeee'
    if level >= 3:
        sty['aa'] = False
    return sty


def spec_for(m, font, size, level=0):
    regs = []
    for k, t in enumerate(LINES[m]):
        regs.append(dict(id='l%d' % k, text=t, x=2, y=Y0 + DY * k, w=123, h=LH, erase=None, align='left', valign='middle',
                         font=font, size='auto', max_size=size, min_sx=0.8, pad=0, dx=0, style=_simp(STYLE, level)))
    return {'supersample': 4, 'regions': regs, 'defaults': {}, 'quantize': 'argb4444'}


def main():
    args = sys.argv[1:]
    write = '--write' in args
    force = '--force' in args
    font = 'segoe-ui-bold'
    size = 22
    if '--font' in args:
        i = args.index('--font'); font = args[i + 1]; del args[i:i + 2]
    if '--size' in args:
        i = args.index('--size'); size = int(args[i + 1]); del args[i:i + 2]
    ms = [a for a in args if not a.startswith('--')] or D.MEMBERS
    for d in ('out', 'v'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    for m in ms:
        pv, a = D.load(m)
        blank = a.copy(); blank[...] = 0
        img = Image.fromarray(blank.astype(np.uint8), 'RGBA')
        with open(os.path.join(ROOT, 'extracted', 'GAME', 'STAFFLST.ZAR'), 'rb') as f:
            data = f.read()
        for level in range(4):
            out, rep = arttext.render_spec(spec_for(m, font, size, level), img)
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
        out.save(os.path.join(OUT, 'out', m + '.png'))
        b = Image.fromarray(a.astype(np.uint8), 'RGBA').crop((0, 0, 128, 104))
        n = Image.fromarray(np.asarray(pvr.decode(new)).astype(np.uint8), 'RGBA').crop((0, 0, 128, 104))
        c = Image.new('RGBA', (260, 104), (90, 90, 110, 255))
        bb = Image.new('RGBA', b.size, (90, 90, 110, 255)); bb.alpha_composite(b); c.paste(bb, (0, 0))
        nb = Image.new('RGBA', n.size, (90, 90, 110, 255)); nb.alpha_composite(n); c.paste(nb, (132, 0))
        c.resize((520, 208), Image.NEAREST).convert('RGB').save(os.path.join(OUT, 'v', m + '_ba.png'))
        print(m, 'fits at level', level, len(new), 'bytes')
        if write:
            for src, tid in [(r[0], r[1]) for r in texinject.find_copies(TEXIDX, 'GAME/STAFFLST.ZAR', m + '.pvr')]:
                p = os.path.join(TEXDIR, *src.split('/'), tid + '.pvr')
                if os.path.exists(p) and not force:
                    print(m, 'EXISTS, skipped (stage 6 or earlier owner):', p); continue
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'wb') as f:
                    f.write(new)
                print(m, 'wrote', os.path.relpath(p, ROOT))


main()
