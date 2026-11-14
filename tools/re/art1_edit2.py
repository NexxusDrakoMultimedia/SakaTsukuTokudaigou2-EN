import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art1_gen.py')
s = open(p, encoding='utf8').read()
s = s.replace('ya=None, hg=False):', 'ya=None, hg=False, cp=None):')
s = s.replace('''    ex = []
    if man:''', '''    if cp:
        for h in hr:
            rr = h[3]
            h[4]["erase"] = {"mode": "copy", "src": [cp, rr[1]]}
            h[4]["erase_rect"] = [rr[0] - 2, rr[1], rr[2] + 4, rr[3]]
    ex = []
    if man:''', 1)
s = s.replace('None, None,\n    ({"x": 163, "y": 198, "w": 42, "h": 34}, {"x": 211, "y": 198, "w": 42, "h": 34}, green), None, ya=Y)',
              'None, None,\n    ({"x": 163, "y": 198, "w": 42, "h": 34}, {"x": 211, "y": 198, "w": 42, "h": 34}, green), None, ya=Y, cp=220)')
s = s.replace('None, None,\n    None, None, ya=Y)', 'None, None,\n    None, None, ya=Y, cp=220)')
s = s.replace('green), None, ya=T)', 'green), None, ya=T, cp=206)')
open(p, 'w', encoding='utf8').write(s)
