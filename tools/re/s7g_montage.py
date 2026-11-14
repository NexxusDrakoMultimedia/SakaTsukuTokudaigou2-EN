"""s7g_montage OUT.png IN.png [IN.png...] : horizontal montage of PNGs (RGBA over blue-grey)."""
import sys
from PIL import Image
ims = []
for p in sys.argv[2:]:
    a = Image.open(p).convert('RGBA'); b = Image.new('RGBA', a.size, (70, 70, 110, 255)); b.alpha_composite(a); ims.append(b.convert('RGB'))
W = sum(i.width for i in ims) + 6 * (len(ims) - 1); H = max(i.height for i in ims)
c = Image.new('RGB', (W, H), (0, 0, 0)); x = 0
for i in ims:
    c.paste(i, (x, 0)); x += i.width + 6
c = c.resize((c.width * 2, c.height * 2), Image.NEAREST) if c.width < 700 else c
c.save(sys.argv[1])
