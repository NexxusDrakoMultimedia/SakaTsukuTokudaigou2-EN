"""s7t: list `mov #imm,rN` (0xEnii) sites with a given imm in an overlay. usage: file imm [regex-less]"""
import sys
d = open(sys.argv[1], 'rb').read(); imm = int(sys.argv[2], 0) & 0xff
r = []
for o in range(0, len(d) - 1, 2):
    if d[o] == imm and d[o + 1] >> 4 == 0xE:
        r.append(o)
print(len(r), ' '.join('0x%x' % x for x in r))
