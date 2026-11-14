"""mn6_zeroruns.py [MIN]: zero runs of at least MIN bytes (default 0x200) in the original 1ST_READ.BIN with their load addresses.  Read only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP      # noqa: E402

mn = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x200
d = MP.read_extracted('1ST_READ.BIN')
i = 0
n = len(d)
while i < n:
    if d[i] == 0:
        j = i
        while j < n and d[j] == 0:
            j += 1
        if j - i >= mn:
            print('%#x..%#x  %#x bytes  (file %#x)' % (MP.IMG_BASE + i, MP.IMG_BASE + j, j - i, i))
        i = j
    else:
        i += 1
