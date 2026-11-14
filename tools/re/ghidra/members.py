"""ZSARC member parser (FUN_8c15a1cc header parse, FUN_8c15a45a extract loop).

Member header (all little-endian), total length = hdrlen (the u16 at +0):
  +0  u16 hdrlen   (44/48 seen; = 2 + ... rounded up to multiple of 4)
  +2  char[5] method: '-nc--' stored, '-bz--' byte LZSS, '-bzw-' word LZSS
  +7  u32 packed_size
  +11 u32 orig_size
  +15 u32 time stamp (unix time; unused by the loader)
  +19 u16 crc16 of the DECOMPRESSED data (CRC-16/X-25), checked by loader
  +21 u8  (os/attr, 0)   +22 u16 (0) ...
  +24 extension chain, each: u16 size (incl. itself), u8 type, payload
        type 0x01 = filename (size-3 bytes)
        type 0x00 = header CRC16 (loader checks crc of the header with this field zeroed;
                    ZSARC handler type 0)
      chain ends with u16 0; if the end offset is not 4-aligned it is rounded up by 2.
  +hdrlen  packed data (packed_size bytes), then padding to the next multiple of 4
Archive ends at a u16 hdrlen == 0 (loader stops).  Files like GAME/BINDFLAG.BIN
contain several such archives, each padded to a 2048-byte sector, so iter_members
skips zero padding to the next 4 byte (and, if all zero, resyncs on 2048).
"""
import struct

def parse_header(d, o):
    hl = struct.unpack_from('<H', d, o)[0]
    meth = bytes(d[o + 2:o + 7]).decode('latin1')
    packed, orig, ts, crc = struct.unpack_from('<IIIH', d, o + 7)
    name = None; hcrc = None
    p = o + 24
    while True:
        sz = struct.unpack_from('<H', d, p)[0]
        if sz == 0:
            break
        t = d[p + 2]
        if t == 1:
            name = bytes(d[p + 3:p + sz]).decode('sjis', 'replace')
        elif t == 0:
            hcrc = struct.unpack_from('<H', d, p + 3)[0]
        p += sz
    return dict(hdrlen=hl, method=meth, packed=packed, orig=orig, time=ts,
                crc16=crc, name=name, hdr_crc16=hcrc)

def iter_members(data):
    """yield (header dict, packed bytes, offset_of_header)"""
    o = 0
    n = len(data)
    while o + 2 < n:
        hl = struct.unpack_from('<H', data, o)[0]
        if hl == 0:
            # skip zero padding (end of one archive; next starts at sector boundary)
            while o < n and data[o] == 0:
                o += 1
            continue
        if hl > 0x200 or data[o + 2] != 0x2d:
            return
        h = parse_header(data, o)
        s = o + hl
        yield h, bytes(data[s:s + h['packed']]), o
        o = s + h['packed']
        o = (o + 3) & ~3
