"""skart2_orig - save the decoded ORIGINAL of texture ids to OUTDIR/ID_o.png (grey bg): OUTDIR ID..."""
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L
for i in sys.argv[2:]:
    a = L.load(i)['arr']
    im = Image.fromarray(a.astype('uint8'), 'RGBA')
    bg = Image.new('RGBA', im.size, (110, 110, 110, 255)); bg.alpha_composite(im)
    bg.convert('RGB').save(os.path.join(sys.argv[1], i + '_o.png'))
