"""hsd_sk: read jump-table slots of 1ST_READ.BIN (base 0x8c010000). usage: hsd_sk_slot.py HEXOFF ...  Read-only."""
import sys, struct
d = open('extracted/1ST_READ.BIN', 'rb').read()
for a in sys.argv[1:]:
    off = int(a, 16)
    v = struct.unpack_from('<I', d, 0x8c159000 + off - 0x8c010000)[0]
    print('slot %#x -> %#x' % (off, v))
