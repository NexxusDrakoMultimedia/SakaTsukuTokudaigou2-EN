"""Transcription of the game's decompressors in 1ST_READ.BIN (ZSARC loader).

  -bz--  : FUN_8c15a9f4(dst, src)   byte-oriented LZSS
  -bzw-  : FUN_8c15aae4(dst, src)   16-bit-word-oriented LZSS
  crc16  : FUN_8c15b028(buf, len)   CRC-16/X-25 (init ffff, refl 8408, xorout ffff)

-bz-- : repeat { flag = next byte; 8 times, consuming flag LSB first:
    bit 1 : literal byte
    bit 0 : b = next byte
        b >= 0x80 : len = (b & 7) + 2 ; dist = 16 - ((b >> 3) & 0xF)   (1..16)
        b <  0x80 : b2 = next byte ; b2 == 0 -> END ;
                    len = b2 + 1 ; dist = 128 - b                      (1..128)
        copy len bytes from out[-dist] forward, byte by byte (overlap ok)
-bzw- : everything in 16-bit units.  flag word = big-endian u16 (first file byte
    is the high byte), consumed LSB first (16 bits per flag word).
    bit 1 : literal word (2 bytes copied as-is)
    bit 0 : w = next 2 bytes (lo, hi) ; hi == 0 -> END ;
        count = hi + 1 words ; src = out_pos_bytes - 512 + lo*2  (copy forward, word by word)
"""

def decompress_bz(packed, orig_size=None):
    src = memoryview(packed)
    n = len(src)
    out = bytearray()
    i = 0
    while True:
        flags = src[i]; i += 1
        for _ in range(8):
            if flags & 1:
                out.append(src[i]); i += 1
            else:
                b = src[i]; i += 1
                if b & 0x80:
                    ln = (b & 7) + 2
                    dist = 16 - ((b >> 3) & 0xF)
                else:
                    b2 = src[i]; i += 1
                    if b2 == 0:
                        return bytes(out)
                    ln = b2 + 1
                    dist = 128 - b
                p = len(out) - dist
                for _ in range(ln):
                    out.append(out[p]); p += 1
            flags >>= 1


def decompress_bzw(packed, orig_size=None):
    src = memoryview(packed)
    out = bytearray()
    i = 0
    while True:
        flags = (src[i] << 8) | src[i + 1]; i += 2
        for _ in range(16):
            if flags & 1:
                out += src[i:i + 2]; i += 2
            else:
                lo, hi = src[i], src[i + 1]; i += 2
                if hi == 0:
                    return bytes(out)
                cnt = hi + 1
                p = len(out) - 512 + lo * 2
                for _ in range(cnt):
                    out += out[p:p + 2]; p += 2
            flags >>= 1


_T = []
for _n in range(256):
    _c = _n
    for _ in range(8):
        _c = (_c >> 1) ^ 0x8408 if _c & 1 else _c >> 1
    _T.append(_c)

def crc16(buf):
    c = 0xFFFF
    for b in buf:
        c = (c >> 8) ^ _T[(c ^ b) & 0xFF]
    return c ^ 0xFFFF

def decompress(method, packed, orig_size=None):
    if method == '-nc--':
        return bytes(packed)
    if method == '-bz--':
        return decompress_bz(packed, orig_size)
    if method == '-bzw-':
        return decompress_bzw(packed, orig_size)
    raise ValueError(method)
