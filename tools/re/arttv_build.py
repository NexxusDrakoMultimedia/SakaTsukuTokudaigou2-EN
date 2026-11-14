"""arttv_build - repaint the TV station card textures (ETC_DATA/TV_EVENT.ZAR) and write translation/textures/.

    python -I -X utf8 tools/re/arttv_build.py [--ids=04080,...] [--no-inject]

Reads build/tex/ETC_DATA__TV_EVENT.ZAR/<id>_*.png (decoded originals), paints with tools/arttext.py, encodes
with tools/pvr.py (same format/size), writes translation/textures/ETC_DATA/TV_EVENT.ZAR/<member>#<i>.pvr.
Intermediate PNGs go to build/art_tv/.
"""
import os
import sys
import glob
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
from PIL import Image
import arttext
import pvr
import texinject

ISO = 'ETC_DATA/TV_EVENT.ZAR'
TEXDIR = os.path.join(ROOT, 'build', 'tex', 'ETC_DATA__TV_EVENT.ZAR')
OUT = os.path.join(ROOT, 'build', 'art_tv')
DEST = os.path.join(ROOT, 'translation', 'textures', 'ETC_DATA', 'TV_EVENT.ZAR')

FONT = ['arial-bold']
STYLES = {
    'row': {'font': FONT, 'gradient': [[0, '#fff6b0'], [0.45, '#ecdc6a'], [1, '#9a9a55']],
            'bold': 0.25, 'outline': {'color': '#001a1a', 'width': 1.2},
            'shadow': {'color': '#001122', 'dx': 1, 'dy': 1, 'blur': 0.8, 'alpha': 0.8}},
    'net': {'font': FONT, 'fill': '#ffff00',
            'outline': {'color': '#0a3a66', 'width': 1.0},
            'shadow': {'color': '#001122', 'dx': 1, 'dy': 1, 'blur': 1.0, 'alpha': 0.85}},
    'promoted': {'font': FONT, 'gradient': [[0, '#ffffff'], [0.3, '#ddeebb'], [0.65, '#aadd77'], [1, '#669944']],
                 'outline': {'color': '#001a14', 'width': 2},
                 'shadow': {'color': '#001010', 'dx': 1, 'dy': 2, 'blur': 1.0, 'alpha': 0.8}},
    'demoted': {'font': FONT, 'gradient': [[0, '#ffffff'], [0.3, '#eeccdd'], [0.65, '#cc6688'], [1, '#661133']],
                'outline': {'color': '#120008', 'width': 2},
                'shadow': {'color': '#100008', 'dx': 1, 'dy': 2, 'blur': 1.0, 'alpha': 0.8}},
    'retained': {'font': FONT, 'gradient': [[0, '#f0f0f8'], [0.35, '#ccccdd'], [0.7, '#7788bb'], [1, '#445599']],
                 'outline': {'color': '#002244', 'width': 2},
                 'shadow': {'color': '#001020', 'dx': 1, 'dy': 2, 'blur': 1.0, 'alpha': 0.8}},
    'decided': {'font': FONT, 'gradient': [[0, '#ffffff'], [0.4, '#ffffaa'], [1, '#ffee22']],
                'outline': {'color': '#606000', 'width': 2},
                'shadow': {'color': '#202000', 'dx': 1, 'dy': 2, 'blur': 1.0, 'alpha': 0.8}},
}
ROW_ERASE = {'mode': 'mask', 'ink': [{'color': [255, 238, 102], 'tol': 120}, {'luma_lt': 45}],
             'dilate': 1, 'fill': 'hfill'}
CLEAR = {'mode': 'clear'}

NETS = {  # id: (network, programme)
    '04082': ('Local Net', 'Soccer Flash TV'),
    '04085': ('Net 6', 'Excite Soccer'),
    '04087': ('Net 12', 'Super Soccer 11'),
    '04089': ('Japan Net', 'Soccer News J'),
    '04091': ('Asia Net', 'Asia Soccer Today'),
    '04093': ('World Net', 'World Soccer Weekly'),
}


def net_spec(net, prog):
    reg = []
    for text, y, er in ((net, 118, [0, 120, 256, 26]), (prog, 142, [0, 146, 256, 30])):
        reg.append({'id': 'net_' + text, 'text': text, 'x': 4, 'y': y, 'w': 246, 'h': 30, 'erase_rect': er,
                    'erase': CLEAR, 'style': 'net', 'size': 21, 'min_sx': 0.7, 'align': 'left', 'dy': 0,
                    'valign': 'middle', 'pad': 2})
    return {'size': [256, 256], 'quantize': 'argb4444', 'styles': STYLES, 'regions': reg}


