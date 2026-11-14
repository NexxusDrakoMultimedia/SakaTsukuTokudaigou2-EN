import sys
from PIL import Image
i, x0, y0, x1, y1, s = sys.argv[1], *map(int, sys.argv[2:7])
out_name = sys.argv[7]
pair = []
for src in (f'build/art1/orig/{i}.png', f'build/art1/new/{i}.dec.png'):
    im = Image.open(src).convert('RGBA').crop((x0, y0, x1, y1))
    bg = Image.new('RGBA', im.size, (70, 90, 70, 255)); bg.alpha_composite(im)
    pair.append(bg.resize((im.width*s, im.height*s), Image.NEAREST))
w, h = pair[0].size
out = Image.new('RGB', (w, h*2+6), (255, 0, 255))
out.paste(pair[0], (0, 0)); out.paste(pair[1], (0, h+6))
out.save(f'build/art1sk/{out_name}.png')
