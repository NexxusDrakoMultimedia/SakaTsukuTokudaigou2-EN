import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
from PIL import Image
import pvr, texinject
which = sys.argv[1]  # old|new
ids = [int(a) for a in sys.argv[2:]]
ims = []
for i in ids:
    if which == 'old':
        b = texinject.extract_pvr('ETC_DATA/SS_TEX.ZAR', 'SS_PR1.TBD#%d' % i)
    else:
        b = open(os.path.join(ROOT, 'translation', 'textures', 'ETC_DATA', 'SS_TEX.ZAR', 'SS_PR1.TBD#%d.pvr' % i), 'rb').read()
    im = Image.fromarray(np.asarray(pvr.decode(b), np.uint8), 'RGBA').crop((0, 0, 256, 40))
    bg = Image.new('RGBA', im.size, (60, 60, 60, 255)); bg.alpha_composite(im)
    ims.append(bg.resize((768, 120), Image.NEAREST).convert('RGB'))
sh = Image.new('RGB', (768, 124 * len(ims)), (255, 0, 255))
for k, im in enumerate(ims): sh.paste(im, (0, k * 124))
sh.save(os.path.join(ROOT, 'build', 'art4sk', 'bars_%s.png' % which))
