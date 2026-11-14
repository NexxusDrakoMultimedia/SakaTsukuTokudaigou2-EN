"""PVR / TBD texture decoding (Dreamcast PowerVR) + PNG writer, pure python.

TBD / DAT / (some ZAR) texture bundle  (INFERRED from data, verified by decoding):
  u32 count
  count * 16-byte record:  u8 pixfmt, u8 datatype, u8 0, u8 flags(0x00 raw, 0x40 -bzw- word LZ, 0x80 -bz-- byte LZ)  [FUN_8c15a776: bit30 -> FUN_8c15aae4, bit31 -> FUN_8c15a9f4],
                           u16 w, u16 h, u32 data offset, u32 stamp
  data of record i = bytes [off_i, off_{i+1}) (last: to EOF), compressed per flags with the
  tools/bzlib.py bz / bzw codecs (the record has no size field -> decode without orig_size).
PVR file (GBIX + PVRT): GBIX u32 8 u32 index u32 0 | PVRT u32 len, u8 pixfmt, u8 datatype, u16 0, u16 w, u16 h.
pixfmt: 0 ARGB1555, 1 RGB565, 2 ARGB4444, 3 YUV422, 4 BUMP, 5 RGB555?, 6 ARGB8888?
datatype (PuyoTools numbering): 1 square twiddled, 2 +mip, 3 VQ, 4 VQ+mip, 5/6 4bpp pal (+mip),
  7/8 8bpp pal (+mip), 9 rectangle, 0xD rect twiddled, 0x10/0x11 small VQ.
"""
import struct
import sys
import os
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import bzlib


def _twid(n):
    """twiddle index table for an n x n image (n power of two): idx[y*n+x] -> position"""
    bits = n.bit_length() - 1
    t = [0] * (n * n)
    for y in range(n):
        for x in range(n):
            v = 0
            for i in range(bits):
                v |= ((x >> i) & 1) << (2 * i + 1)     # x bits at odd positions (verified on text textures)
                v |= ((y >> i) & 1) << (2 * i)
            t[y * n + x] = v
    return t


_TW = {}


def twid(n):
    if n not in _TW:
        _TW[n] = _twid(n)
    return _TW[n]


def px(fmt, v):
    """16-bit pixel -> (r,g,b,a)"""
    if fmt == 0:     # ARGB1555
        return ((v >> 10 & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v & 31) * 255 // 31, 255 if v & 0x8000 else 0)
    if fmt == 1:     # RGB565
        return ((v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31, 255)
    if fmt == 2:     # ARGB4444
        return ((v >> 8 & 15) * 17, (v >> 4 & 15) * 17, (v & 15) * 17, (v >> 12 & 15) * 17)
    return (v >> 8 & 255, v & 255, 128, 255)


def decode(data, fmt, dt, w, h):
    """decode the largest level; returns RGBA bytes or None if unsupported"""
    if fmt not in (0, 1, 2):
        return None
    if dt in (1, 2, 0x12):                    # square twiddled (+mip: largest level is last)
        if w != h:
            return None
        n = w * h * 2
        d = data[-n:] if dt != 1 else data[:n]
        if len(d) < n:
            return None
        t = twid(w)
        px16 = struct.unpack('<%dH' % (w * h), d[:n])
        out = bytearray(w * h * 4)
        for i in range(w * h):
            out[i * 4:i * 4 + 4] = bytes(px(fmt, px16[t[i]]))
        return bytes(out)
    if dt in (3, 4, 0x10, 0x11):              # VQ / small VQ (codebook size depends on w for small VQ)
        if w != h:
            return None
        if dt in (3, 4):
            ncode = 256
        elif dt == 0x10:
            ncode = 16 if w <= 16 else 32 if w <= 32 else 128 if w <= 64 else 256
        else:
            ncode = 16 if w <= 16 else 64 if w <= 32 else 256
        cb = struct.unpack('<%dH' % (ncode * 4), data[:ncode * 8])
        nidx = (w // 2) * (h // 2)
        idx = data[ncode * 8:ncode * 8 + nidx] if dt in (3, 0x10) else data[-nidx:]
        if len(idx) < nidx:
            return None
        n2 = w // 2
        t = twid(n2)
        out = bytearray(w * h * 4)
        for y in range(n2):
            for x in range(n2):
                c = idx[t[y * n2 + x]]
                for k, (dx, dy) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
                    p = px(fmt, cb[c * 4 + k])
                    o = ((2 * y + dy) * w + 2 * x + dx) * 4
                    out[o:o + 4] = bytes(p)
        return bytes(out)
    if dt == 9:                               # rectangle linear
        n = w * h * 2
        if len(data) < n:
            return None
        px16 = struct.unpack('<%dH' % (w * h), data[:n])
        out = bytearray(w * h * 4)
        for i, v in enumerate(px16):
            out[i * 4:i * 4 + 4] = bytes(px(fmt, v))
        return bytes(out)
    if dt == 0xD:                             # rectangle twiddled
        n = w * h * 2
        if len(data) < n:
            return None
        s = min(w, h)
        t = twid(s)
        px16 = struct.unpack('<%dH' % (w * h), data[:n])
        out = bytearray(w * h * 4)
        for blk in range((w * h) // (s * s)):
            for y in range(s):
                for x in range(s):
                    v = px16[blk * s * s + t[y * s + x]]
                    if w > h:
                        o = (y * w + blk * s + x) * 4
                    else:
                        o = ((blk * s + y) * w + x) * 4
                    out[o:o + 4] = bytes(px(fmt, v))
        return bytes(out)
    return None


def png(w, h, rgba, path):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgba[y * w * 4:(y + 1) * w * 4]

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
                chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))


def parse_pvr(d):
    """GBIX/PVRT blob -> dict(fmt, dt, w, h, data) or None"""
    o = 0
    if d[:4] == b'GBIX':
        o = 8 + struct.unpack_from('<I', d, 4)[0]
    if d[o:o + 4] != b'PVRT':
        return None
    ln, = struct.unpack_from('<I', d, o + 4)
    fmt, dt = d[o + 8], d[o + 9]
    w, h = struct.unpack_from('<HH', d, o + 12)
    return dict(fmt=fmt, dt=dt, w=w, h=h, data=d[o + 16:o + 8 + ln], gbix=o > 0)


def parse_tbd(d):
    """texture bundle -> list of dict(fmt, dt, w, h, comp, off, raw) (raw = still-compressed bytes) or None"""
    if len(d) < 20:
        return None
    n, = struct.unpack_from('<I', d, 0)
    if not 0 < n < 4096 or 4 + 16 * n > len(d):
        return None
    recs = []
    for i in range(n):
        f, w, h, off, st = struct.unpack_from('<IHHII', d, 4 + 16 * i)
        recs.append((f, w, h, off, st))
    if recs[0][3] != 4 + 16 * n:
        return None
    out = []
    for i, (f, w, h, off, st) in enumerate(recs):
        end = recs[i + 1][3] if i + 1 < n else len(d)
        if off > end or end > len(d):
            return None
        out.append(dict(fmt=f & 0xff, dt=f >> 8 & 0xff, comp=f >> 30, w=w, h=h, off=off, raw=d[off:end], flags=f))
    return out


def tbd_plain(rec):
    c = rec['comp']
    if c == 0:
        return rec['raw']
    return bzlib.decompress(rec['raw'], None, '-bzw-' if c == 1 else '-bz--')   # flag bit30 -> word LZ (FUN_8c15aae4), bit31 -> byte LZ (FUN_8c15a9f4); verified in FUN_8c15a776
