"""ar6_stack: stack PNGs vertically: ar6_stack.py OUT IN ... (left aligned)"""
import sys
from PIL import Image
ims = [Image.open(p).convert('RGB') for p in sys.argv[2:]]
W = max(i.width for i in ims); H = sum(i.height + 4 for i in ims)
o = Image.new('RGB', (W, H), (30, 30, 30)); y = 0
for i in ims:
    o.paste(i, (0, y)); y += i.height + 4
o.save(sys.argv[1])
