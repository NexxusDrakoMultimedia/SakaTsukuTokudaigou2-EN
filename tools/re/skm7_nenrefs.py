"""skm7_nenrefs.py: pool words of extracted FLOW_PRG/NENREP.BIN that point into the money format block (any of several bases), and the code that loads them.  Read only."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP      # noqa: E402

d = MP.read_extracted('FLOW_PRG/NENREP.BIN')
BASE = 0x8c2e0000
for i in range(0, len(d) - 4, 4):
    v = struct.unpack_from('<I', d, i)[0]
    if BASE + 0x24ee0 <= v < BASE + 0x24f60:
        # code words that load this pool word
        loads = []
        for o in range(max(0, i - 1020), i, 2):
            w = d[o] | d[o + 1] << 8
            if (w >> 12) == 0xD and ((o + 4) & ~3) + (w & 0xFF) * 4 == i:
                loads.append('%05x r%d' % (o, (w >> 8) & 15))
        print('pool %05x -> +%#x  loaded at %s' % (i, v - BASE, loads))
