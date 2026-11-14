"""ovmem: find 32-bit words in 1ST_READ.BIN that equal given addresses (read-only). usage: ovmem_refs.py HEX [HEX...]"""
import struct, sys
D = open('extracted/1ST_READ.BIN', 'rb').read()
B = 0x8C010000
for h in sys.argv[1:]:
    t = int(h, 16)
    print(h, [hex(B + i) for i in range(0, len(D) - 3, 2) if struct.unpack_from('<I', D, i)[0] == t])
