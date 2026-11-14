"""skart2_montage - stack the 'after' halves of several skart2_sheet PNGs: OUT.png IN.png [IN.png ...] (each cropped to its lower half)"""
import sys
from PIL import Image
ims = []
for p in sys.argv[2:]:
    im = Image.open(p)
    ims.append(im.crop((0, im.height // 2 + 3, im.width, im.height)))
W = max(i.width for i in ims)
H = sum(i.height + 4 for i in ims)
s = Image.new('RGB', (W, H), (255, 0, 255))
y = 0
for i in ims:
    s.paste(i, (0, y)); y += i.height + 4
s.save(sys.argv[1])
