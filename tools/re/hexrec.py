"""hexrec.py FILE START STRIDE COUNT [WIDTH] : print records as hex + cp932 text"""
import sys
d = open(sys.argv[1], 'rb').read()
s = int(sys.argv[2], 16); st = int(sys.argv[3]); n = int(sys.argv[4])
for i in range(n):
    r = d[s + i * st: s + (i + 1) * st]
    print('%06x ' % (s + i * st), r.hex(' ', 1)[:3 * 64], '|', r.decode('cp932', 'replace').replace('\x00', '.').replace('\n', '~'))
