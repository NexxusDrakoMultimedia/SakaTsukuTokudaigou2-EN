"""ovmem: read-only scan of 1ST_READ.BIN for the overlay load table (file names + descriptors).
usage: python -I -X utf8 tools/re/ovmem_scan.py"""
import re
import struct
import sys

D = open('extracted/1ST_READ.BIN', 'rb').read()
BASE = 0x8C010000
print('size', len(D), hex(BASE + len(D)))


def u32(a):
    return struct.unpack_from('<I', D, a - BASE)[0]


for name in (b'CLUBEDIT.BIN', b'GAME.BIN', b'MEETING.BIN', b'FLOW_PRG'):
    for m in re.finditer(re.escape(name) + rb'\x00', D):
        va = BASE + m.start()
        print('string', name, hex(va))
        for i in range(0, len(D) - 3, 4):
            if struct.unpack_from('<I', D, i)[0] == va:
                print('   ptr word at', hex(BASE + i))
