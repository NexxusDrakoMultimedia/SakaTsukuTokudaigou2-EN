import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art1_gen2.py')
s = open(p, encoding='utf8').read()
s = s.replace('"x": 143, "y": 206, "w": 88, "h": 42,', '"x": 143, "y": 207, "w": 88, "h": 40,')
s = s.replace('"ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "hvfill"}}]})',
              '"ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "diffuse"}},\n   {"id": "tick", "ja": "年", "x": 143, "y": 203, "w": 88, "h": 4, "erase": {"mode": "mask", "ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "hfill"}}]})')
s = s.replace('{"sat_lt": 0.18, "luma_gt": 90}, {"color": [16, 16, 66], "tol": 40}', '{"sat_lt": 0.18, "luma_gt": 90}, {"luma_lt": 55}')
open(p, 'w', encoding='utf8').write(s)
