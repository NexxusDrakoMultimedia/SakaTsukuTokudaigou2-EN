"""ovmem: list words in 1ST_READ.BIN pointing into a range (read-only). usage: ovmem_refs2.py LO HI"""
import struct, sys
D = open('extracted/1ST_READ.BIN', 'rb').read()
B = 0x8C010000
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
for i in range(0, len(D) - 3, 2):
    w = struct.unpack_from('<I', D, i)[0]
    if lo <= w < hi:
        print(hex(B + i), hex(w))
