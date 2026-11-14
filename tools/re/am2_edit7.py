p = 'tools/re/art5_plates.py'
s = open(p, encoding='utf8').read()
s = s.replace("""        o = L.over(i, img)
        if o <= 400:   # am2: --texture-policy grow lets a stream exceed its slot; keep the best-looking variant
            if o > 0:
                print(i, "grows by", o, "bytes")
            break
""", """        if L.over(i, img) <= 0:
            break
""")
s = s.replace("    for v in (0, 1, 2):\n        VAR[0] = v\n        img = build()", "    for v in (0, 1, 2, 3):\n        VAR[0] = v\n        img = build()")
s = s.replace("    if VAR[0] >= 2:\n        d['aa'] = False\n", "    if VAR[0] >= 2:\n        d['aa'] = False\n    if VAR[0] >= 3:   # am2: no shadow either (the wider 'Yen' plates only fit this way)\n        d.pop('shadow', None)\n")
open(p, 'w', encoding='utf8').write(s)
