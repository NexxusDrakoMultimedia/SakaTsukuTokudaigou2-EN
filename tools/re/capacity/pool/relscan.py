"""Risk scan: aligned u32 words (not pointer refs) equal to a movable string's file offset (>=0x10000).
Round values (multiple of 0x1000) are buffer-size style constants, others would hint at relative addressing."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import textrepack as R
tot = rnd = oth = 0; ex = []
for source, img, strs, ptrs in load_all():
    mov = {s.off for s in strs if R.is_movable(s) and s.off >= 0x10000}
    rw = {w for s in strs if R.is_movable(s) for w in s.refs}
    d = img.data
    for i in range(0, len(d) - 3, 4):
        if i in rw: continue
        v = struct.unpack_from('<I', d, i)[0]
        if v in mov:
            tot += 1
            if v % 0x1000 == 0: rnd += 1
            else:
                oth += 1
                if len(ex) < 12: ex.append((source[9:], hex(i), hex(v)))
print('hits', tot, 'multiples of 0x1000', rnd, 'others', oth); print(ex)
