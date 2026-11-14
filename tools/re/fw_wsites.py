"""fw_wsites.py FILE BASE_HEX VALUE [VALUE..]: addresses of the `mov.w @(disp,PC),Rn` instructions in FILE whose literal equals VALUE
(and the destination register), read-only helper of the field-width study."""
import sys

f, base = sys.argv[1], int(sys.argv[2], 16)
vals = [int(v, 0) for v in sys.argv[3:]]
d = open(f, 'rb').read()
for a in range(0, len(d) - 1, 2):
    x = d[a] | d[a + 1] << 8
    if x >> 12 == 0x9:
        t = a + 4 + 2 * (x & 0xFF)
        if t + 1 < len(d):
            lv = d[t] | d[t + 1] << 8
            if lv in vals:
                print('%#x: mov.w @(%#x),r%d  = %#x' % (base + a, base + t, (x >> 8) & 15, lv))
