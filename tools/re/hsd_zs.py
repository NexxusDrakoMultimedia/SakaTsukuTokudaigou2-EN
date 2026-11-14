"""hsd: walk ZSARC members at a given offset of a file with the game's checks (texinject.game_walk_zsarc re-implementation).
usage: hsd_zs.py FILE OFFSET(hex) [COUNT]. Prints header fields, stored CRC16 vs CRC16 of the data.  Read-only."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bzlib

d = open(sys.argv[1], 'rb').read()
o = int(sys.argv[2], 16)
cnt = int(sys.argv[3]) if len(sys.argv) > 3 else 4
for _ in range(cnt):
    hl = struct.unpack_from('<H', d, o)[0]
    if hl == 0:
        print('%x: terminator' % o); break
    meth = bytes(d[o+2:o+7])
    packed, orig, mtime, crc = struct.unpack_from('<IIIH', d, o + 7)
    data = bytes(d[o+hl:o+hl+packed])
    try:
        plain = bzlib.decompress(data, None, meth.decode())
        c = bzlib.crc16(plain)
    except Exception as e:
        plain = None; c = repr(e)
    print('%x: hl=%d meth=%s packed=%#x orig=%#x stored_crc=%04x data_crc=%s  name=%r' % (o, hl, meth, packed, orig, crc, c if isinstance(c, str) else '%04x' % c, d[o+24:o+hl][:24]))
    o += hl + packed + ((4 - (packed & 3)) if packed & 3 else 0)
