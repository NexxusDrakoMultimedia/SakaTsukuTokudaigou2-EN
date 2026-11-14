import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = ['x', 'none']
import importlib.util
spec = importlib.util.spec_from_file_location('b', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ar6_banner.py'))
src = open(spec.origin, encoding='utf8').read().replace('\nmain()\n', '\n')
ns = {'__name__': 'b', '__file__': spec.origin}
exec(compile(src, spec.origin, 'exec'), ns)
from PIL import Image
blank = Image.new('RGBA', (256, 32), (0, 0, 0, 0))
for sz in (21, 19, 17, 15):
    _, r, w = ns['render_text'](blank, 'Local Junior High Champions', 'argb4444', 249 - 219, sz)
    print(sz, r.get('size'), r.get('squash'), r['block'], w)
