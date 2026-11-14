"""s7g_peek OUT.png PVR...: montage of installed pvr files (RGBA over blue-grey)"""
import sys, numpy as np
from PIL import Image
sys.path.insert(0, 'tools')
import pvr
ims = []
for p in sys.argv[2:]:
    a = np.asarray(pvr.decode(open(p, 'rb').read())).astype(np.uint8)
    im = Image.fromarray(a, 'RGBA'); b = Image.new('RGBA', im.size, (70, 70, 110, 255)); b.alpha_composite(im); ims.append(b.convert('RGB'))
c = Image.new('RGB', (sum(i.width for i in ims) + 4 * len(ims), max(i.height for i in ims)))
x = 0
for i in ims: c.paste(i, (x, 0)); x += i.width + 4
c.save(sys.argv[1])
