"""s7t: list SH-4 `cmp/eq #imm,r0` (0x88ii) sites with a given imm in an overlay. usage: file imm"""
import struct, sys
d = open(sys.argv[1], 'rb').read(); imm = int(sys.argv[2], 0) & 0xff
for o in range(0, len(d) - 1, 2):
    if d[o] == imm and d[o + 1] == 0x88:
        print('0x%x' % o)
