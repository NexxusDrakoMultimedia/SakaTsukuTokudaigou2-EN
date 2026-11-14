"""art7_run [--write] [--scale N] ID ... : run the art7 specs (art7_specs*.py) for the given 5-digit ids.
Always writes build/art7/out/ID.png (repainted PNG) and build/art7/v/ID_ba.png (before | after, tight around the edits).
--write also encodes into the texture's own format and writes translation/textures/<iso path>/<id>.pvr for every identical copy."""
import sys, os, glob, importlib
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import art7_lib as L

SPECS = {}
for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), 'art7_specs*.py'))):
    m = importlib.import_module(os.path.basename(f)[:-3])
    SPECS.update(m.SPECS)


def main():
    args = sys.argv[1:]
    write = '--write' in args
    scale = 2
    if '--scale' in args:
        i = args.index('--scale')
        scale = int(args[i + 1])
        del args[i:i + 2]
    ids = [a for a in args if not a.startswith('--')]
    if ids == ['all']:
        ids = sorted(SPECS)
    os.makedirs(os.path.join(L.OUT, 'v'), exist_ok=True)
    for i in ids:
        spec = SPECS[i]
        t = L.load(i)
        fmt = spec.get('fmt') or {'ARGB1555': 'argb1555', 'RGB565': 'rgb565'}.get(t['info']['format'].split('/')[0], 'argb4444')
        lvl0 = int(os.environ.get('ART7_LEVEL', '0'))
        level = lvl0
        while True:
            out, rep = L.repaint(t, spec['items'], fmt, level)
            if not write:
                break
            import pvr as _pvr
            new = _pvr.encode(np.asarray(out.convert('RGBA')), original=t['pvr'])
            bad = [r for r in L.fit_report(new, t) if not r[2]]
            if not bad:
                break
            print(i, 'level', level, 'does not fit:', bad[0][3][:90])
            level += 1
            if level > 3:
                print(i, 'FAILED to fit at level 3; not written')
                out = None
                break
        if out is None:
            continue
        if level:
            print(i, 'simplified to level', level)
        for w in rep['warnings']:
            print(i, 'WARN', w)
        L.save_png(out, i)
        # before/after crop
        rs = [it['rect'] for it in spec['items']]
        x0 = max(0, min(r[0] for r in rs) - 4)
        y0 = max(0, min(r[1] for r in rs) - 4)
        x1 = min(t['arr'].shape[1], max(r[0] + r[2] for r in rs) + 4)
        y1 = min(t['arr'].shape[0], max(r[1] + r[3] for r in rs) + 4)
        b = Image.fromarray(t['arr'].astype(np.uint8), 'RGBA').crop((x0, y0, x1, y1))
        a = out.crop((x0, y0, x1, y1))
        w, h = b.size
        bgc = Image.new('RGBA', (w * 2 + 4, h), (110, 110, 130, 255))
        bgc.alpha_composite(b, (0, 0))
        bgc.alpha_composite(a, (w + 4, 0))
        bgc = bgc.resize((bgc.width * scale, bgc.height * scale), Image.NEAREST).convert('RGB')
        bgc.save(os.path.join(L.OUT, 'v', i + '_ba.png'))
        if write:
            new, paths = L.encode_and_write(t, out)
            print(i, 'wrote', len(paths), 'copies', len(new), 'bytes')
            with open(os.path.join(L.OUT, 'written.txt'), 'a', encoding='utf8') as wf:
                for pth in paths:
                    wf.write(os.path.relpath(pth, L.TEXDIR).replace(os.sep, '/') + chr(10))
        else:
            print(i, 'ok (not written)')


main()
