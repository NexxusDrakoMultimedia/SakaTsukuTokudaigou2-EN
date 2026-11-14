import json
p = 'tools/re/art1_run.py'
s = open(p, encoding='utf8').read()
s = s.replace("    base = np.asarray(img).astype(np.float64)\n",
"""    pf = spec.get('polyfill')   # am2: rebuild a plate with a slanted bevelled left edge under an erased glyph
    if pf:
        a = np.array(img)
        for y in range(pf['y0'], pf['y1'] + 1):
            ex = int(round(pf['e0'] + (pf['e1'] - pf['e0']) * (y - pf['y0']) / float(pf['y1'] - pf['y0'])))
            a[y, ex:pf['xend']] = pf['body'] + [255]
            for k, c in enumerate(pf['edge']):
                a[y, ex + k] = c + [255]
        for x in range(pf['xstart'], pf['xend']):
            a[pf['y0'], x] = pf['top'] + [255] if a[pf['y0'], x, 3] else a[pf['y0'], x]
        img = Image.fromarray(a, 'RGBA')
    base = np.asarray(img).astype(np.float64)
""", 1)
open(p, 'w', encoding='utf8').write(s)
q = 'tools/re/art1_spec/07308.json'
d = json.load(open(q, encoding='utf8'))
d['polyfill'] = {'y0': 8, 'y1': 23, 'e0': 185, 'e1': 170, 'xstart': 185, 'xend': 237, 'body': [0x66, 0x77, 0xbb],
                 'edge': [[0xcc, 0xcc, 0xee], [0xaa, 0xbb, 0xdd]], 'top': [0x88, 0x88, 0xcc]}
d['post'] = {'clear': [[160, 0, 90, 8]], 'edge': [160, 8, 23, 185, 170, 190]}
json.dump(d, open(q, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
