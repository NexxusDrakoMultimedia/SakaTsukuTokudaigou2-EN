import re, os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art1_gen.py')
s = open(p, encoding='utf8').read()
# oku text
s = s.replace('"text": "x100M", "style": "oku", "size": 17,', '"text": "100M", "style": "oku", "size": 18,')
# hgrad header option
s = s.replace('def bar(i, tid, qf, hdr_ink, hs, man, oku, half, man_ink, ha=None, hb=None, ya=None):',
              'def bar(i, tid, qf, hdr_ink, hs, man, oku, half, man_ink, ha=None, hb=None, ya=None, hg=False):')
s = s.replace('''    ex = []
    if man:''', '''    if hg:
        er = {"yr": [196, 34, 42, 34], "mo": [260, 34, 22, 34], "wk": [296, 34, 26, 34]}
        for h in hr:
            h[4]["erase"] = {"mode": "hgrad"}
            h[4]["erase_rect"] = er[h[0]]
    ex = []
    if man:''')
s = s.replace('''"erase": {"mode": "mask", "ink": man_ink, "dilate": 1, "fill": "hfill"}}, **man[1]))''',
              '''"erase": ({"mode": "hgrad"} if hg else {"mode": "mask", "ink": man_ink, "dilate": 1, "fill": "hfill"}),
                        "erase_rect": man[2]}, **man[1]))''')
# man tuples get an erase rect as third element
s = s.replace('(sty("#ffffff", "#d0ecd8", "#000000", "#000000"), {"x": 66, "y": 139, "w": 52, "h": 27, "align": "right"}),',
              '(sty("#ffffff", "#d0ecd8", "#000000", "#000000"), {"x": 66, "y": 141, "w": 49, "h": 24, "align": "right"}, [70, 141, 45, 24]),')
s = s.replace('(sty("#292194", "#292194", None, "#000000"), {"x": 62, "y": 126, "w": 62, "h": 36}),',
              '(sty("#292194", "#292194", None, "#000000"), {"x": 62, "y": 126, "w": 52, "h": 36}, [60, 128, 54, 34]),')
s = s.replace('(sty("#c6d600", "#c6d600", None, "#000000"), {"x": 62, "y": 126, "w": 62, "h": 36}),',
              '(sty("#c6d600", "#c6d600", None, "#000000"), {"x": 62, "y": 126, "w": 52, "h": 36}, [60, 128, 54, 34]),')
s = s.replace('''    [{"color": [41, 33, 148], "tol": 45}, {"luma_lt": 40}])''', '''    [{"color": [41, 33, 148], "tol": 45}, {"luma_lt": 40}], hg=True)''')
s = s.replace('''    [{"color": [198, 214, 0], "tol": 45}, {"luma_lt": 40}])''', '''    [{"color": [198, 214, 0], "tol": 45}, {"luma_lt": 40}], hg=True)''')
s = s.replace('HALF_A = [{"x": 466, "y": 299, "w": 46, "h": 33}, {"x": 466, "y": 338, "w": 46, "h": 33}]',
              'HALF_A = [{"x": 466, "y": 296, "w": 46, "h": 37}, {"x": 466, "y": 335, "w": 46, "h": 38}]')
open(p, 'w', encoding='utf8').write(s)
