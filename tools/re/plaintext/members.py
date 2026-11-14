"""Member-record parser for the LHA-like archives ("-nc--", "-bz--", "-bzw-")
used by SakaTsuku Tokudaigou 2 (Dreamcast).

Record layout (all little endian; offsets relative to the record start `o`):

  +0   u16  hdrlen     total header length INCLUDING this field (44/48/52 seen).
                       Packed data starts at o + hdrlen (NOT hdrlen+2).
  +2   5s   method     b'-nc--' stored, b'-bz--' LZ ("bz"), b'-bzw-' LZ variant
  +7   u32  packed_size  bytes of packed data following the header
  +11  u32  orig_size    bytes after decompression
  +15  u32  mtime        looks like a unix timestamp (2001 for GAME/ files,
                         0x3749xxxx ~1999 for MASCOT/FLOW_PRG); not verified
  +19  u16  crc16        CRC-16/X-25 (poly 0x1021 reflected = 0x8408, init 0xFFFF,
                         xorout 0xFFFF, i.e. CRC-16/IBM-SDLC) of the ORIGINAL
                         (decompressed) data.
  +21  3B    always 00 00 00 (reserved / OS id; unused)
  +24  ...   LHA level-2 style extended headers, each:
                u16 size (incl. these 2 bytes), u8 type, size-3 data bytes
                type 0x01 : file name (sometimes NUL terminated)
                type 0x00 : header CRC: u16 crc (+ 1 pad byte, so size=6)
             list ends with a u16 size 0; header then padded with zeros to hdrlen.
             header CRC = same CRC-16/X-25 computed over the whole `hdrlen`
             header bytes with the 2 crc bytes set to 0.
  +hdrlen  packed data (packed_size bytes)
  then zero padding up to the next 4-byte boundary (and in some bind files such
  as GAME/BINDFLAG.BIN up to the next 2048-byte sector).  A new record is found
  by skipping zero bytes.  End of data = EOF or an invalid header.
"""
import struct

_TAB = None


def crc16(data):
    """CRC-16/X-25 (a.k.a. IBM-SDLC): poly 0x1021 reflected, init/xorout 0xFFFF."""
    global _TAB
    if _TAB is None:
        _TAB = []
        for i in range(256):
            c = i
            for _ in range(8):
                c = (c >> 1) ^ 0x8408 if c & 1 else c >> 1
            _TAB.append(c)
    crc = 0xFFFF
    t = _TAB
    for b in data:
        crc = (crc >> 8) ^ t[(crc ^ b) & 0xFF]
    return crc ^ 0xFFFF


METHODS = (b'-nc--', b'-bz--', b'-bzw-')


def parse_header(data, o):
    """Parse one header at offset o. Returns dict or None if not a valid header."""
    if o + 28 > len(data):
        return None
    hdrlen = struct.unpack_from('<H', data, o)[0]
    method = bytes(data[o + 2:o + 7])
    if hdrlen < 28 or hdrlen > 512 or method not in METHODS or o + hdrlen > len(data):
        return None
    packed, orig, mtime, crc = struct.unpack_from('<IIIH', data, o + 7)
    h = {'offset': o, 'hdrlen': hdrlen, 'method': method.decode('ascii'),
         'packed_size': packed, 'orig_size': orig, 'mtime': mtime, 'crc16': crc,
         'reserved21': bytes(data[o + 21:o + 24]), 'name': None, 'hdr_crc': None,
         'ext': []}
    p = o + 24
    end = o + hdrlen
    while p + 2 <= end:
        sz = struct.unpack_from('<H', data, p)[0]
        if sz == 0:
            break
        if sz < 3 or p + sz > end:
            return None
        typ = data[p + 2]
        body = bytes(data[p + 3:p + sz])
        h['ext'].append((typ, body))
        if typ == 1:
            h['name'] = body.rstrip(b'\0').decode('cp932', 'replace')
        elif typ == 0 and len(body) >= 2:
            h['hdr_crc'] = struct.unpack_from('<H', body, 0)[0]
        p += sz
    h['data_offset'] = end
    h['end_offset'] = end + packed
    return h


def header_crc_ok(data, h):
    """True/False if the header CRC matches, None if there is no CRC ext header."""
    if h['hdr_crc'] is None:
        return None
    o = h['offset']
    hb = bytearray(data[o:o + h['hdrlen']])
    p = 24
    while True:
        sz = struct.unpack_from('<H', hb, p)[0]
        if sz == 0:
            return None
        if hb[p + 2] == 0:
            hb[p + 3] = hb[p + 4] = 0
            break
        p += sz
    return crc16(hb) == h['hdr_crc']


def iter_members(data):
    """Yield (header dict, packed bytes, offset) for each record in `data`."""
    o = 0
    n = len(data)
    while o < n:
        while o < n and data[o] == 0:       # skip zero padding
            o += 1
        if o >= n:
            break
        h = parse_header(data, o)
        if h is None or h['end_offset'] > n:
            break
        yield h, bytes(data[h['data_offset']:h['end_offset']]), o
        o = h['end_offset']


def extract_member(h, packed):
    """Return plaintext of a member (decompresses as required)."""
    m = h['method']
    if m == '-nc--':
        return packed
    from bz_plain import decompress_bz, decompress_bzw
    if m == '-bz--':
        return decompress_bz(packed, h['orig_size'])
    return decompress_bzw(packed, h['orig_size'])


def data_crc_ok(h, plain):
    return crc16(plain) == h['crc16']
