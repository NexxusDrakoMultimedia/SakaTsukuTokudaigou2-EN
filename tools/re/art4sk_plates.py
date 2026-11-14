"""art4sk_plates - skeptic fix for the SS_PR1 profile plates: rebuild name bar (dark fill + bright plate + bevel), redraw the name,
clean rule-line and right-edge remnants.  python -I -X utf8 tools/re/art4sk_plates.py [--write] RECS..."""
import os, sys, copy
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import pvr, texinject, arttext
import art4_specs
write = '--write' in sys.argv
recs = [int(a) for a in sys.argv[1:] if a.isdigit()]
BAR = {0, 1, 2, 3, 4, 8}
JEN = {28: (0xee, 0xcc, 0x66), 29: (0xff, 0xee, 0x88), 30: (0xdd, 0xaa, 0x22), 31: (0xdd, 0xaa, 0x22), 32: (0xdd, 0xaa, 0x22), 33: (0xaa, 0x88, 0x22), 34: (0x66, 0x55, 0x11)}
TD = os.path.join(ROOT, 'translation', 'textures', 'ETC_DATA', 'SS_TEX.ZAR')


def mode(vals):
    return np.array(Counter(tuple(int(c) for c in v) for v in vals).most_common(1)[0][0], np.uint8)


for rec in recs:
    tid = 'SS_PR1.TBD#%d' % rec
    orig_b = texinject.extract_pvr('ETC_DATA/SS_TEX.ZAR', tid)
    orig = np.asarray(pvr.decode(orig_b), np.uint8)
    cur = np.asarray(pvr.decode(open(os.path.join(TD, tid + '.pvr'), 'rb').read()), np.uint8).copy()
    job = art4_specs.JOBS['pr%d' % rec]
    nreg = [r for r in job['spec']['regions'] if r['id'] == 'name'][0]
    nx = nreg['x']
    # rule top rows and right edge cleanup (all plates)
    for y in (98, 127, 155, 184):
        cur[y, 2:253] = cur[y + 1, 2:253]
    for y in range(74, 186):
        for x in range(249, 255):
            if tuple(cur[y, x]) != (0, 0, 0, 187):
                cur[y, x] = (0, 0, 0, 187)
    if rec in BAR:
        xd = 6 if nx < 20 else 40
        pm = mode([orig[y, x] for y in range(9, 29) for x in range(238, 248)]) if rec != 1 else np.array([255, 204, 51, 255], np.uint8)
        # plate left edge from top rows
        xes = []
        for y in (4, 5, 6):
            p = mode([orig[y, x] for x in range(238, 248)])
            for x in range(150, 238):
                if tuple(orig[y, x]) == tuple(p) and tuple(orig[y, x + 1]) == tuple(p):
                    xes.append(x); break
        xe = 194
        print('rec', rec, 'plate left edge', xe, xes, 'pm', pm)
        for y in range(4, 35):
            d = orig[y, xd]
            if rec == 1:
                d = np.array(JEN.get(y, (0x55, 0x44, 0x11)) + (255,), np.uint8)
            if rec == 1 and y >= 28:
                p = d
            elif 8 <= y <= 31:
                p = pm
            else:
                p = mode([orig[y, x] for x in range(238, 248)])
            for x in range(nx - 1 if nx > 20 else 4, 249):
                cur[y, x] = d if x < xe else p
        spec = copy.deepcopy(job['spec'])
        spec['regions'] = [dict(nreg, erase=None)]
        spec['regions'][0].pop('erase_rect', None)
        out, rep = arttext.render_spec(spec, Image.fromarray(cur, 'RGBA'), HERE, {}, None)
        for w in rep['warnings']:
            print('  WARN', w)
        cur = np.asarray(out, np.uint8)
    # fit
    enc = pvr.encode_ex(cur, original=orig_b)
    chk = np.asarray(pvr.decode(enc.data), np.uint8)
    texinject.replace_texture('ETC_DATA/SS_TEX.ZAR', tid, enc.data, 'exact')
    print('rec', rec, 'len', len(enc.data), len(orig_b), 'diff>17', int((np.abs(chk.astype(int) - cur.astype(int)).max(axis=2) > 17).sum()))
    if write:
        open(os.path.join(TD, tid + '.pvr'), 'wb').write(enc.data)
