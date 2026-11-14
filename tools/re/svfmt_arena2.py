"""svfmt_arena2.py DUMP : for each save-arena section, treat as array of 288-byte structs and list structs whose first 14 bytes hold a name-like string."""
import sys, struct
d = open(sys.argv[1], 'rb').read(); B = 0x8c000000
w = lambda a: struct.unpack_from('<I', d, a - B)[0]
gsp = w(0x8c159220)
for o in range(0x24, 0xa0, 8):
    p = w(gsp + o); sz = w(gsp + o + 4) & 0xffff
    if not (0x8ce4c000 <= p < 0x8ce5c000): continue
    names = []
    for i in range(0, sz - 13, 0x120):
        r = d[p - B + i:p - B + i + 14].split(b'\0')[0]
        if r and all(32 <= c < 127 or 0xa1 <= c <= 0xdf for c in r) and len(r) >= 3: names.append((i // 0x120, r.decode('cp932')))
    print('gsp+%03x arena+%05x size %04x (/288=%.2f) named structs %d %s' % (o, p - 0x8ce4c000, sz, sz / 288, len(names), names[:4]))
