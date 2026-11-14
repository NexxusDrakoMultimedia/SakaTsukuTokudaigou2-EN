import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art1_gen2.py')
s = open(p, encoding='utf8').read()
s = s.replace('"dilate": 1, "fill": "hfill"}}]})\n\n# 07308', '"dilate": 1, "fill": "hvfill"}}]})\n\n# 07308') if False else s
s = s.replace('"ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "hfill"}', '"ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "hvfill"}')
s = s.replace('"size": "auto", "max_size": 13, "min_sx": 0.7, "align": "left",\n      "erase"', '"size": "auto", "max_size": 13, "min_sx": 0.7, "align": "left", "erase_rect": [6, 6, 66, 25],\n      "erase"')
s = s.replace('"size": "auto", "max_size": 22, "align": "right",\n      "erase"', '"size": "auto", "max_size": 22, "align": "right", "erase_rect": [40, 38, 38, 32],\n      "erase"')
s = s.replace('"x": 1, "y": 172, "w": 46, "h": 28, "size": "auto", "max_size": 18, "align": "center",\n      "erase": {"mode": "mask", "ink": YINK, "dilate": 1, "fill": "hfill"}, "erase_rect": [0, 170, 48, 34]},',
              '"x": 1, "y": 174, "w": 46, "h": 30, "size": "auto", "max_size": 18, "align": "center",\n      "erase": {"mode": "flat", "color": [0, 82, 82]}, "erase_rect": [0, 174, 48, 31]},')
open(p, 'w', encoding='utf8').write(s)
