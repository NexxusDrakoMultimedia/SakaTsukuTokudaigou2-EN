import sys
from PIL import Image
ids = sys.argv[1:]
for i in ids:
    a = Image.open(f'build/art1/orig/{i}.png').convert('RGBA')
    b = Image.open(f'build/art1/new/{i}.dec.png').convert('RGBA')
    w, h = a.size
    out = Image.new('RGBA', (w*2+8, h), (255, 0, 255, 255))
    for k, im in enumerate((a, b)):
        bg = Image.new('RGBA', (w, h), (70, 90, 70, 255))
        bg.alpha_composite(im)
        out.paste(bg, (k*(w+8), 0))
    out.convert('RGB').save(f'build/art1sk/{i}.png')
    print(i, a.size, b.size)
