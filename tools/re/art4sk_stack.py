import sys, os
from PIL import Image
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'build', 'art4sk')
out = sys.argv[1]; names = sys.argv[2:]
ims = [Image.open(os.path.join(d, n)) for n in names]
W = max(i.width for i in ims); H = sum(i.height + 6 for i in ims)
s = Image.new('RGB', (W, H), (255, 0, 255)); y = 0
for i in ims: s.paste(i, (0, y)); y += i.height + 6
s.save(os.path.join(d, out))
