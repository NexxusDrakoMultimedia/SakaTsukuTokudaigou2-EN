"""skm7_nendump.py FILE_REL OFF_HEX LEN_HEX: hex + cp932 dump of an extracted overlay region.  Read only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP      # noqa: E402

d = MP.read_extracted(sys.argv[1])
o, n = int(sys.argv[2], 16), int(sys.argv[3], 16)
for i in range(o, o + n, 16):
    row = d[i:i + 16]
    print('%05x  %-48s %s' % (i, row.hex(' '), ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)))
