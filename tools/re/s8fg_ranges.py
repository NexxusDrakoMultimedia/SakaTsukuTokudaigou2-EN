"""s8fg: differing byte ranges between two files (merge gap G), optionally only inside [lo,hi).
usage: s8fg_ranges.py A B [GAP=16] [LO HI]   (hex lo/hi)"""
import sys
a = open(sys.argv[1], 'rb').read()
b = open(sys.argv[2], 'rb').read()
gap = int(sys.argv[3]) if len(sys.argv) > 3 else 16
lo = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0
hi = int(sys.argv[5], 16) if len(sys.argv) > 5 else min(len(a), len(b))
rs = []
i = lo
n = min(len(a), len(b), hi)
cur = None
while i < n:
    if a[i] != b[i]:
        if cur and i - cur[1] <= gap:
            cur[1] = i + 1
        else:
            if cur:
                rs.append(cur)
            cur = [i, i + 1]
    i += 1
if cur:
    rs.append(cur)
tot = sum(e - s for s, e in rs)
print('ranges', len(rs), 'span bytes', tot, 'sizes', len(a), len(b))
for s, e in rs:
    print('%06x-%06x %6d' % (s, e, e - s))
