"""am2_over - how many bytes over its slot is the Yen plate in each variant."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = ['x']
import art5_lib as L
import numpy as np
from PIL import Image
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art5_plates.py'), encoding='utf8').read()
ns = {'__file__': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art5_plates.py')}
head = src.split("T = {")[0]
exec(compile(head, 'plates_head', 'exec'), ns)
for i in ('03555', '03556', '03557', '03560', '03562'):
    for v in (0, 1, 2):
        ns['VAR'][0] = v
        a = ns['clear_from'](L.load(i), 97)
        img = L.render(i, {'regions': [ns['reg']('Yen', 98, 5, 30, 23, 20)]}, a)
        print(i, v, L.over(i, img))
