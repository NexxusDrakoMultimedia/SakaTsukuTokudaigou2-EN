"""s7x_inkcheck ID: print rightmost opaque-ink column per 32px row band for x>=100 of build/s7x/out/ID.png"""
import sys, os
import numpy as np
from PIL import Image
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
a = np.asarray(Image.open(os.path.join(R, 'build', 's7x', 'out', sys.argv[1] + '.png')).convert('RGBA'))
for k in range(7):
    band = a[32 * k:32 * k + 32, 100:, :]
    m = band[..., 3] > 128
    cols = np.where(m.any(axis=0))[0]
    print(k, (cols.min() + 100, cols.max() + 100) if len(cols) else None)