def spec_04080():
    reg = []
    rows = [('Avg Ratings', 3, 124), ('Capital', 35, 84), ('Region', 67, 62), ('Employees', 99, 106)]
    for text, y, w in rows:
        reg.append({'id': 'row_' + text, 'text': text, 'x': 54, 'y': y - 2, 'w': w, 'h': 28,
                    'erase_rect': [53, y - 1, w + 2, 26], 'erase': None, 'style': 'row', 'size': 21,
                    'min_sx': 0.72, 'align': 'left', 'valign': 'middle', 'pad': 1})
    for rid, word, y, ey, eh in (('promoted', 'Promoted', 148, 146, 44), ('demoted', 'Demoted', 190, 190, 46)):
        # the Japanese had a gap at x138..148 between the two words; keep each word on its own side of it
        reg.append({'id': rid + '_a', 'text': 'TV Station', 'x': 4, 'y': y, 'w': 132, 'h': 40,
                    'erase_rect': [0, ey, 140, eh], 'erase': CLEAR, 'style': rid, 'size': 27, 'min_sx': 0.7,
                    'align': 'left', 'valign': 'middle', 'pad': 2})
        reg.append({'id': rid + '_b', 'text': word, 'x': 146, 'y': y, 'w': 70, 'h': 40, 'font': ['arial-narrow-bold', 'arial-bold'],
                    'erase_rect': [140, ey, 116, eh], 'erase': CLEAR, 'style': rid, 'size': 27, 'min_sx': 0.6,
                    'align': 'left', 'valign': 'middle', 'pad': 2})
    return {'size': [256, 256], 'quantize': 'argb4444', 'styles': STYLES, 'regions': reg}


def spec_head(style, line2):
    reg = [{'id': 'l1', 'text': 'TV Station', 'x': 4, 'y': 1, 'w': 122, 'h': 38, 'erase_rect': [0, 0, 128, 41],
            'erase': CLEAR, 'style': style, 'size': 25, 'min_sx': 0.7, 'align': 'left', 'valign': 'middle', 'pad': 2},
           {'id': 'l2', 'text': line2, 'x': 6, 'y': 42, 'w': 80, 'h': 38, 'erase_rect': [0, 41, 128, 42], 'font': ['arial-narrow-bold', 'arial-bold'],
            'erase': CLEAR, 'style': style, 'size': 25, 'min_sx': 0.6, 'align': 'left', 'valign': 'middle', 'pad': 2}]
    return {'size': [128, 128], 'quantize': 'argb4444', 'styles': STYLES, 'regions': reg}


# x0, x1 (exclusive), first row of the full-replace band, end row (exclusive); rows around it use the ink mask only
ROW_BOXES = [(53, 180, 4, 27, 1, 31), (53, 132, 36, 59, 33, 63), (53, 109, 68, 91, 65, 95), (53, 156, 100, 123, 97, 127)]


def pre_erase_rows(img):
    a = np.array(img.convert('RGBA')).astype(np.int32)
    for x0, x1, f0, f1, m0, m1 in ROW_BOXES:
        for y in range(m0, m1):
            col = np.median(a[y, 49:54, :], axis=0)
            seg = a[y, x0:x1, :].copy()
            if f0 <= y < f1:
                seg[:] = col
            else:
                ink = (seg[:, 2] - seg[:, 0]) < 40
                g = ink.copy()
                for d in (1, 2):
                    g[d:] |= ink[:-d]
                    g[:-d] |= ink[d:]
                seg[g] = col
            a[y, x0:x1, :] = seg
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')


def specs():
    s = {'04080': spec_04080(), '04081': spec_head('retained', 'Retained'), '04084': spec_head('decided', 'Decided')}
    for k, (n, p) in NETS.items():
        s[k] = net_spec(n, p)
    return s


def main():
    ids = None
    inject = True
    for a in sys.argv[1:]:
        if a.startswith('--ids='):
            ids = a.split('=', 1)[1].split(',')
        if a == '--no-inject':
            inject = False
    os.makedirs(OUT, exist_ok=True)
    for tid, spec in sorted(specs().items()):
        if ids and tid not in ids:
            continue
        src = glob.glob(os.path.join(TEXDIR, tid + '_*.png'))[0]
        member = os.path.basename(src)[6:-4]          # TV_EB.TBD_0
        mem, idx = member.rsplit('_', 1)
        texid = '%s#%s' % (mem, idx)
        with open(os.path.join(OUT, tid + '.spec.json'), 'w', encoding='utf8') as f:
            json.dump(spec, f, indent=1)
        img = Image.open(src).convert('RGBA')
        if tid == '04080':
            img = pre_erase_rows(img)
        out, rep = arttext.render_spec(spec, img, OUT, None, None)
        out.save(os.path.join(OUT, tid + '.out.png'))
        for w in rep.get('warnings') or []:
            print(tid, 'WARN', w)
        for r in rep['regions']:
            print(tid, {k: v for k, v in r.items() if k != 'rect'})
        if inject:
            orig = texinject.extract_pvr(ISO, texid)
            arr = np.array(out.convert('RGBA'))
            new = pvr.encode(arr, original=orig)
            if pvr.parse_file(new) is None:
                pf = pvr.parse_file(orig)
                new = orig[:pf.data_off] + new + orig[pf.data_off + pf.data_len:]
            os.makedirs(DEST, exist_ok=True)
            with open(os.path.join(DEST, texid + '.pvr'), 'wb') as f:
                f.write(new)
            back = pvr.decode(new)
            Image.fromarray(np.array(back)).save(os.path.join(OUT, tid + '.dec.png'))
            print(tid, texid, 'written', len(new))
        else:
            print(tid, 'painted')


if __name__ == '__main__':
    main()
