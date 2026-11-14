import sys, numpy as np
from PIL import Image
i = sys.argv[1]; x0, x1, y0, y1 = map(int, sys.argv[2:6])
for nm, p in (('orig', f'build/art1/orig/{i}.png'), ('new', f'build/art1/new/{i}.dec.png')):
    a = np.asarray(Image.open(p).convert('RGBA'))
    print(nm)
    for y in range(y0, y1):
        print('%3d' % y, ''.join('.' if a[y, x, 3] < 128 else ('#' if a[y, x, 2] > 200 else 'o') for x in range(x0, x1)))
