"""bzlib - canonical library for the SakaTsuku Tokudaigou 2 (Dreamcast) member
archives ("ZSARC": LHA-level-2-like records with methods -nc-- / -bz-- / -bzw-).

Pure stdlib.  See docs/formats.md for the format specification.

Public API
----------
crc16(data)                       CRC-16/X-25 (the game's FUN_8c15b028)
decompress(packed, orig_size, method)
decompress_bz(packed, orig_size=None) / decompress_bzw(...)
compress(plain, method)           -> packed bytes (terminator included)
compress_bz(plain) / compress_bzw(plain)
parse_member(data, offset)        -> Member or None
iter_members(data)                -> yields Member (packed data in .packed)
parse_archive(data)               -> (list[Member], tail_offset)
build_header(...)                 -> bytes   (round-trips every header on disc)
pack_member(name, plain, method, ...) -> bytes (complete record, 4-byte padded)
Member.extract()                  -> plain bytes (decoded, verified)

Decoder semantics follow the game's code in 1ST_READ.BIN
(FUN_8c15a9f4 = bz, FUN_8c15aae4 = bzw) exactly, including the end marker
(second token byte == 0), which differs subtly from a "both bytes zero" check.
"""
import struct

METHODS = ('-nc--', '-bz--', '-bzw-')
_METHODS_B = {m.encode('ascii'): m for m in METHODS}

# ---------------------------------------------------------------- CRC16 ----
_TAB = []
for _n in range(256):
    _c = _n
    for _ in range(8):
        _c = (_c >> 1) ^ 0x8408 if _c & 1 else _c >> 1
    _TAB.append(_c)


def crc16(data):
    """CRC-16/X-25 (init 0xFFFF, reflected poly 0x8408, xorout 0xFFFF)."""
    c = 0xFFFF
    t = _TAB
    for b in data:
        c = (c >> 8) ^ t[(c ^ b) & 0xFF]
    return c ^ 0xFFFF


# ----------------------------------------------------------- decompress ----
class DecodeError(ValueError):
    pass


