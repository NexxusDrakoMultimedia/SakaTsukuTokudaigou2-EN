"""mn5_texpng.py PVR OUT.png [x y w h scale]: decode a repo texture file to a PNG (optional crop + integer upscale), alpha over magenta."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image
import pvr
a = pvr.decode(open(sys.argv[1], 'rb').read())
if len(sys.argv) > 3:
    x, y, w, h, s = [int(v) for v in sys.argv[3:8]]
    a = a[y:y + h, x:x + w]
else:
    s = 1
al = a[..., 3:4].astype(float) / 255
rgb = (a[..., :3] * al + np.array([255, 0, 255]) * (1 - al)).astype(np.uint8)
im = Image.fromarray(rgb)
im = im.resize((im.width * s, im.height * s), Image.NEAREST)
im.save(sys.argv[2])
print(im.size)
