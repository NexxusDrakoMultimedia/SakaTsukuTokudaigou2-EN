import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art1_gen2.py')
s = open(p, encoding='utf8').read()
s = s.replace('"x": 143, "y": 205, "w": 96, "h": 44,', '"x": 143, "y": 206, "w": 88, "h": 42,')
s = s.replace('"align": "center", "erase": {"mode": "mask", "ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "diffuse"}}]})',
              '"align": "center", "erase": {"mode": "mask", "ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "hfill"}}]})')
s = s.replace('"x": 168, "y": 0, "w": 70, "h": 28, "size": "auto", "max_size": 20, "align": "right",\n    "erase": {"mode": "mask", "ink": [{"color": [238, 255, 68], "tol": 70}, {"luma_lt": 65, "sat_gt": 0.6}], "dilate": 1, "fill": "hfill"}}]})',
              '"x": 168, "y": 0, "w": 70, "h": 29, "size": "auto", "max_size": 20, "align": "right",\n    "erase": {"mode": "mask", "ink": [{"color": [238, 255, 68], "tol": 70}, {"luma_lt": 105, "sat_gt": 0.3}], "dilate": 1, "fill": "hfill"}}]})')
s = s.replace('"x": 6, "y": 6, "w": 64, "h": 24, "size": "auto", "max_size": 13, "min_sx": 0.7, "align": "left",\n      "erase": {"mode": "mask", "ink": [{"sat_lt": 0.18, "luma_gt": 90}, {"luma_lt": 50}], "dilate": 1, "fill": "hfill"}},',
              '"x": 6, "y": 8, "w": 64, "h": 19, "size": "auto", "max_size": 13, "min_sx": 0.7, "align": "left",\n      "erase": {"mode": "mask", "ink": [{"sat_lt": 0.18, "luma_gt": 90}, {"color": [16, 16, 66], "tol": 40}], "dilate": 1, "fill": "hfill"}},')
s = s.replace('"ink": [{"color": [239, 255, 66], "tol": 80}], "dilate": 2, "fill": "hfill"}},', '"ink": [{"color": [239, 255, 66], "tol": 80}, {"luma_lt": 14}], "dilate": 2, "fill": "hfill"}},')
s = s.replace('"erase_rect": [0, 170, 48, 32]}', '"erase_rect": [0, 170, 48, 34]}')
s = s.replace('"text": "Income", "style": "silver", "x": 88, "y": 163, "w": 64, "h": 28, "size": "auto", "max_size": 24,', '"text": "Income", "style": "silver", "x": 88, "y": 163, "w": 62, "h": 28, "size": "auto", "max_size": 20,')
s = s.replace('"text": "Total", "style": "silver", "x": 152,', '"text": "Total", "style": "silver", "x": 158,')
s = s.replace('"text": "Expenses", "style": "silver", "x": 90, "y": 195, "w": 100, "h": 30, "size": "auto", "max_size": 24,', '"text": "Expenses", "style": "silver", "x": 90, "y": 195, "w": 100, "h": 30, "size": "auto", "max_size": 20,')
open(p, 'w', encoding='utf8').write(s)
