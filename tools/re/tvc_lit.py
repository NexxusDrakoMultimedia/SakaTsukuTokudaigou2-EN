"""tvc_lit.py FILE OFF... : print the little-endian u32 at each hex file offset."""
import sys, struct
d = open(sys.argv[1], 'rb').read()
for a in sys.argv[2:]:
    o = int(a, 16)
    print('%x: %08x' % (o, struct.unpack_from('<I', d, o)[0]))
