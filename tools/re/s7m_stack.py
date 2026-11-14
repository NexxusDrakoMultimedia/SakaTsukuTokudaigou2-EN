"""s7m_stack OUT.png IN.png ... : stack PNGs vertically."""
import sys
from PIL import Image
ims = [Image.open(p) for p in sys.argv[2:]]
W = max(i.width for i in ims); H = sum(i.height for i in ims) + 4 * len(ims)
c = Image.new('RGB', (W, H), (20, 20, 20)); y = 0
for i in ims:
    c.paste(i, (0, y)); y += i.height + 4
c.save(sys.argv[1])
