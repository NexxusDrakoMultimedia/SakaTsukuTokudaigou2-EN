import sys, numpy as np
from PIL import Image
i = sys.argv[1]; x0, x1, y0, y1 = map(int, sys.argv[2:6])
a = np.asarray(Image.open(f'build/art1/new/{i}.dec.png').convert('RGBA'))
for y in range(y0, y1):
    xs = [x for x in range(x0, x1) if a[y, x, 3] > 0]
    print(y, len(xs), xs[:12])
