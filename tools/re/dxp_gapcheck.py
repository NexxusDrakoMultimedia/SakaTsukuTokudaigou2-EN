"""Read-only: are the free gap sectors zero user data, and are they valid Mode 1 sectors? usage: dxp_gapcheck.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D
src = D.Source('.')
for a, b in ((45061, 51342), (549000, 549150)):
    z = ok = raw0 = 0
    for l in range(a, b):
        r = src.raw(l)
        if r[16:2064] == bytes(2048): z += 1
        if r == bytes(2352): raw0 += 1
        elif D.sector_ok(l, r): ok += 1
    print(a, b, 'sectors', b - a, 'zero user', z, 'raw all-zero', raw0, 'valid mode1', ok)
