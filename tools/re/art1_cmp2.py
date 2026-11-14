"""art1_cmp2 - diff bytes inside [lo,hi). python -I -X utf8 tools/re/art1_cmp2.py A B LO HI (ints, 0x ok)"""
import sys
a = open(sys.argv[1], 'rb').read(); b = open(sys.argv[2], 'rb').read()
lo, hi = int(sys.argv[3], 0), int(sys.argv[4], 0)
d = [i for i in range(lo, min(hi, len(a), len(b))) if a[i] != b[i]]
print(len(d), [hex(i) for i in d[:8]], [hex(i) for i in d[-3:]])
