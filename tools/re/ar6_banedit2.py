"""ar6_banedit2: ar6_banner.py: caps from clean donors per colour class; plate minimum width 132 (idempotent)."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ar6_banner.py')
s = open(p, encoding='utf8').read()
s = s.replace("    L1 = max(0, min(L0, int(round(inkl - 30))))\n    n = np.zeros_like(a)\n    for x in range(L1, L1 + CAP):\n        n[:, x] = a[:, L0 + (x - L1)]\n    capl = a[:, L0 + CAP - 1]\n",
 "    L1 = max(0, min(124, int(round(inkl - 30))))\n    n = np.zeros_like(a)\n    da, dL0 = donor(a)\n    for x in range(L1, L1 + CAP):\n        n[:, x] = da[:, dL0 + (x - L1)]\n    capl = da[:, dL0 + CAP - 1]\n")
s = s.replace("def build(t, text):", '''_DON = {}


def donor(a):
    """clean left cap of the same colour class: blue 04706, red 04163, orange 04263 (their text starts well right of the cap)"""
    ref = np.median(a[20:30, 252:255, :3], axis=(0, 1))
    if ref[0] > 120 and ref[2] < 60:
        k = '04263' if ref[1] > 90 else '04163'
    elif ref[0] > ref[2] + 40:
        k = '04163'
    else:
        k = '04706'
    if k not in _DON:
        d = L.load(k)['arr'].astype(int)
        _DON[k] = (d, plate_of(d))
    return _DON[k]


def build(t, text):''')
open(p, 'w', encoding='utf8').write(s)
print('ok')
