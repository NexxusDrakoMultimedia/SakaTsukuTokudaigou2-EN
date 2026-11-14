import os
d = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(d, 'art1_run.py')
s = open(p, encoding='utf8').read()
s = s.replace("    out, rep = A.render_spec(", '''    base = np.asarray(img).astype(np.float64)
    os.makedirs(os.path.join(B, 'masks'), exist_ok=True)
    for r in spec['regions']:
        hs = r.get('hsmooth')
        if hs:
            x, y, w, h = r['erase_rect']
            L = base[y:y + h, x - hs:x].mean(axis=1)
            R = base[y:y + h, x + w:x + w + hs].mean(axis=1)
            t = ((np.arange(w) + 0.5) / w)[None, :, None]
            pl = L[:, None, :] * (1 - t) + R[:, None, :] * t
            pth = os.path.join(B, 'masks', i + '_' + r['id'] + '.plate.png')
            Image.fromarray(np.clip(np.rint(pl), 0, 255).astype(np.uint8), 'RGBA').save(pth)
            r['erase'] = {'mode': 'plate', 'path': pth}
    out, rep = A.render_spec(''', 1)
open(p, 'w', encoding='utf8').write(s)
g = os.path.join(d, 'art1_gen.py')
s = open(g, encoding='utf8').read()
s = s.replace('''            h[4]["erase"] = {"mode": "copy", "src": [cp, rr[1]]}
            h[4]["erase_rect"] = [rr[0] - 2, rr[1], rr[2] + 4, rr[3]]''', '''            h[4]["hsmooth"] = 4
            h[4]["erase_rect"] = [rr[0] - 2, rr[1], rr[2] + 4, rr[3]]''')
open(g, 'w', encoding='utf8').write(s)
