"""s7p_view PVR_FILE OUT_PNG [SCALE] - decode a written texture file on the game's blue, enlarged."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import numpy as np
from PIL import Image
import pvr
import s7p_dump as D
a = np.asarray(pvr.decode(open(sys.argv[1], 'rb').read()))
sc = int(sys.argv[3]) if len(sys.argv) > 3 else 3
D.on_bg(a).resize((a.shape[1] * sc, a.shape[0] * sc), Image.NEAREST).save(sys.argv[2])
print(a.shape)
