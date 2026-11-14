import re
p = 'tools/re/art1_run.py'
s = open(p, encoding='utf8').read()
s = s.replace("    base = np.asarray(img).astype(np.float64)\n",
"""    for x, y, w, h, cx in spec.get('prefill', []):   # am2: row fill from column cx over (x, y, w, h)
        a = np.array(img)
        a[y:y + h, x:x + w] = a[y:y + h, cx:cx + 1]
        img = Image.fromarray(a, 'RGBA')
    base = np.asarray(img).astype(np.float64)
""")
open(p, 'w', encoding='utf8').write(s)
import json
for n, pf in (('00002', [[66, 140, 52, 26, 64]]), ('10475', [[66, 140, 52, 26, 64]])):
    q = 'tools/re/art1_spec/%s.json' % n
    d = json.load(open(q, encoding='utf8'))
    d['prefill'] = pf
    for r in d['regions']:
        if r['id'] == 'man':
            r.pop('hsmooth', None); r['erase'] = None; r.pop('erase_rect', None)
    json.dump(d, open(q, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
