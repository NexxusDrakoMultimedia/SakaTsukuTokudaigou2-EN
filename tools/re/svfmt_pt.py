"""svfmt_pt.py DUMP : probe the 288-byte player table around 0x8ce4c004 in a RAM dump."""
import sys, struct
d = open(sys.argv[1], 'rb').read()
B = 0x8c000000
def s(a, n=14):
    r = d[a - B:a - B + n]; return r.split(b'\0')[0].decode('cp932', 'replace')
for n in [-1, 0, 1, 2, 100, 226, 227, 228, 229, 1000, 3000, 5319, 5320, 5321]:
    a = 0x8ce4c004 + n * 0x120
    print(n, hex(a), repr(s(a)))
