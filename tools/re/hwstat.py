"""hwstat.py SOURCE... : count hw-katakana strings (NUL bounded, aligned) in an overlay and how many are pointer targets."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import textdb as T

HW = re.compile(rb'(?<![^\x00])([\xa1-\xdf][\xa1-\xdf A-Za-z.\-]{2,23})(?=\x00)')
for src in sys.argv[1:]:
    img = T.load_image(src)
    d = img.data
    ptrs = T.find_pointers(img)
    tg = {}
    for w, t in ptrs.items():
        tg.setdefault(t, []).append(w)
    n = refd = al = 0
    cov = 0
    unref = []
    for m in HW.finditer(d):
        o = m.start(1)
        if o % 4:
            continue
        s = m.group(1)
        if re.search(rb'(.)\1\1', s):
            continue
        n += 1
        if o in tg:
            refd += 1
        else:
            unref.append((o, s.decode('cp932')))
    print(src, 'base %#x' % img.base, 'hw strings', n, 'pointer-referenced', refd, 'unref', n - refd, unref[:8])
