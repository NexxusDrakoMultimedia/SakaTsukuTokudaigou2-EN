import json
import numpy as np
from PIL import Image
im = np.asarray(Image.open('build/art6/o_37300.png').convert('RGBA')).copy()
def plate(name, x0, y0, x1, y1, srcx):
    p = im[y0:y1, x0:x1].copy()
    for y in range(p.shape[0]):
        p[y, :] = im[y0 + y, srcx]
    Image.fromarray(p, 'RGBA').save('tools/re/art6/' + name)
plate('p37300a.png', 364, 20, 489, 106, 362)
plate('p37300b.png', 228, 138, 489, 200, 227)
white = {'font': ['segoe-ui-semibold', 'arial-bold'], 'fill': '#f4f8ff', 'shadow': {'color': '#163a8a', 'dx': 1.2, 'dy': 1.5, 'alpha': 1.0}}
gold = {'font': ['arial-narrow-bold', 'arial-bold'], 'fill': '#e0bc30', 'aa': True}
big = dict(white); big['letter_spacing'] = 1; big['shadow'] = {'color': '#163a8a', 'dx': 2, 'dy': 2, 'alpha': 1.0}
pa = {'mode': 'plate', 'path': 'p37300a.png', 'replace': True}
regs = [
 {'id': 'off', 'ja': '攻撃力', 'text': 'Offence', 'x': 368, 'y': 30, 'w': 120, 'h': 20, 'size': 17, 'align': 'left', 'style': 'white', 'erase': pa, 'erase_rect': [364, 20, 125, 86]},
 {'id': 'def', 'ja': '守備力', 'text': 'Defence', 'x': 368, 'y': 54, 'w': 120, 'h': 20, 'size': 17, 'align': 'left', 'style': 'white', 'erase': None},
 {'id': 'tir', 'ja': '疲れ', 'text': 'Tired', 'x': 368, 'y': 78, 'w': 120, 'h': 20, 'size': 17, 'align': 'left', 'style': 'white', 'erase': None},
 {'id': 'sta', 'ja': 'スタミナ', 'text': 'Stamina', 'x': 234, 'y': 156, 'w': 250, 'h': 40, 'size': 30, 'align': 'left', 'style': 'big',
  'erase': {'mode': 'plate', 'path': 'p37300b.png', 'replace': True}, 'erase_rect': [228, 138, 261, 62]},
]
ink = [{'luma_gt': 38}]
def lab(id, ja, en, x, y, w, h, align='left', size=6):
    return {'id': id, 'ja': ja, 'text': en, 'x': x, 'y': y, 'w': w, 'h': h, 'size': size, 'style': 'gold', 'align': align,
            'erase': {'mode': 'mask', 'ink': ink, 'dilate': 1, 'fill': 'diffuse'}, 'erase_rect': [x, y, w, h]}
regs += [
 lab('rate', 'チーム総合力', 'Team Rating', 26, 16, 68, 11, 'center', 9),
 lab('c_off', 'オフェンス', 'Offence', 44, 29, 34, 7, 'center', 6),
 lab('c_tac', 'タクティクス', 'Tactics', 14, 45, 29, 8, 'left', 6),
 lab('c_def', 'ディフェンス', 'Defence', 78, 45, 27, 8, 'right', 6),
 lab('c_for', 'システム', 'Formation', 14, 96, 38, 8, 'left', 6),
 lab('c_sta', 'スタミナ', 'Stamina', 62, 96, 41, 8, 'right', 6),
]
d = {'texture': '37300', 'supersample': 4, 'quantize': 'rgb565', 'regions': regs, 'styles': {'white': white, 'gold': gold, 'big': big},
     'defaults': {'min_sx': 0.7}}
json.dump(d, open('tools/re/art6/37300.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
