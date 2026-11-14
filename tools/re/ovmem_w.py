"""ovmem: print 32-bit words of 1ST_READ.BIN at given VAs (read-only). usage: ovmem_w.py HEX [HEX...]"""
import struct, sys
D = open('extracted/1ST_READ.BIN', 'rb').read()
B = 0x8C010000
for h in sys.argv[1:]:
    a = int(h, 16)
    print(h, hex(struct.unpack_from('<I', D, a - B)[0]))
