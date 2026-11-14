"""art3_run.py - repaint one texture of group 3 (Name Entry / edit-screen labels) and write the .pvr for build_patch.

usage: python -I -X utf8 tools/re/art3_run.py KEY [--crop x y w h] [--scale 3] [--bg 90]
KEY is one of N_ENTRY PASSWD SEARCH PT1 PT2 PT3 PT4.  Spec: translation/art/<texture id>.json (tools/arttext.py format).
Writes translation/textures/<iso path>/<id>.pvr and build/art3/<KEY>_{before,after}.png and a crop sheet."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
from PIL import Image
import arttext
import pvr
import texinject

TEX = {
    'N_ENTRY': ('ETC_DATA/N_ENTRY.DAT', 'pvr.tbd#0', '03541'),
    'PASSWD': ('ETC_DATA/PASSWD.TBD', '#0', '03553'),
    'SEARCH': ('FLOW_PRG/SEARCH.BIN', '@2c58c#0', '07594'),
    'PT1': ('ETC_DATA/PL_EDIT.ZAR', 'PL_PT1.TBD#2', '03578'),
    'PT2': ('ETC_DATA/PL_EDIT.ZAR', 'PL_PT2.TBD#0', '03583'),
    'PT3': ('ETC_DATA/PL_EDIT.ZAR', 'PL_PT3.TBD#0', '03584'),
    'PT4': ('ETC_DATA/PL_EDIT.ZAR', 'PL_PT4.TBD#0', '03585'),
}


def flat(img, bg):
    a = np.asarray(img.convert('RGBA')).astype(np.float64)
    al = a[:, :, 3:4] / 255.0
    rgb = a[:, :, :3] * al + bg * (1 - al)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB')


def main():
    args = sys.argv[1:]
    key = args[0]
    crop = None
    scale = 3
    bg = 90
    i = 1
    while i < len(args):
        if args[i] == '--crop':
            crop = [int(v) for v in args[i + 1:i + 5]]
            i += 5
        elif args[i] == '--scale':
            scale = int(args[i + 1])
            i += 2
        elif args[i] == '--bg':
            bg = int(args[i + 1])
            i += 2
        else:
            raise SystemExit('bad arg ' + args[i])
    iso, tid, num = TEX[key]
    orig = texinject.extract_pvr(iso, tid)
    before = Image.fromarray(pvr.decode(orig), 'RGBA')
    spec_path = os.path.join(ROOT, 'translation', 'art', num + '.json')
    with open(spec_path, encoding='utf-8') as f:
        spec = json.load(f)
    gl = arttext.load_glossary(os.path.join(ROOT, 'translation', 'glossary.tsv'))
    src = before
    for rr in spec.get('art3_row_mode', []):      # rebuild gradient bars under old text: per row, the most common colour
        a = np.asarray(src).copy()
        x0, x1 = rr['x']
        y0, y1 = rr['y']
        for y in range(y0, y1):
            row = a[y, x0 + 2:x1 - 2].reshape(-1, 4)
            vals, cnt = np.unique(row, axis=0, return_counts=True)
            a[y, x0 + 2:x1 - 2] = vals[cnt.argmax()]
        src = Image.fromarray(a, 'RGBA')
    after, rep = arttext.render_spec(spec, src, os.path.dirname(spec_path), gl)
    for w in rep['warnings']:
        print('WARNING:', w)
    for r in rep['regions']:
        if r.get('font'):
            print('  %-14s %-20r size=%s squash=%s block=%s' % (r['id'], r['text'], r['size'], r['squash'], r['block']))
    new = pvr.encode(after, original=orig)
    chk = Image.fromarray(pvr.decode(new), 'RGBA')
    diff = np.abs(np.asarray(chk).astype(int) - np.asarray(after).astype(int)).max()
    print('encode roundtrip max diff vs painted image:', diff)
    fc = texinject.fit_check(iso, tid, new)
    print('fit:', {k: fc[k] for k in ('fits', 'packed', 'slot', 'over') if k in fc})
    out = os.path.join(ROOT, 'translation', 'textures', *iso.split('/'), tid + '.pvr')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(new)
    print('wrote', out)
    od = os.path.join(ROOT, 'build', 'art3')
    os.makedirs(od, exist_ok=True)
    before.save(os.path.join(od, key + '_before.png'))
    chk.save(os.path.join(od, key + '_after.png'))
    b, a = flat(before, bg), flat(chk, bg)
    if crop:
        x, y, w, h = crop
        b, a = b.crop((x, y, x + w, y + h)), a.crop((x, y, x + w, y + h))
    W, H = b.size
    sh = Image.new('RGB', (W * scale, H * scale * 2 + 6), (30, 30, 30))
    sh.paste(b.resize((W * scale, H * scale), Image.NEAREST), (0, 0))
    sh.paste(a.resize((W * scale, H * scale), Image.NEAREST), (0, H * scale + 6))
    sp = os.path.join(od, key + '_sheet.png')
    sh.save(sp)
    print('sheet', sp)


main()
