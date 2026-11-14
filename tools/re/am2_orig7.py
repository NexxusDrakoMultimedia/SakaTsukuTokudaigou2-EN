"""am2_orig7 - save the decoded original of art7 ids as build/am2/o7_ID.png. python -I -X utf8 tools/re/am2_orig7.py ID ..."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L
from PIL import Image
for i in sys.argv[1:]:
    t = L.load(i)
    a = t['arr'] if 'arr' in t else None
    print(i, list(t.keys()))
    Image.fromarray(a.astype('uint8'), 'RGBA').save(os.path.join(L.ROOT, 'build', 'am2', 'o7_%s.png' % i))
