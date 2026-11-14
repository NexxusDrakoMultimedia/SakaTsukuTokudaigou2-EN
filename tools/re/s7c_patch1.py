import re
p = 'tools/re/s7c_run.py'
s = open(p, encoding='utf8').read()
s = s.replace("def spec_for(m, font, size):\n    regs = []", "def spec_for(m, font, size, level=0):\n    regs = []")
s = s.replace("font=font, size='auto', max_size=size, min_sx=0.8, pad=0, dx=1, style=dict(STYLE)))",
              "font=font, size='auto', max_size=size, min_sx=0.8, pad=0, dx=1, style=_simp(STYLE, level)))")
s = s.replace("def spec_for", '''def _simp(sty, level):
    sty = dict(sty)
    if level >= 1:
        sty['gradient'] = [[0, '#f0f0f0'], [0.6, '#f0f0f0'], [0.6, '#c8c8c8'], [1, '#c8c8c8']]
    if level >= 2:
        sty.pop('gradient'); sty['fill'] = '#eeeeee'
    if level >= 3:
        sty['aa'] = False
    return sty


def spec_for''', 1)
old = s[s.index("        blank = a.copy()"):s.index("        if write:")]
new = '''        blank = a.copy(); blank[...] = 0
        img = Image.fromarray(blank.astype(np.uint8), 'RGBA')
        with open(os.path.join(ROOT, 'extracted', 'GAME', 'STAFFLST.ZAR'), 'rb') as f:
            data = f.read()
        for level in range(4):
            out, rep = arttext.render_spec(spec_for(m, font, size, level), img)
            arr = np.asarray(out.convert('RGBA'))
            new = pvr.encode(arr, original=pv)
            assert pvr.decode(new).shape == arr.shape
            try:
                texinject.inject(data, m + '.pvr', new, 'exact')
                break
            except texinject.TexInjectError as e:
                print(m, 'level', level, 'does not fit:', str(e)[:100])
        else:
            print(m, 'FAILED to fit'); continue
        for w in rep.get('warnings', []):
            print(m, 'WARN', w)
        out.save(os.path.join(OUT, 'out', m + '.png'))
        b = Image.fromarray(a.astype(np.uint8), 'RGBA').crop((0, 0, 128, 104))
        n = Image.fromarray(np.asarray(pvr.decode(new)).astype(np.uint8), 'RGBA').crop((0, 0, 128, 104))
        c = Image.new('RGBA', (260, 104), (90, 90, 110, 255))
        bb = Image.new('RGBA', b.size, (90, 90, 110, 255)); bb.alpha_composite(b); c.paste(bb, (0, 0))
        nb = Image.new('RGBA', n.size, (90, 90, 110, 255)); nb.alpha_composite(n); c.paste(nb, (132, 0))
        c.resize((520, 208), Image.NEAREST).convert('RGB').save(os.path.join(OUT, 'v', m + '_ba.png'))
        print(m, 'fits at level', level, len(new), 'bytes')
'''
s = s.replace(old, new)
open(p, 'w', encoding='utf8').write(s)
