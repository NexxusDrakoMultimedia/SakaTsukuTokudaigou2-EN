"""s7t: dump NUL-separated cp932 strings around an offset. usage: file off [before after]"""
import sys
f, off = sys.argv[1], int(sys.argv[2], 0)
b = int(sys.argv[3]) if len(sys.argv) > 3 else 200
a = int(sys.argv[4]) if len(sys.argv) > 4 else 300
d = open(f, 'rb').read()
lo, hi = max(0, off - b), min(len(d), off + a)
o = lo
while o < hi:
    e = d.find(b'\0', o)
    if e < 0:
        break
    if e > o:
        print('0x%x %r' % (o, d[o:e].decode('cp932', 'replace')))
    o = e + 1
