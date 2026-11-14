"""ar6_tvedit: apply the ar6 heading-width change to tools/re/arttv_build.py (idempotent)."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arttv_build.py')
s = open(p, encoding='utf8').read()
a = "reg.append({'id': rid + '_b', 'text': word, 'x': 146, 'y': y, 'w': 108, 'h': 40,\n                    'erase_rect': [140, ey, 116, eh], 'erase': CLEAR, 'style': rid, 'size': 27, 'min_sx': 0.7,"
b = "reg.append({'id': rid + '_b', 'text': word, 'x': 146, 'y': y, 'w': 70, 'h': 40, 'font': ['arial-narrow-bold', 'arial-bold'],\n                    'erase_rect': [140, ey, 116, eh], 'erase': CLEAR, 'style': rid, 'size': 27, 'min_sx': 0.6,"
if a in s:
    s = s.replace(a, b)
c = "{'id': 'l2', 'text': line2, 'x': 4, 'y': 42, 'w': 122, 'h': 38, 'erase_rect': [0, 41, 128, 42],\n            'erase': CLEAR, 'style': style, 'size': 25, 'min_sx': 0.7,"
d = "{'id': 'l2', 'text': line2, 'x': 6, 'y': 42, 'w': 80, 'h': 38, 'erase_rect': [0, 41, 128, 42], 'font': ['arial-narrow-bold', 'arial-bold'],\n            'erase': CLEAR, 'style': style, 'size': 25, 'min_sx': 0.6,"
if c in s:
    s = s.replace(c, d)
open(p, 'w', encoding='utf8').write(s)
print('edited')
