"""s7e_boxes: ink component boxes of an id inside a crop (texture coords).
    python -I -X utf8 tools/re/s7e_boxes.py ID x,y,w,h [gx] [gy] [--cur]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import art7_lib as L
import pvr

args = [a for a in sys.argv[1:] if not a.startswith('--')]
t = L.load(args[0])
arr = t['arr']
if '--cur' in sys.argv:
    arr = np.asarray(pvr.decode(open(L.tex_path(t['src'], t['tid']), 'rb').read())).copy()
x, y, w, h = [int(v) for v in args[1].split(',')]
gx = int(args[2]) if len(args) > 2 else 5
gy = int(args[3]) if len(args) > 3 else 2
sub = arr[y:y + h, x:x + w]
for b in L.components(sub, gx=gx, gy=gy, min_area=4):
    print((b[0] + x, b[1] + y, b[2], b[3]))
