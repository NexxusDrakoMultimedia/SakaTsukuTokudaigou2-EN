"""Decompressors for the '-bz--' / '-bzw-' member methods."""


def decompress_bz(packed, orig_size=None):
    """'-bz--' : flag-byte LZ.
    - flag byte, consumed LSB first; bit=1 -> literal byte, bit=0 -> match token
    - match token, first byte b1:
        b1 & 0x80 : 1-byte token  1 dddd lll : dist = 16 - dddd (1..16), len = lll + 2 (2..9)
        else      : 2-byte token  b1, b2     : dist = 128 - b1, len = b2 + 1
                    b1 == 0 and b2 == 0 -> end of stream
    Copies are byte-wise from already-written output (overlap allowed)."""
    out = bytearray()
    i = 0
    while True:
        fl = packed[i]
        i += 1
        for b in range(8):
            if fl >> b & 1:
                out.append(packed[i])
                i += 1
            else:
                b1 = packed[i]
                if b1 & 0x80:
                    i += 1
                    dist = 16 - ((b1 >> 3) & 15)
                    ln = (b1 & 7) + 2
                else:
                    b2 = packed[i + 1]
                    i += 2
                    if b1 == 0 and b2 == 0:
                        if orig_size is not None and len(out) != orig_size:
                            raise ValueError('bz: end marker at %d, expected %d' % (len(out), orig_size))
                        return bytes(out)
                    dist = 128 - b1
                    ln = b2 + 1
                if dist > len(out):
                    raise ValueError('bz: distance %d beyond output %d' % (dist, len(out)))
                for _ in range(ln):
                    out.append(out[-dist])


def decompress_bzw(packed, orig_size=None):
    """'-bzw-' : the 16-bit "word" version of the same scheme.
    All units are 2 bytes wide:
    - flag word: u16 BIG endian ((b0 << 8) | b1), consumed LSB first; 1 = literal, 0 = match
    - literal: one 2-byte word copied verbatim
    - match token (2 bytes, b1 b2): dist = 256 - b1 WORDS, len = b2 + 1 WORDS;
      b1 == 0 and b2 == 0 -> end of stream
    Output size is therefore always even; the copy is word-wise (overlap allowed)."""
    out = bytearray()
    i = 0
    while True:
        fl = (packed[i] << 8) | packed[i + 1]
        i += 2
        for b in range(16):
            if fl >> b & 1:
                out += packed[i:i + 2]
                i += 2
            else:
                b1 = packed[i]
                b2 = packed[i + 1]
                i += 2
                if b1 == 0 and b2 == 0:
                    if orig_size is not None and len(out) != orig_size:
                        raise ValueError('bzw: end marker at %d, expected %d' % (len(out), orig_size))
                    return bytes(out)
                dist = (256 - b1) * 2
                ln = (b2 + 1) * 2
                if dist > len(out):
                    raise ValueError('bzw: distance %d beyond output %d' % (dist, len(out)))
                for _ in range(ln):
                    out.append(out[-dist])
