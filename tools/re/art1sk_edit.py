import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art1sk_fix04112.py')
s = open(p, encoding='utf8').read()
s = s.replace("\npy = np.pad(yellow, 1)\nyellow = sum(py[1 + dy:1 + dy + H, 1 + dx:1 + dx + W] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) > 0", "")
s = s.replace("    out[y, x] = a[yr, xr]", "    if y >= 231:\n        yr = y\n        xr = 34 + ((x - 143) % 76)\n    out[y, x] = a[yr, xr]")
open(p, 'w', encoding='utf8').write(s)
