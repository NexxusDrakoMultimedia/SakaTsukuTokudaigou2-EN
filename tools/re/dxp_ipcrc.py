"""Read-only: which byte range of IP.BIN does the 4-hex-digit CRC at 0x0E cover?  usage: dxp_ipcrc.py"""
import binascii
d = open('extracted/IP.BIN', 'rb').read()
print(d[0x20:0x24], d[0x40:0x50])
target = int(d[0x20:0x24], 16)
def crc16(data, poly=0x1021, init=0xFFFF, refl=False, xor=0):
    c = init
    for b in data:
        if refl:
            c ^= b
            for _ in range(8): c = (c >> 1) ^ (0x8408 if c & 1 else 0)
        else:
            c ^= b << 8
            for _ in range(8): c = ((c << 1) ^ poly) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c ^ xor
hits = []
for init in (0, 0xFFFF):
    for refl in (False, True):
        for xor in (0, 0xFFFF):
            for a in range(0x10, 0x60, 1):
                for b in range(a + 1, 0x110):
                    if crc16(d[a:b], 0x1021, init, refl, xor) == target:
                        hits.append((hex(a), hex(b), init, refl, xor))
print(hits[:10], len(hits))