def decompress_bz(packed, orig_size=None):
    """-bz-- : byte LZSS (see docs/formats.md).  Stops at the end token."""
    src = packed
    n = len(src)
    out = bytearray()
    i = 0
    try:
        while True:
            flags = src[i]
            i += 1
            for _ in range(8):
                if flags & 1:
                    out.append(src[i])
                    i += 1
                else:
                    b = src[i]
                    i += 1
                    if b & 0x80:
                        ln = (b & 7) + 2
                        dist = 16 - ((b >> 3) & 15)
                    else:
                        b2 = src[i]
                        i += 1
                        if b2 == 0:
                            if orig_size is not None and len(out) != orig_size:
                                raise DecodeError('bz: end marker at %d, expected %d' % (len(out), orig_size))
                            return bytes(out)
                        ln = b2 + 1
                        dist = 128 - b
                    if dist > len(out):
                        raise DecodeError('bz: distance %d beyond output %d' % (dist, len(out)))
                    if dist >= ln:
                        out += out[-dist:len(out) - dist + ln]
                    else:
                        pat = bytes(out[-dist:])
                        out += (pat * (ln // dist + 1))[:ln]
                flags >>= 1
    except IndexError:
        raise DecodeError('bz: ran off the end of packed data (%d bytes)' % n) from None


def decompress_bzw(packed, orig_size=None):
    """-bzw- : 16-bit-word LZSS with big-endian 16-bit flag words."""
    src = packed
    n = len(src)
    out = bytearray()
    i = 0
    try:
        while True:
            flags = (src[i] << 8) | src[i + 1]
            i += 2
            for _ in range(16):
                if flags & 1:
                    out += src[i:i + 2]
                    if i + 2 > n:
                        raise IndexError
                    i += 2
                else:
                    lo = src[i]
                    hi = src[i + 1]
                    i += 2
                    if hi == 0:
                        if orig_size is not None and len(out) != orig_size:
                            raise DecodeError('bzw: end marker at %d, expected %d' % (len(out), orig_size))
                        return bytes(out)
                    cnt = (hi + 1) * 2
                    dist = 512 - lo * 2
                    if dist > len(out):
                        raise DecodeError('bzw: distance %d beyond output %d' % (dist, len(out)))
                    if dist >= cnt:
                        out += out[-dist:len(out) - dist + cnt]
                    else:
                        pat = bytes(out[-dist:])
                        out += (pat * (cnt // dist + 1))[:cnt]
                flags >>= 1
    except IndexError:
        raise DecodeError('bzw: ran off the end of packed data (%d bytes)' % n) from None


def decompress(packed, orig_size, method):
    """Decode `packed` with `method` ('-nc--', '-bz--', '-bzw-').
    `orig_size` may be None (no length check)."""
    if method == '-nc--':
        out = bytes(packed)
        if orig_size is not None and len(out) != orig_size:
            raise DecodeError('nc: length %d, expected %d' % (len(out), orig_size))
        return out
    if method == '-bz--':
        return decompress_bz(packed, orig_size)
    if method == '-bzw-':
        return decompress_bzw(packed, orig_size)
    raise ValueError('unknown method %r' % (method,))


# ------------------------------------------------------------- compress ----
class _FlagWriter:
    """Collects items into groups of `nbits` flag bits (LSB first)."""

    def __init__(self, nbits, big_endian_word):
        self.nbits = nbits
        self.be = big_endian_word
        self.out = bytearray()
        self.flags = 0
        self.nf = 0
        self.buf = bytearray()

    def put(self, is_literal, data):
        if is_literal:
            self.flags |= 1 << self.nf
        self.buf += data
        self.nf += 1
        if self.nf == self.nbits:
            self.flush()

    def flush(self):
        if self.nf == 0:
            return
        if self.nbits == 8:
            self.out.append(self.flags)
        else:
            self.out += struct.pack('>H', self.flags)
        self.out += self.buf
        self.flags = 0
        self.nf = 0
        self.buf = bytearray()


def compress_bz(plain):
    """Greedy LZ encoder for -bz--.  Matches only reference already-emitted
    output, never beyond 128 bytes back, so the game's decoder (which has no
    ring buffer, it reads its own output buffer) accepts it for any size."""
    plain = bytes(plain)
    n = len(plain)
    w = _FlagWriter(8, False)
    heads = {}          # 3-byte key -> list of recent positions (ascending)
    i = 0

    def add(p):
        if p + 3 <= n:
            k = plain[p:p + 3]
            l = heads.get(k)
            if l is None:
                heads[k] = [p]
            else:
                l.append(p)
                if len(l) > 24:
                    del l[0]

    while i < n:
        best_len = 0
        best_dist = 0
        if i + 3 <= n:
            cands = heads.get(plain[i:i + 3])
            if cands:
                maxl = min(256, n - i)
                for p in reversed(cands):
                    d = i - p
                    if d > 128:
                        break
                    # overlap-safe compare
                    l = 3
                    while l < maxl and plain[p + l] == plain[i + l]:
                        l += 1
                    if l > best_len:
                        best_len, best_dist = l, d
                        if l == maxl:
                            break
        # also try 2-byte matches reachable by 1-byte token (dist<=16)
        if best_len < 2 and i + 2 <= n:
            for d in range(1, min(16, i) + 1):
                if plain[i - d] == plain[i] and plain[i - d + 1] == plain[i + 1]:
                    best_len, best_dist = 2, d
                    break
        if best_len >= 2 and best_dist <= 16 and best_len <= 9:
            w.put(False, bytes([0x80 | ((16 - best_dist) << 3) | (best_len - 2)]))
        elif best_len >= 3:
            w.put(False, bytes([128 - best_dist, best_len - 1]))
        else:
            best_len = 1
            w.put(True, plain[i:i + 1])
        for k in range(best_len):
            add(i + k)
        i += best_len
    w.put(False, b'\x00\x00')       # end token (b2 == 0)
    w.flush()
    return bytes(w.out)


def compress_bzw(plain):
    """Greedy LZ encoder for -bzw- (16-bit words; plain length must be even)."""
    plain = bytes(plain)
    if len(plain) % 2:
        raise ValueError('-bzw- data must have an even length (got %d)' % len(plain))
    words = [plain[k:k + 2] for k in range(0, len(plain), 2)]
    n = len(words)
    w = _FlagWriter(16, True)
    heads = {}
    i = 0

    def add(p):
        if p + 2 <= n:
            k = (words[p], words[p + 1])
            l = heads.get(k)
            if l is None:
                heads[k] = [p]
            else:
                l.append(p)
                if len(l) > 24:
                    del l[0]

    while i < n:
        best_len = 0
        best_dist = 0
        if i + 2 <= n:
            cands = heads.get((words[i], words[i + 1]))
            if cands:
                maxl = min(256, n - i)
                for p in reversed(cands):
                    d = i - p
                    if d > 256:
                        break
                    l = 2
                    while l < maxl and words[p + l] == words[i + l]:
                        l += 1
                    if l > best_len:
                        best_len, best_dist = l, d
                        if l == maxl:
                            break
        if best_len >= 2:
            w.put(False, bytes([256 - best_dist, best_len - 1]))
        else:
            best_len = 1
            w.put(True, words[i])
        for k in range(best_len):
            add(i + k)
        i += best_len
    w.put(False, b'\x00\x00')
    w.flush()
    return bytes(w.out)


def compress(plain, method):
    """Encode `plain` with `method`; result is accepted by the game's decoder
    and round-trips through decompress().  Ratio caveat: greedy, no lazy
    matching or optimal parsing, so packed sizes are typically a few to ~10 %
    larger than the original tool's.  Size never matters to the loader beyond
    the header's packed_size field."""
    if method == '-nc--':
        return bytes(plain)
    if method == '-bz--':
        return compress_bz(plain)
    if method == '-bzw-':
        return compress_bzw(plain)
    raise ValueError('unknown method %r' % (method,))


# -------------------------------------------------------- member header ----
def _align4(x):
    return (x + 3) & ~3


class Member:
    """One parsed record.  Attributes: offset, hdrlen, method, packed_size,
    orig_size, mtime, crc16, reserved (3 bytes at +21), ext (list of
    (type, body) in file order), name, name_raw, hdr_crc, header (raw bytes),
    data_offset, end_offset, packed (bytes), hdr_crc_ok."""

    def __repr__(self):
        return '<Member %r %s %d->%d @%#x>' % (self.name, self.method, self.packed_size, self.orig_size, self.offset)

    def extract(self, verify=True):
        plain = decompress(self.packed, self.orig_size, self.method)
        if verify and crc16(plain) != self.crc16:
            raise DecodeError('crc16 mismatch for %r: %04x != %04x' % (self.name, crc16(plain), self.crc16))
        return plain


def header_crc(hdr):
    """CRC16 over a header with its type-0 extension's 2 CRC bytes zeroed.
    Returns None if the header has no type-0 extension."""
    hb = bytearray(hdr)
    p = 24
    while p + 2 <= len(hb):
        sz = struct.unpack_from('<H', hb, p)[0]
        if sz == 0:
            return None
        if hb[p + 2] == 0:
            hb[p + 3] = hb[p + 4] = 0
            return crc16(hb)
        p += sz
    return None


def parse_member(data, o=0, with_data=True):
    """Parse the record at offset `o`; return a Member, or None if there is no
    valid, in-bounds record there."""
    n = len(data)
    if o + 28 > n:
        return None
    hdrlen = struct.unpack_from('<H', data, o)[0]
    m = _METHODS_B.get(bytes(data[o + 2:o + 7]))
    if hdrlen < 28 or hdrlen > 512 or m is None or o + hdrlen > n or hdrlen % 2:
        return None
    packed, orig, mtime, crc = struct.unpack_from('<IIIH', data, o + 7)
    mem = Member()
    mem.offset = o
    mem.hdrlen = hdrlen
    mem.method = m
    mem.packed_size = packed
    mem.orig_size = orig
    mem.mtime = mtime
    mem.crc16 = crc
    mem.reserved = bytes(data[o + 21:o + 24])
    mem.ext = []
    mem.name = None
    mem.name_raw = None
    mem.hdr_crc = None
    p = o + 24
    end = o + hdrlen
    terminated = False
    while p + 2 <= end:
        sz = struct.unpack_from('<H', data, p)[0]
        if sz == 0:
            terminated = True
            break
        if sz < 3 or p + sz > end:
            return None
        t = data[p + 2]
        body = bytes(data[p + 3:p + sz])
        mem.ext.append((t, body))
        if t == 1 and mem.name_raw is None:
            mem.name_raw = body
            mem.name = body.rstrip(b'\0').decode('cp932', 'replace')
        elif t == 0 and len(body) >= 2:
            mem.hdr_crc = struct.unpack_from('<H', body, 0)[0]
        p += sz
    if not terminated:
        return None
    mem.header = bytes(data[o:end])
    mem.data_offset = end
    mem.end_offset = end + packed
    if mem.end_offset > n:
        return None
    mem.hdr_crc_ok = None if mem.hdr_crc is None else (header_crc(mem.header) == mem.hdr_crc)
    mem.packed = bytes(data[end:mem.end_offset]) if with_data else None
    return mem


def parse_archive(data):
    """Parse back-to-back records, skipping zero padding between them.
    Returns (members, tail_offset): tail_offset is where parsing stopped
    (== len(data) when everything was consumed, ignoring trailing zeros)."""
    members = []
    o = 0
    n = len(data)
    while True:
        while o < n and data[o] == 0:
            o += 1
        if o >= n:
            return members, n
        m = parse_member(data, o)
        if m is None:
            return members, o
        members.append(m)
        o = m.end_offset


def iter_members(data):
    """Yield Member objects (see parse_archive)."""
    for m in parse_archive(data)[0]:
        yield m


def build_header(name_raw, method, packed_size, orig_size, mtime, crc, hdrlen=None,
                 ext=None, reserved=b'\0\0\0'):
    """Serialise a member header (including the header CRC).

    name_raw : bytes stored in the type-1 extension (e.g. b'tex.pvr', cp932).
    ext      : optional full extension list [(type, body), ...]; when given,
               it is used verbatim (the type-0 body's first 2 bytes are
               overwritten with the freshly computed header CRC).  When None a
               default [(1, name_raw), (0, crc_placeholder + 1 pad byte)] is
               used, which is the layout seen on the disc.
    hdrlen   : forced header length (must be >= the natural length)."""
    if isinstance(method, str):
        method = method.encode('ascii')
    if ext is None:
        ext = [(1, bytes(name_raw)), (0, b'\0\0\0')]
    ext = [(t, bytearray(b)) for t, b in ext]
    chain = b''.join(struct.pack('<HB', len(b) + 3, t) + bytes(b) for t, b in ext) + b'\0\0'
    natural = _align4(24 + len(chain))
    if hdrlen is None:
        hdrlen = natural
    if hdrlen < natural:
        raise ValueError('hdrlen %d too small (need %d)' % (hdrlen, natural))
    hdr = bytearray(struct.pack('<H5sIIIH3s', hdrlen, method, packed_size, orig_size, mtime, crc, reserved))
    hdr += chain
    hdr += b'\0' * (hdrlen - len(hdr))
    # fill header CRC
    p = 24
    while p + 2 <= len(hdr):
        sz = struct.unpack_from('<H', hdr, p)[0]
        if sz == 0:
            break
        if hdr[p + 2] == 0:
            hdr[p + 3] = hdr[p + 4] = 0
            struct.pack_into('<H', hdr, p + 3, crc16(hdr))
            break
        p += sz
    return bytes(hdr)


def pack_member(name, plain, method, mtime=0, hdrlen=None, ext=None, pad4=True):
    """Build a complete record (header + packed data [+ zero pad to 4]).
    `name` may be str (encoded cp932) or bytes."""
    if isinstance(name, str):
        name = name.encode('cp932')
    packed = compress(plain, method)
    rec = build_header(name, method, len(packed), len(plain), mtime, crc16(plain), hdrlen, ext) + packed
    if pad4:
        rec += b'\0' * (_align4(len(rec)) - len(rec))
    return rec


def member_record(m, plain=None, method=None):
    """Re-encode member `m` (optionally with new plaintext / method) keeping its
    name, mtime, extension layout and header length (grown only if needed)."""
    if plain is None:
        plain = m.extract()
    method = method or m.method
    packed = compress(plain, method)
    hdr = build_header(m.name_raw, method, len(packed), len(plain), m.mtime, crc16(plain),
                       hdrlen=None, ext=m.ext, reserved=m.reserved)
    if len(hdr) < m.hdrlen:
        hdr = build_header(m.name_raw, method, len(packed), len(plain), m.mtime, crc16(plain),
                           hdrlen=m.hdrlen, ext=m.ext, reserved=m.reserved)
    rec = hdr + packed
    return rec + b'\0' * (_align4(len(rec)) - len(rec))
