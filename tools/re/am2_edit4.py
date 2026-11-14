import json
p = 'tools/re/art1_run.py'
s = open(p, encoding='utf8').read()
s = s.replace("    out.save(os.path.join(B, 'new', i + '.png'))\n",
"""    if spec.get('post'):   # am2: alpha repairs after the render
        a = np.array(out)
        for x, y, w, h in spec['post'].get('clear', []):
            a[y:y + h, x:x + w, 3] = 0
        e = spec['post'].get('edge')   # [xmin, y0, y1, e0, e1, xend]: left of the slanted edge transparent, right of it opaque up to xend
        if e:
            xmin, y0, y1, e0, e1, xend = e
            for y in range(y0, y1 + 1):
                ex = int(round(e0 + (e1 - e0) * (y - y0) / float(y1 - y0)))
                a[y, xmin:ex, 3] = 0
                a[y, ex:xend, 3] = 255
        out = Image.fromarray(a, 'RGBA')
    out.save(os.path.join(B, 'new', i + '.png'))
""", 1)
open(p, 'w', encoding='utf8').write(s)
q = 'tools/re/art1_spec/07308.json'
d = json.load(open(q, encoding='utf8'))
d['post'] = {'clear': [[160, 0, 90, 8]], 'edge': [160, 8, 22, 185, 173, 200]}
for r in d['regions']:
    if r['id'] == 'man':
        r['y'] = 3; r['h'] = 29
json.dump(d, open(q, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
