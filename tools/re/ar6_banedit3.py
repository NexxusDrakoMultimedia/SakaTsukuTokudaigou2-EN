"""ar6_banedit3: ar6_banner.py: style simplification levels when a banner does not pack into its slot (idempotent)."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ar6_banner.py')
s = open(p, encoding='utf8').read()
if 'STYLE_LEVEL' not in s:
    s = s.replace("def plate_of(a):", '''STYLE_LEVEL = [0]


def style_for(level):
    st = dict(TEXT_STYLE)
    if level >= 1:
        st['fill'] = '#ffffff'
        st.pop('gradient', None)
    if level >= 2:
        st['aa'] = False
    if level >= 3:
        st.pop('outline', None)
    return st


def plate_of(a):''', 1)
    s = s.replace("pad=0, style=dict(TEXT_STYLE))", "pad=0, style=style_for(STYLE_LEVEL[0]))")
    old = s[s.index("        out, info = build(t, WORDS[i])"):s.index("        print(msg)")]
    new = '''        lvl = 0
        while True:
            STYLE_LEVEL[0] = lvl
            out, info = build(t, WORDS[i])
            msg = '%s %-30s L0=%3d L1=%3d w=%5.1f size=%s sx=%s lvl=%d' % (i, WORDS[i], info['L0'], info['L1'], info['block'][0], info['size'], info['squash'], lvl)
            if not write:
                break
            new = L.pvr.encode(np.asarray(out.convert('RGBA')), original=t['pvr'])
            fr = L.fit_report(new, t)
            if all(r[2] for r in fr):
                _, w = L.encode_and_write(t, out)
                msg += ' wrote %d' % len(w)
                break
            if lvl >= 3:
                msg += ' DOES NOT FIT: ' + str([r[3] for r in fr if not r[2]])[:100]
                bad += 1
                break
            lvl += 1
        out.save(os.path.join(OUT, i + '.png'))
        if info['warn']:
            msg += ' WARN ' + '; '.join(info['warn'])[:60]
'''
    s = s.replace(old, new)
    open(p, 'w', encoding='utf8').write(s)
print('ok')
