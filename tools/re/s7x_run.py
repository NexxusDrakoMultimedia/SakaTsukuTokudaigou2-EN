"""s7x_run [--write] [--scale N] [--full] ID ...: repaint textures of package E (match owner) from tools/re/s7x_specs.py.
SPECS[id] = {'items': [...art7_lib.repaint items...], 'base': 'installed' (start from translation/textures file; default original),
             'palette': 'bg_barx.pvp' (pal8 textures: external palette)}.
Always writes build/s7x/out/ID.png and build/s7x/v/ID.png (before | after).  --write encodes and writes every identical copy
(backing the old file up in build/s7/bak/)."""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import art7_lib as L
import pvr, pvr_scan, texinject
import s7x_specs

OUT = os.path.join(L.ROOT, 'build', 's7x')


def palette(name):
    data = open(os.path.join(L.ROOT, 'extracted', 'TRAINING', 'BFGAME.ZAR'), 'rb').read()
    got = []
    sc = pvr_scan.Scanner(lambda t: got.append((t.path, t.payload)) if t.kind == 'PVP' else None, keep_rows=False)
    sc.walk('TRAINING/BFGAME.ZAR', data)
    for p, pl in got:
        if p.endswith(name):
            return pvr.parse_pvp(pl)
    raise KeyError(name)


def extract(src, tid):
    return texinject.extract_pvr(open(os.path.join(L.ROOT, 'extracted', *src.split('/')), 'rb').read(), tid)


def enc(arr, orig, pal):
    return pvr.encode(arr, original=orig, palette=pal) if pal is not None else pvr.encode(arr, original=orig)


def main():
    args = sys.argv[1:]
    write = '--write' in args
    scale = 2
    if '--scale' in args:
        i = args.index('--scale')
        scale = int(args[i + 1])
        del args[i:i + 2]
    full = '--full' in args
    ids = [a for a in args if not a.startswith('--')]
    for i in ids:
        spec = s7x_specs.SPECS[i]
        t = L.load(i)
        pal = palette(spec['palette']) if spec.get('palette') else None
        if pal is not None:
            t['arr'] = np.asarray(pvr.decode(t['pvr'], palette=pal)).copy()
        orig_arr = t['arr'].copy()
        if spec.get('base') == 'installed':
            fp = L.tex_path(t['src'], t['tid'])
            t['arr'] = np.asarray(pvr.decode(open(fp, 'rb').read(), palette=pal)).copy()
        for it in spec['items']:
            cf = it.get('colfill2')
            if cf:
                cx, cy, cw, ch = cf['rect']
                t['arr'][cy:cy + ch, cx:cx + cw] = t['arr'][cy:cy + ch, cf['src']:cf['src'] + 1]
            cf = it.get('colfill')
            if cf:
                cx, cy, cw, ch = cf['rect']
                sy = cf.get('srcy', cy)
                t['arr'][cy:cy + ch, cx:cx + cw] = t['arr'][sy:sy + ch, cf['src']:cf['src'] + 1]
        fmt = spec.get('fmt') or {'ARGB1555': 'argb1555', 'RGB565': 'rgb565'}.get(t['info']['format'].split('/')[0], 'argb4444')
        out, rep = L.repaint(t, spec['items'], fmt, spec.get('level', 0))
        for w in rep['warnings']:
            print(i, 'WARN', w)
        for r in rep['regions']:
            extra = {k: v for k, v in r.items() if k not in ('id', 'text', 'ja')}
            print(i, r.get('id'), r.get('text'), extra)
        arr = np.asarray(out.convert('RGBA')).copy()
        new = enc(arr, t['pvr'], pal)
        dec = np.asarray(pvr.decode(new, palette=pal)).copy()
        os.makedirs(os.path.join(OUT, 'out'), exist_ok=True)
        os.makedirs(os.path.join(OUT, 'v'), exist_ok=True)
        Image.fromarray(dec, 'RGBA').save(os.path.join(OUT, 'out', i + '.png'))
        rs = [it['rect'] for it in spec['items']]
        H, W = arr.shape[:2]
        if full:
            x0, y0, x1, y1 = 0, 0, W, H
        else:
            x0 = max(0, min(r[0] for r in rs) - 6)
            y0 = max(0, min(r[1] for r in rs) - 6)
            x1 = min(W, max(r[0] + r[2] for r in rs) + 6)
            y1 = min(H, max(r[1] + r[3] for r in rs) + 6)
        b = Image.fromarray(t['arr'], 'RGBA').crop((x0, y0, x1, y1))
        a = Image.fromarray(dec, 'RGBA').crop((x0, y0, x1, y1))
        w, h = b.size
        c = Image.new('RGBA', (w * 2 + 4, h), (110, 110, 130, 255))
        c.alpha_composite(b, (0, 0))
        c.alpha_composite(a, (w + 4, 0))
        c = c.resize((c.width * scale, c.height * scale), Image.NEAREST).convert('RGB')
        c.save(os.path.join(OUT, 'v', i + '.png'))
        bad = [r for r in L.fit_report(new, t) if not r[2]]
        print(i, 'fit:', 'OK' if not bad else bad[0][3], 'copies', L.dups(t['src'], t['tid']))
        if write and not bad:
            for src, tid in L.dups(t['src'], t['tid']):
                p = L.tex_path(src, tid)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                if os.path.exists(p):
                    shutil.copy(p, os.path.join(L.ROOT, 'build', 's7', 'bak', 's7x_%s_%s.pvr' % (i, (src + '_' + tid).replace('/', '_').replace('#', 'n'))))
                open(p, 'wb').write(enc(arr, extract(src, tid), pal))
                print(i, 'wrote', p)


main()
