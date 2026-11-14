"""tvc_w.py FILE OFF COUNT : print COUNT little-endian u16 (hex and signed) from hex file offset."""
import sys, struct
d = open(sys.argv[1], 'rb').read()
o = int(sys.argv[2], 16)
for i in range(int(sys.argv[3])):
    v = struct.unpack_from('<H', d, o + 2 * i)[0]
    print('%x: %04x %d' % (o + 2 * i, v, v if v < 32768 else v - 65536))
