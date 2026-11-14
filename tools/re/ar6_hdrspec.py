"""ar6_hdrspec: header unit cells (Mo / Wk) get left padding so the code-placed digit sprites do not overlap them.
Moves the 'mo' and 'wk' regions of the art1 specs right by DX, narrows them (Mo 19 px, Wk 24 px at the 512 grid) and uses a
narrow face; the old kanji stay inside the (unchanged or widened) erase rectangles.  Idempotent.
Usage: ar6_hdrspec.py"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, 'art1_spec')
# id -> (old mo x, old wk x) before the change; the new x is old + 5
TARGET = {'00002': (260, 296), '07332': (260, 296), '10469': (260, 296), '10475': (260, 296),
          '37285': (131, 173), '10470': (145, 187), '10474': (145, 187)}
FONT = ['arial-narrow-bold', 'segoe-ui-bold', 'arial-bold']
for i, (mx, wx) in TARGET.items():
    p = os.path.join(SPEC, i + '.json')
    s = json.load(open(p, encoding='utf8'))
    for r in s['regions']:
        if r['id'] == 'mo':
            r.update(x=mx + 5, w=16, align='left', font=FONT, size=16, min_sx=0.5)
            er = r.get('erase_rect')
            r['erase_rect'] = [mx - 1, er[1] if er else r['y'] - 2, 26, er[3] if er else r['h'] + 4]
        if r['id'] == 'wk':
            r.update(x=wx + 5, w=24, align='left', font=FONT, size=17, min_sx=0.6)
            er = r.get('erase_rect')
            r['erase_rect'] = [wx - 1, er[1] if er else r['y'] - 2, 32, er[3] if er else r['h'] + 4]
    json.dump(s, open(p, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(i, 'ok')
