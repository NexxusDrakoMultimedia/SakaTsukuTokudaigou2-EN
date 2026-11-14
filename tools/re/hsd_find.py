"""hsd: find all occurrences of a byte string and of 32-bit little-endian words (literals) in a file.
usage: hsd_find.py FILE ASCII-or-0xHEXWORD ...  Read-only."""
import sys, struct
d = open(sys.argv[1], 'rb').read()
for a in sys.argv[2:]:
    pat = struct.pack('<I', int(a, 16)) if a.startswith('0x') else a.encode()
    i = d.find(pat); r = []
    while i >= 0:
        r.append('%x' % i); i = d.find(pat, i + 1)
    print(a, r)
