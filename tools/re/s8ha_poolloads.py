"""s8ha: every pc-relative long load (mov.l @(d,pc),rn) that reads the given pool words of an overlay.
usage: s8ha_poolloads.py FILE BASE WORD_ADDR..."""
import struct, sys
d = open(sys.argv[1], 'rb').read()
base = int(sys.argv[2], 16)
targets = set(int(x, 16) for x in sys.argv[3:])
n = len(d) // 2
for i in range(n):
    w = struct.unpack_from('<H', d, 2 * i)[0]
    if w >> 12 == 0xD:
        pc = base + 2 * i
        t = ((pc + 4) & ~3) + (w & 0xFF) * 4
        if t in targets:
            print('%08x: mov.l @(%#x),r%d' % (pc, t, (w >> 8) & 15))
