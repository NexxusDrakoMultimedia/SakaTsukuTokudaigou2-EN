"""s7e_run [--write] [--scale N] [--cand] ID ... : run the s7e specs (s7e_specs.py) for 5-digit ids.
Base image = the installed translation/textures file when there is one (earlier repaint kept), else the original.
Always writes build/s7/e/out/ID.png and build/s7/e/ba_ID.png (before | after, crop around the edits).
--write  encodes into the texture's own format and writes every identical copy under translation/textures (single-file
         backup of any file it replaces goes to build/s7/bak/).  Refuses a copy file that is newer than OWN_AFTER unless the id
         is in ALLOW_RECENT.
--cand   write the encoded result to build/s7/e/cand/ID.pvr instead (not installed)."""
import os, sys, shutil, time, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import art7_lib as L
import pvr

S = importlib.import_module('s7e_specs')
OUTD = os.path.join(L.ROOT, 'build', 's7', 'e')
BAK = os.path.join(L.ROOT, 'build', 's7', 'bak')
# files newer than this (epoch) were written by stage 6 during this session: do not overwrite
OWN_AFTER = time.mktime((2026, 11, 12, 3, 0, 0, 0, 0, -1))


def main():
    args = sys.argv[1:]
    write = '--write' in args
    cand = '--cand' in args
    scale = 3
    if '--scale' in args:
        i = args.index('--scale')
        scale = int(args[i + 1])
        del args[i:i + 2]
    ids = [a for a in args if not a.startswith('--')]
    os.makedirs(os.path.join(OUTD, 'out'), exist_ok=True)
    os.makedirs(os.path.join(OUTD, 'cand'), exist_ok=True)
    os.makedirs(BAK, exist_ok=True)
    for i in ids:
        spec = S.SPECS[i]
        t = L.load(i)
        cur = L.tex_path(t['src'], t['tid'])
        base_pvr = t['pvr']
        base = t['arr']
        if os.path.isfile(cur):
            base_pvr = open(cur, 'rb').read()
            base = np.asarray(pvr.decode(base_pvr)).copy()
        base0 = base
        if spec.get('pre'):
            base = base.copy()
            spec['pre'](base)
        tt = dict(t)
        tt['arr'] = base
        fmt = spec.get('fmt') or {'ARGB1555': 'argb1555', 'RGB565': 'rgb565'}.get(t['info']['format'].split('/')[0], 'argb4444')
        level = 0
        while True:
            out, rep = L.repaint(tt, spec['items'], fmt, level)
            new = pvr.encode(np.asarray(out.convert('RGBA')), original=base_pvr)
            bad = [r for r in L.fit_report(new, t) if not r[2]]
            if not bad:
                break
            print(i, 'level', level, 'does not fit:', bad[0][3][:90])
            level += 1
            if level > 3:
                print(i, 'FAILED to fit at level 3')
                break
        for w in rep['warnings']:
            print(i, 'WARN', w)
        out.save(os.path.join(OUTD, 'out', i + '.png'))
        rs = [it['rect'] for it in spec['items']]
        x0 = max(0, min(r[0] for r in rs) - 6)
        y0 = max(0, min(r[1] for r in rs) - 6)
        x1 = min(base.shape[1], max(r[0] + r[2] for r in rs) + 6)
        y1 = min(base.shape[0], max(r[1] + r[3] for r in rs) + 6)
        dec = np.asarray(pvr.decode(new)).copy()   # what the hardware shows
        b = Image.fromarray(base0.astype(np.uint8), 'RGBA').crop((x0, y0, x1, y1))
        a = Image.fromarray(dec.astype(np.uint8), 'RGBA').crop((x0, y0, x1, y1))
        w, h = b.size
        bgc = Image.new('RGBA', (w * 2 + 4, h), (110, 110, 130, 255))
        bgc.alpha_composite(b, (0, 0))
        bgc.alpha_composite(a, (w + 4, 0))
        bgc = bgc.resize((bgc.width * scale, bgc.height * scale), Image.NEAREST).convert('RGB')
        bgc.save(os.path.join(OUTD, 'ba_' + i + '.png'))
        print(i, 'level', level, 'crop', (x0, y0, x1 - x0, y1 - y0), len(new), 'bytes')
        if cand:
            open(os.path.join(OUTD, 'cand', i + '.pvr'), 'wb').write(new)
            print(i, 'candidate written (not installed)')
        elif write:
            for src, tid in L.dups(t['src'], t['tid']):
                p = L.tex_path(src, tid)
                if os.path.isfile(p):
                    if os.path.getmtime(p) > OWN_AFTER and i not in S.ALLOW_RECENT:
                        print(i, 'SKIP (newer than stage-6 cut-off, stage 6 owns):', p)
                        continue
                    shutil.copy2(p, os.path.join(BAK, src.replace('/', '__') + '__' + tid.replace('#', '_') + '.pvr'))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                tmp = p + '.s7e.tmp'
                open(tmp, 'wb').write(new)
                os.replace(tmp, p)
                print(i, 'wrote', p)
            with open(os.path.join(OUTD, 'written.txt'), 'a', encoding='utf8') as wf:
                wf.write(i + chr(10))


main()
