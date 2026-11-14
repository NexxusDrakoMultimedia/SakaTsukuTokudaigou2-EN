import re
p = 'tools/re/art3_run.py'
s = open(p, encoding='utf8').read()
s = s.replace("""    after, rep = arttext.render_spec(spec, before, os.path.dirname(spec_path), gl)""",
"""    src = before
    for rr in spec.get('art3_row_mode', []):      # rebuild gradient bars under old text: per row, the most common colour
        a = np.asarray(src).copy()
        x0, x1 = rr['x']
        y0, y1 = rr['y']
        for y in range(y0, y1):
            row = a[y, x0 + 2:x1 - 2].reshape(-1, 4)
            vals, cnt = np.unique(row, axis=0, return_counts=True)
            a[y, x0 + 2:x1 - 2] = vals[cnt.argmax()]
        src = Image.fromarray(a, 'RGBA')
    after, rep = arttext.render_spec(spec, src, os.path.dirname(spec_path), gl)""")
open(p, 'w', encoding='utf8').write(s)
