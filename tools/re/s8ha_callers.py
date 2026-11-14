"""s8ha: find callers of a function address in an overlay: literal words equal to ADDR, and bsr / bra targets.
usage: s8ha_callers.py FILE BASE ADDR"""
import struct, sys
d = open(sys.argv[1], 'rb').read()
base = int(sys.argv[2], 16)
t = int(sys.argv[3], 16)
for i in range(0, len(d) - 3, 4):
    if struct.unpack_from('<I', d, i)[0] == t:
        lit = base + i
        # loads of this literal
        for k in range(max(0, i - 1100), i, 2):
            w = struct.unpack_from('<H', d, k)[0]
            if w >> 12 == 0xD and ((((base + k) + 4) & ~3) + (w & 0xFF) * 4) == lit:
                print('literal %08x loaded at %08x into r%d' % (lit, base + k, (w >> 8) & 15))
for k in range(0, len(d) - 1, 2):
    w = struct.unpack_from('<H', d, k)[0]
    if w >> 12 in (0xA, 0xB):
        disp = w & 0xFFF
        if disp & 0x800:
            disp -= 0x1000
        if base + k + 4 + 2 * disp == t:
            print('%s at %08x' % ('bra' if w >> 12 == 0xA else 'bsr', base + k))
