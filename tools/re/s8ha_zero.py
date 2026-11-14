"""s8ha: map the non-zero ranges of extracted/1ST_READ.BIN in [LO, HI) (hex file offsets).  usage: s8ha_zero.py LO HI"""
import sys
d = open('extracted/1ST_READ.BIN', 'rb').read()
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
i = lo
while i < hi:
    if d[i]:
        j = i
        while j < hi and (d[j] or any(d[j:j + 64])):
            j += 1
        print('%#x..%#x (%08x..%08x) non-zero' % (i, j, 0x8c010000 + i, 0x8c010000 + j))
        i = j
    else:
        i += 1
