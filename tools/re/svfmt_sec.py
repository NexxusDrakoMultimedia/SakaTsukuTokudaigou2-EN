"""svfmt_sec.py DUMP : does the upper half of each gsp section-table size word equal a CRC/sum of the section bytes?"""
import sys, struct
d = open(sys.argv[1], 'rb').read(); B = 0x8c000000
w = lambda a: struct.unpack_from('<I', d, a - B)[0]
def crc_poly(data, init, poly, refin, refout, xorout):
    c = init
    for b in data:
        if refin:
            c ^= b
            for _ in range(8): c = (c >> 1) ^ (0x8408 if c & 1 else 0) if poly == 0x1021 else (c >> 1) ^ (poly if c & 1 else 0)
        else:
            c ^= b << 8
            for _ in range(8): c = ((c << 1) ^ poly) & 0xffff if c & 0x8000 else (c << 1) & 0xffff
    return (c ^ xorout) & 0xffff
VAR = {'ccitt-false': (0xffff, 0x1021, 0, 0, 0), 'xmodem': (0, 0x1021, 0, 0, 0), 'x25': (0xffff, 0x1021, 1, 1, 0xffff),
       'kermit': (0, 0x1021, 1, 1, 0), 'zero-init-refl': (0, 0x1021, 1, 1, 0), 'arc': (0, 0xA001, 1, 1, 0)}
gsp = w(0x8c159220)
for o in range(0x24, 0xa0, 8):
    p = w(gsp + o); sz = w(gsp + o + 4)
    if not (0x8ce4c000 <= p < 0x8ce5c000): continue
    n = sz & 0xffff; hi = sz >> 16
    data = d[p - B:p - B + n]
    hits = [k for k, v in VAR.items() if crc_poly(data, *v) == hi]
    s16 = sum(data) & 0xffff; sw = sum(struct.unpack('<%dH' % (n // 2), data[:n // 2 * 2])) & 0xffff
    x = 0
    for i in range(0, n - 1, 2): x ^= struct.unpack_from('<H', data, i)[0]
    print('gsp+%03x sec %08x size %04x hi %04x crc-hits %s sum8 %04x sum16 %04x xor16 %04x' % (o, p, n, hi, hits, s16, sw, x))
