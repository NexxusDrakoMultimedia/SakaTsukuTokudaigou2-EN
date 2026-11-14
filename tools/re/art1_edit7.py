import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art1_gen2.py')
s = open(p, encoding='utf8').read()
s = s.replace('{"sat_lt": 0.18, "luma_gt": 90}, {"luma_lt": 55}', '{"sat_lt": 0.18, "luma_gt": 90}, {"color": [16, 16, 66], "tol": 30}, {"color": [0, 0, 0], "tol": 30}')
s = s.replace('"erase_rect": [6, 6, 66, 25],', '"erase_rect": [6, 7, 62, 22],')
open(p, 'w', encoding='utf8').write(s)
