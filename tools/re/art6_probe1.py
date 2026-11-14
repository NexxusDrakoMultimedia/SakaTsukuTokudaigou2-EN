import numpy as np
from PIL import Image
im = np.asarray(Image.open('build/art6/o_00165.png').convert('RGBA')).astype(int)
for y0 in (38, 39, 40):
    prof = np.stack([im[y0 + 32 * k: y0 + 32 * k + 32, 11, :3] for k in range(6)])
    print(y0, 'std over plates at x=11:', prof.std(axis=0).mean())
y0 = 39
print([tuple(im[y0 + j, 11, :3]) for j in range(0, 32, 2)])
print([tuple(im[y0 + j, 70, :3]) for j in range(0, 32, 2)])
print([tuple(im[y0 + j, 126, :3]) for j in range(0, 32, 2)])
