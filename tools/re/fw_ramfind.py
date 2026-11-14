"""fw_ramfind.py DUMP TEXT [MAX]: addresses (0x8c000000 based) of ASCII/cp932-latin TEXT in a RAM dump, with 24 bytes of context (read-only)."""
import sys
d = open(sys.argv[1], 'rb').read()
t = sys.argv[2].encode('cp932')
mx = int(sys.argv[3]) if len(sys.argv) > 3 else 40
p = d.find(t)
n = 0
while p != -1 and n < mx:
    c = d[max(0, p - 8):p + 24]
    print('%08x  %s' % (0x8c000000 + p, ' '.join('%02x' % b for b in c)), ''.join(chr(b) if 32 <= b < 127 else '.' for b in c))
    p = d.find(t, p + 1)
    n += 1
