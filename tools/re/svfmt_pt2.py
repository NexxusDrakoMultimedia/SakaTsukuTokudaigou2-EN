"""svfmt_pt2.py DUMP : names that look like ascii in the 288-byte table at 0x8ce4c004; last used index."""
import sys
d = open(sys.argv[1], 'rb').read(); B = 0x8c000000
last = -1; cnt = 0
for n in range(0, 5400):
    a = 0x8ce4c004 + n * 0x120
    r = d[a - B:a - B + 14]
    if r[0] and all(32 <= c < 127 for c in r.split(b'\0')[0]):
        last = n; cnt += 1
print('ascii-named records', cnt, 'last index', last, 'end addr', hex(0x8ce4c004 + (last + 1) * 0x120))
