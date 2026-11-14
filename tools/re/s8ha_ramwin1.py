"""s8ha: print one window of a RAM dump: the code array as text and its geometry.  usage: s8ha_ramwin1.py DUMP ADDR"""
import struct, sys
dump = open(sys.argv[1], 'rb').read()
B = 0x8c000000
a = int(sys.argv[2], 16)
ptr, n, idx = struct.unpack_from('<I', dump, a + 0x30 - B)[0], struct.unpack_from('<H', dump, a + 0x22 - B)[0], struct.unpack_from('<H', dump, a + 0x2c - B)[0]
codes = struct.unpack_from('<%dH' % n, dump, ptr - B)
s = ''
for c in codes:
    if c == 0x2020: s += ' '
    elif c == 0x200a: s += '\n'
    elif c & 0x8000: s += chr(c & 0x7f) if 0x20 <= (c & 0xff) < 0x7f else '<%04x>' % c
    else: s += '<%04x>' % c
print('win %08x ptr %08x n %d idx %d W %d R %d adv %d x0 %d y0 %d' % (a, ptr, n, idx, dump[a + 0x3c - B], dump[a + 0x3d - B], dump[a + 0x3e - B], struct.unpack_from('<h', dump, a + 0x4a - B)[0], struct.unpack_from('<h', dump, a + 0x4c - B)[0]))
print(repr(s))
