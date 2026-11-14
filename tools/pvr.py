"""pvr - decode and ENCODE Dreamcast PowerVR (PVR/PVRT) texture data for SakaTsuku Tokudaigou 2.

Pure Python + numpy (Pillow is only needed for the optional PNG helpers).
Run with  python -I -X utf8 tools/pvr.py --help   for the small CLI.
See docs/textures.md for the formats found on the disc and how they are stored.

Terminology
-----------
pix  pixel format byte:   0 ARGB1555  1 RGB565  2 ARGB4444  3 YUV422  4 BUMP  5 PAL4  6 PAL8
     (inside the disc's texture-bundle records 'pix' of a paletted texture is the format of the
      palette entries, 0..2; the data format alone says that texels are indices)
dat  data format byte:    1 square twiddled        2 square twiddled + mipmaps   3 VQ    4 VQ + mipmaps
                          5 4bpp paletted           6 4bpp paletted + mips       7 8bpp paletted   8 8bpp pal + mips
                          9 rectangle (linear)      0xA rectangle + mips        0xB stride (linear)
                          0xD rectangle twiddled    0x10 small VQ                0x11 small VQ + mipmaps
                          0x12 square twiddled + mipmaps (alternate)
A "texture" is (pix, dat, w, h) + payload bytes.  Payload = the pixel data only.  On the disc a
payload lives either behind a GBIX/PVRT header (".pvr" files and members) or, in the texture
bundles (".tbd", ".dat", tails of ".zar"), without any header (the format is in the table record).

Public API
----------
parse_file(data)                     -> PVRFile | None     (GBIX/PVRT wrapper)
data_size(pix, dat, w, h)            -> payload byte length the game expects   (KeyError-free; ValueError if unsupported)
decode(data, pix=None, dat=None, w=None, h=None, palette=None, level=0) -> uint8 array (H, W, 4) RGBA
decode_ex(...)                       -> Decoded (image, words, indices, codebook, levels, ...)
encode(image, pix=None, dat=None, w=None, h=None, original=None, palette=None, **opts) -> bytes
encode_ex(...)                       -> Encoded (data, codebook, palette, stats)
build_file(pix, dat, w, h, payload, gbix=None) -> bytes
parse_pvp(data) / build_pvp(...)     palette files (PVPL)
quantize_palette(rgba, n, pix)       k-means palette from an image
to_png(rgba, path) / from_png(path)  Pillow helpers

Layouts (all PROVEN on the disc, see tests):  twiddle = texel (x,y) at stream position
interleave(x bits on odd positions, y bits on even); VQ = 256-entry (or less for small VQ)
codebook of 2x2 blocks (4 x 16-bit texels, order (0,0),(0,1),(1,0),(1,1) = (x,y)) + one index byte per 2x2
block in twiddled order; mip levels are stored smallest first with the full-size level LAST for
twiddled mips (2-byte pad in front) and with the full-size level followed by 10 pad bytes for VQ mips.
"""
import os
import struct
import sys

import numpy as np

# ------------------------------------------------------------------ constants
ARGB1555, RGB565, ARGB4444, YUV422, BUMP, PAL4, PAL8 = range(7)
PIX_NAMES = {0: 'ARGB1555', 1: 'RGB565', 2: 'ARGB4444', 3: 'YUV422', 4: 'BUMP', 5: 'PAL4', 6: 'PAL8'}
DAT_NAMES = {1: 'twiddled', 2: 'twiddled+mips', 3: 'VQ', 4: 'VQ+mips', 5: 'pal4', 6: 'pal4+mips', 7: 'pal8',
             8: 'pal8+mips', 9: 'rectangle', 0xA: 'rectangle+mips', 0xB: 'stride', 0xD: 'rect-twiddled',
             0x10: 'smallVQ', 0x11: 'smallVQ+mips', 0x12: 'twiddled+mips(alt)'}

VQ_FORMATS = (3, 4, 0x10, 0x11)
MIP_FORMATS = (2, 4, 6, 8, 0xA, 0x11, 0x12)
PAL_FORMATS = (5, 6, 7, 8)
TWIDDLED_FORMATS = (1, 2, 5, 6, 7, 8, 0xD, 0x12)
LINEAR_FORMATS = (9, 0xA, 0xB)

TWID_MIP_PAD = 2        # bytes in front of the 1x1 level of a 16 bpp twiddled mip chain (PROVEN: sizes)
VQ_MIP_TRAIL = 10       # bytes behind the full-size index level of a VQ mip chain (PROVEN: smoothness test)


class PVRError(ValueError):
    pass


# ---------------------------------------------------------------- format info
def is_vq(dat):
    return dat in VQ_FORMATS


def has_mips(dat):
    return dat in MIP_FORMATS


def index_bits(dat):
    """Bits per texel index for paletted formats, else None."""
    return {5: 4, 6: 4, 7: 8, 8: 8}.get(dat)


def vq_codes(dat, w):
    """Number of codebook entries."""
    if dat in (3, 4):
        return 256
    if dat == 0x10:          # 16:16 32:32 64:128 PROVEN; 8 and >=128 INFERRED (Puyo Tools numbers)
        return 16 if w <= 16 else 32 if w <= 32 else 128 if w <= 64 else 256
    if dat == 0x11:          # 16:16 32:64 PROVEN; 8 and >=64 INFERRED
        return 16 if w <= 16 else 64 if w <= 32 else 128 if w <= 64 else 256
    raise PVRError('not a VQ format: %#x' % dat)


def _is_pow2(x):
    return x > 0 and (x & (x - 1)) == 0


def _levels(dat, w, h):
    """Mip chain dimensions, full size first (a single entry for non-mip formats)."""
    if not has_mips(dat):
        return [(w, h)]
    if w != h or not _is_pow2(w):
        raise PVRError('mipmapped texture must be square power of two, got %dx%d' % (w, h))
    out = []
    n = w
    while n >= 1:
        out.append((n, n))
        n //= 2
    return out


def _texel_bits(dat):
    return index_bits(dat) or 16


def _level_bytes(dat, lw, lh):
    """Payload bytes of one level (VQ: index bytes)."""
    if is_vq(dat):
        return max(1, lw // 2) * max(1, lh // 2)
    return (lw * lh * _texel_bits(dat) + 7) // 8


class Layout:
    """Byte layout of a payload.  `levels`: list of (lw, lh, offset, nbytes), full size FIRST."""

    def __init__(self, pix, dat, w, h):
        if dat not in DAT_NAMES:
            raise PVRError('unknown data format %#x' % dat)
        if dat in (6, 8, 0xA):
            raise PVRError('data format %#x (%s) is not implemented (not used on this disc)' % (dat, DAT_NAMES[dat]))
        self.pix, self.dat, self.w, self.h = pix, dat, w, h
        dims = _levels(dat, w, h)
        self.head = 0
        if is_vq(dat):
            if w != h or not _is_pow2(w) or w < 2:
                raise PVRError('VQ textures must be square power of two >= 2, got %dx%d' % (w, h))
            self.ncodes = vq_codes(dat, w)
            self.head = self.ncodes * 8
        else:
            self.ncodes = 0
            if dat in (1, 5, 7) or dat in (2, 0x12):
                if w != h and dat in (1, 2, 0x12, 5, 7):
                    # non square twiddled is legal for the hardware (blocks of min x min); keep it permissive
                    if not (_is_pow2(w) and _is_pow2(h)):
                        raise PVRError('bad twiddled size %dx%d' % (w, h))
        sizes = [_level_bytes(dat, lw, lh) for lw, lh in dims]
        if dat in (2, 0x12):
            pre, post = TWID_MIP_PAD, 0
        elif dat == 4 or dat == 0x11:
            pre, post = 0, VQ_MIP_TRAIL
        else:
            pre, post = 0, 0
        self.pre, self.post = pre, post
        # stored smallest -> largest
        off = self.head + pre
        offs = [0] * len(dims)
        for i in range(len(dims) - 1, -1, -1):
            offs[i] = off
            off += sizes[i]
        self.levels = [(dims[i][0], dims[i][1], offs[i], sizes[i]) for i in range(len(dims))]
        self.total = off + post


def data_size(pix, dat, w, h):
    """Expected payload length in bytes."""
    return Layout(pix, dat, w, h).total


# ---------------------------------------------------------------- twiddling
_TW = {}


def _spread(a, bits):
    r = np.zeros_like(a)
    for i in range(bits):
        r |= ((a >> i) & 1) << (2 * i)
    return r


def twiddle_map(n):
    """int64 array (n, n): stream position of texel (y, x).  x bits -> odd, y bits -> even positions."""
    m = _TW.get(n)
    if m is None:
        bits = max(0, n.bit_length() - 1)
        a = np.arange(n, dtype=np.int64)
        s = _spread(a, bits)
        m = (s[None, :] << 1) | s[:, None]
        m.setflags(write=False)
        _TW[n] = m
    return m


_PM = {}


def pos_map(dat, w, h):
    """int64 array (h, w) giving, for every texel, its position in the stored texel stream."""
    key = (dat in LINEAR_FORMATS, w, h)
    m = _PM.get(key)
    if m is not None:
        return m
    if dat in LINEAR_FORMATS:
        m = np.arange(w * h, dtype=np.int64).reshape(h, w)
    elif w == h:
        m = twiddle_map(w)
    else:
        s = min(w, h)
        t = twiddle_map(s)
        yy, xx = np.mgrid[0:h, 0:w]
        if w > h:
            m = (xx // s) * s * s + t[yy, xx % s]
        else:
            m = (yy // s) * s * s + t[yy % s, xx]
    m = np.ascontiguousarray(m)
    m.setflags(write=False)
    _PM[key] = m
    return m


# ---------------------------------------------------------- pixel conversion
_LUT = {}


def _build_lut(pix):
    v = np.arange(65536, dtype=np.int32)
    lut = np.zeros((65536, 4), dtype=np.uint8)
    if pix == ARGB1555:
        r, g, b = (v >> 10) & 31, (v >> 5) & 31, v & 31
        lut[:, 0] = (r << 3) | (r >> 2)
        lut[:, 1] = (g << 3) | (g >> 2)
        lut[:, 2] = (b << 3) | (b >> 2)
        lut[:, 3] = np.where(v & 0x8000, 255, 0)
    elif pix == RGB565:
        r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
        lut[:, 0] = (r << 3) | (r >> 2)
        lut[:, 1] = (g << 2) | (g >> 4)
        lut[:, 2] = (b << 3) | (b >> 2)
        lut[:, 3] = 255
    elif pix == ARGB4444:
        lut[:, 0] = ((v >> 8) & 15) * 17
        lut[:, 1] = ((v >> 4) & 15) * 17
        lut[:, 2] = (v & 15) * 17
        lut[:, 3] = ((v >> 12) & 15) * 17
    elif pix == BUMP:       # INFERRED (no sample on the disc): high byte = S, low byte = R; shown as (R, S, 0)
        lut[:, 0] = v & 255
        lut[:, 1] = v >> 8
        lut[:, 2] = 0
        lut[:, 3] = 255
    else:
        raise PVRError('no direct colour conversion for pixel format %d' % pix)
    return lut


def words_to_rgba(words, pix):
    """uint16 texel words (any shape) -> uint8 (..., 4)."""
    lut = _LUT.get(pix)
    if lut is None:
        lut = _LUT[pix] = _build_lut(pix)
    return lut[np.asarray(words, dtype=np.int64)]


def rgba_to_words(rgba, pix):
    """uint8 (..., 4) -> uint16 words (nearest representable value, rounding)."""
    a = np.asarray(rgba).astype(np.int32)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    if pix == ARGB1555:
        w = ((al >= 128).astype(np.int32) << 15) | (((r * 31 + 127) // 255) << 10) | (((g * 31 + 127) // 255) << 5) \
            | ((b * 31 + 127) // 255)
    elif pix == RGB565:
        w = (((r * 31 + 127) // 255) << 11) | (((g * 63 + 127) // 255) << 5) | ((b * 31 + 127) // 255)
    elif pix == ARGB4444:
        w = (((al * 15 + 127) // 255) << 12) | (((r * 15 + 127) // 255) << 8) | (((g * 15 + 127) // 255) << 4) \
            | ((b * 15 + 127) // 255)
    elif pix == BUMP:
        w = (g << 8) | r
    else:
        raise PVRError('no direct colour conversion for pixel format %d' % pix)
    return w.astype(np.uint16)


def _yuv_decode(words):
    """words (h, w) uint16 (w even): even x = (Y0<<8|U), odd x = (Y1<<8|V) -> RGBA (INFERRED, no sample)."""
    w16 = words.astype(np.int32)
    y = (w16 >> 8) & 255
    u = np.repeat(w16[:, 0::2] & 255, 2, axis=1) - 128
    v = np.repeat(w16[:, 1::2] & 255, 2, axis=1) - 128
    r = y + 1.402 * v
    g = y - 0.344136 * u - 0.714136 * v
    b = y + 1.772 * u
    out = np.stack([r, g, b], -1)
    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return np.concatenate([out, np.full(out.shape[:2] + (1,), 255, np.uint8)], -1)


def _yuv_encode(rgba):
    a = rgba.astype(np.float64)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    u = (b - y) / 1.772 + 128
    v = (r - y) / 1.402 + 128
    h, w = y.shape
    ua = u.reshape(h, w // 2, 2).mean(2)
    va = v.reshape(h, w // 2, 2).mean(2)
    yi = np.clip(np.rint(y), 0, 255).astype(np.int32)
    ui = np.clip(np.rint(ua), 0, 255).astype(np.int32)
    vi = np.clip(np.rint(va), 0, 255).astype(np.int32)
    out = np.zeros((h, w), dtype=np.int32)
    out[:, 0::2] = (yi[:, 0::2] << 8) | ui
    out[:, 1::2] = (yi[:, 1::2] << 8) | vi
    return out.astype(np.uint16)


# ------------------------------------------------------------ palette (PVP)
class Palette:
    """Palette entries as RGBA (n, 4) uint8 plus the entry format."""

    def __init__(self, rgba, pix=6, header=None, words=None):
        self.rgba = np.asarray(rgba, dtype=np.uint8).reshape(-1, 4)
        self.pix = pix
        self.header = header          # original 16 byte PVPL header (or None)
        self.words = words            # original raw entries (np array) for bit exact re-write

    def __len__(self):
        return len(self.rgba)


def parse_pvp(data):
    """PVPL palette file -> Palette.  Entry format 0/1/2 = 16-bit, 6 = ARGB8888 (B,G,R,A bytes)."""
    data = bytes(data)
    if data[:4] != b'PVPL':
        raise PVRError('not a PVPL file')
    size, pix = struct.unpack_from('<IB', data, 4)
    n = struct.unpack_from('<H', data, 14)[0]
    body = data[16:16 + (4 if pix == 6 else 2) * n]
    if pix == 6:
        raw = np.frombuffer(body, 'u1').reshape(n, 4)
        rgba = raw[:, [2, 1, 0, 3]]
        return Palette(rgba, 6, data[:16], raw)
    raw = np.frombuffer(body, '<u2')
    return Palette(words_to_rgba(raw, pix), pix, data[:16], raw)


def build_pvp(pal, original=None):
    """Palette -> PVPL bytes.  With `original` (bytes) the header and trailing bytes are kept."""
    pix = pal.pix
    n = len(pal)
    if pix == 6:
        raw = np.asarray(pal.rgba, np.uint8)[:, [2, 1, 0, 3]].tobytes()
    else:
        raw = rgba_to_words(pal.rgba, pix).astype('<u2').tobytes()
    if original is not None:
        original = bytes(original)
        hdr = original[:16]
        tail = original[16 + len(raw):]
        return hdr + raw + tail
    hdr = b'PVPL' + struct.pack('<I', len(raw) + 8) + bytes([pix, 0]) + b'\0\0' + struct.pack('<HH', 0, n)
    return hdr + raw


def _as_palette(palette, pix_hint=None):
    if palette is None:
        return None
    if isinstance(palette, Palette):
        return palette
    if isinstance(palette, (bytes, bytearray)):
        return parse_pvp(palette)
    return Palette(np.asarray(palette, dtype=np.uint8), pix_hint if pix_hint is not None else 6)


# ------------------------------------------------------------ file wrapper
class PVRFile:
    """Parsed GBIX/PVRT wrapper.  `prefix` = bytes before the pixel data (GBIX + PVRT header),
    `data_off`/`data_len` locate the payload (data_len from the PVRT size field, clipped to the file)."""

    def __repr__(self):
        return '<PVRFile %s/%s %dx%d gbix=%s data=%d+%d>' % (
            PIX_NAMES.get(self.pix, self.pix), DAT_NAMES.get(self.dat, self.dat), self.w, self.h,
            self.gbix, self.data_off, self.data_len)


def parse_file(data):
    """Parse a GBIX+PVRT / PVRT blob; None when `data` is not one."""
    data = bytes(data) if not isinstance(data, (bytes, bytearray, memoryview)) else data
    o = 0
    gbix = None
    if data[:4] == b'GBIX':
        if len(data) < 16:
            return None
        gsz = struct.unpack_from('<I', data, 4)[0]
        if gsz > 64:
            return None
        gbix = struct.unpack_from('<I', data, 8)[0]
        o = 8 + gsz
    if data[o:o + 4] != b'PVRT' or o + 16 > len(data):
        return None
    size, pix, dat, _pad, w, h = struct.unpack_from('<IBBHHH', data, o + 4)
    f = PVRFile()
    f.gbix, f.pvrt_off, f.size = gbix, o, size
    f.pix, f.dat, f.w, f.h = pix, dat, w, h
    f.data_off = o + 16
    f.data_len = min(size - 8, len(data) - f.data_off)
    f.prefix = bytes(data[:f.data_off])
    return f


def build_file(pix, dat, w, h, payload, gbix=0):
    """GBIX + PVRT file around `payload` (gbix None -> bare PVRT)."""
    pre = b'' if gbix is None else b'GBIX' + struct.pack('<III', 8, gbix, 0)
    return pre + b'PVRT' + struct.pack('<IBBHHH', len(payload) + 8, pix, dat, 0, w, h) + bytes(payload)


# ------------------------------------------------------------ decoding
class Decoded:
    """Result of decode_ex.
    image     (h, w, 4) uint8 RGBA of the requested level
    words     (h, w) uint16 texel words (or uint8 indices for paletted) of that level
    indices   VQ: (h/2, w/2) codebook indices of that level;  paletted: same as words
    codebook  VQ: (n, 4) uint16 words
    levels    list of RGBA arrays, full size first (all stored mip levels)
    palette   Palette used (paletted) or None
    fmt       (pix, dat, w, h);  payload_len, pre_pad, post_pad
    """


def _resolve(data, pix, dat, w, h):
    """-> (payload memoryview-able bytes, pix, dat, w, h, PVRFile|None)"""
    f = None
    if data[:4] in (b'GBIX', b'PVRT'):
        f = parse_file(data)
    if f is not None:
        payload = bytes(data[f.data_off:f.data_off + f.data_len])
        return payload, f.pix, f.dat, f.w, f.h, f
    if pix is None or dat is None or w is None or h is None:
        raise PVRError('raw payload needs pix, dat, w, h')
    return bytes(data), pix, dat, w, h, None


def _read_direct(buf, off, w, h, dat):
    n = w * h
    bits = _texel_bits(dat)
    pm = pos_map(dat, w, h)
    if bits == 16:
        stream = np.frombuffer(buf, '<u2', n, off)
    elif bits == 8:
        stream = np.frombuffer(buf, 'u1', n, off)
    else:
        raw = np.frombuffer(buf, 'u1', (n + 1) // 2, off)
        stream = np.empty(((n + 1) // 2) * 2, np.uint8)
        stream[0::2] = raw & 15
        stream[1::2] = raw >> 4
        stream = stream[:n]
    return stream[pm]


def _write_direct(arr, dat):
    h, w = arr.shape
    n = w * h
    bits = _texel_bits(dat)
    pm = pos_map(dat, w, h)
    if bits == 16:
        stream = np.empty(n, '<u2')
        stream[pm.ravel()] = arr.ravel()
        return stream.tobytes()
    if bits == 8:
        stream = np.empty(n, np.uint8)
        stream[pm.ravel()] = arr.ravel()
        return stream.tobytes()
    stream = np.zeros(((n + 1) // 2) * 2, np.uint8)
    stream[pm.ravel()] = arr.ravel()
    return (stream[0::2] | (stream[1::2] << 4)).astype(np.uint8).tobytes()


def _read_indices(buf, off, lw, lh):
    """VQ index grid (lh/2, lw/2) (1x1 for the 2x2 and 1x1 levels)."""
    gw, gh = max(1, lw // 2), max(1, lh // 2)
    stream = np.frombuffer(buf, 'u1', gw * gh, off)
    return stream[twiddle_map(gw)] if gw == gh else stream[pos_map(1, gw, gh)]


def _write_indices(grid):
    gh, gw = grid.shape
    stream = np.empty(gw * gh, np.uint8)
    pm = twiddle_map(gw) if gw == gh else pos_map(1, gw, gh)
    stream[pm.ravel()] = grid.ravel()
    return stream.tobytes()


def ext_codebook(payload, ncodes):
    """A 256-entry view of the codebook for indices >= ncodes: the game's small-VQ textures can address past their
    codebook, where the GPU simply reads the following bytes of the same texture (here: the payload itself)."""
    buf = bytes(payload[:256 * 8])
    buf += b'\0' * (256 * 8 - len(buf))
    return np.frombuffer(buf, '<u2').reshape(256, 4)


def _vq_blocks_to_words(cb, grid, lw, lh):
    """cb (n,4) uint16, grid (gh, gw) -> words (lh, lw).  Texel k of a block = (dx = k>>1, dy = k&1)."""
    gh, gw = grid.shape
    b = cb[grid]                                         # gh, gw, 4
    if lw == 1:                                          # 1x1 level: first texel of the block
        return b[:, :, 0].reshape(1, 1)
    out = np.zeros((gh * 2, gw * 2), np.uint16)
    for k in range(4):
        out[(k & 1)::2, (k >> 1)::2] = b[:, :, k]
    return out


def _vq_words_to_blocks(words):
    """(H, W) -> (nb, 4) block vectors, raster block order, k = dx*2 + dy."""
    h, w = words.shape
    if w == 1:
        return np.repeat(words.reshape(1, 1), 4, axis=1)
    b = words.reshape(h // 2, 2, w // 2, 2)              # by, dy, bx, dx
    return b.transpose(0, 2, 3, 1).reshape(-1, 4)


def _palette_apply(idx, palette):
    n = len(palette)
    safe = np.minimum(idx.astype(np.int64), n - 1)
    return palette.rgba[safe]


def decode_ex(data, pix=None, dat=None, w=None, h=None, palette=None, level=0):
    """Full decode.  `data` = PVR file bytes (header read from it) or raw payload with pix/dat/w/h given."""
    payload, pix, dat, w, h, f = _resolve(data, pix, dat, w, h)
    lay = Layout(pix, dat, w, h)
    if len(payload) < lay.total:
        raise PVRError('payload too short: %d < %d for %s/%s %dx%d' % (len(payload), lay.total, pix, dat, w, h))
    pal = _as_palette(palette)
    res = Decoded()
    res.fmt = (pix, dat, w, h)
    res.layout = lay
    res.palette = pal
    res.file = f
    res.payload_len = len(payload)
    res.pre_pad = payload[lay.head:lay.head + lay.pre] if lay.pre else b''
    res.post_pad = payload[lay.total - lay.post:lay.total] if lay.post else b''
    res.codebook = None
    levels_rgba, levels_words, levels_idx = [], [], []
    if is_vq(dat):
        cb = np.frombuffer(payload, '<u2', lay.ncodes * 4, 0).reshape(lay.ncodes, 4)
        res.codebook = cb
        res.oob_indices = False
        cpix = pix
        for lw, lh, off, nb in lay.levels:
            grid = _read_indices(payload, off, lw, lh)
            if int(grid.max()) >= lay.ncodes:      # index beyond the codebook: hardware reads on into the payload
                cb_use = ext_codebook(payload, lay.ncodes)
                res.oob_indices = True
            else:
                cb_use = cb
            words = _vq_blocks_to_words(cb_use, grid, lw, lh)
            levels_idx.append(grid)
            levels_words.append(words)
            levels_rgba.append(_colour(words, cpix))
    elif dat in PAL_FORMATS:
        for lw, lh, off, nb in lay.levels:
            idx = _read_direct(payload, off, lw, lh, dat)
            levels_idx.append(idx)
            levels_words.append(idx)
            if pal is None:
                g = (idx.astype(np.int32) * 255 // (255 if index_bits(dat) == 8 else 15)).astype(np.uint8)
                levels_rgba.append(np.stack([g, g, g, np.full_like(g, 255)], -1))
            else:
                levels_rgba.append(_palette_apply(idx, pal))
    else:
        for lw, lh, off, nb in lay.levels:
            words = _read_direct(payload, off, lw, lh, dat)
            levels_idx.append(words)
            levels_words.append(words)
            levels_rgba.append(_colour(words, pix))
    res.levels = levels_rgba
    res.level_words = levels_words
    res.level_indices = levels_idx
    if level >= len(levels_rgba):
        raise PVRError('level %d out of range (%d levels)' % (level, len(levels_rgba)))
    res.image = levels_rgba[level]
    res.words = levels_words[level]
    res.indices = levels_idx[level]
    return res


def _colour(words, pix):
    if pix == YUV422:
        return _yuv_decode(words)
    return words_to_rgba(words, pix)


def decode(data, pix=None, dat=None, w=None, h=None, palette=None, level=0):
    """Decode a texture to an RGBA uint8 array (h, w, 4).  See module docstring."""
    return decode_ex(data, pix, dat, w, h, palette, level).image


# ------------------------------------------------------------ quantisation
def _sqdist(X, C):
    return (X * X).sum(1)[:, None] - 2.0 * (X @ C.T) + (C * C).sum(1)[None, :]


def _assign(X, C, chunk=16384):
    """Nearest centroid index and squared distance for every row of X."""
    m = len(X)
    idx = np.empty(m, np.int64)
    dist = np.empty(m, np.float64)
    C = np.asarray(C, np.float64)
    c2 = (C * C).sum(1)[None, :]
    for s in range(0, m, chunk):
        x = np.asarray(X[s:s + chunk], np.float64)
        d = (x * x).sum(1)[:, None] - 2.0 * (x @ C.T) + c2
        j = d.argmin(1)
        idx[s:s + chunk] = j
        dist[s:s + chunk] = np.maximum(d[np.arange(len(x)), j], 0)
    return idx, dist


def kmeans(X, wts, k, fixed=None, iters=12, seed=0):
    """Weighted k-means (k-means++ seeding) on rows of X (m, d) float32.
    `fixed` (f, d): extra centroids that attract points but are never moved.
    Returns new centroids (k, d) (float64)."""
    X = np.asarray(X, np.float32)
    wts = np.asarray(wts, np.float64)
    m, d = X.shape
    rng = np.random.RandomState(seed)
    if m <= k:
        out = np.zeros((k, d))
        out[:m] = X
        return out
    # --- k-means++ seeding
    if fixed is not None and len(fixed):
        near = _assign(X, np.asarray(fixed, np.float32))[1]
    else:
        near = np.full(m, np.inf)
    cents = []
    for i in range(k):
        if i == 0 and not np.isfinite(near).any():
            p = wts / wts.sum()
        else:
            p = np.where(np.isfinite(near), near, 1e9) * wts
            s = p.sum()
            if s <= 0:
                p = wts / wts.sum()
            else:
                p = p / s
        j = min(int(np.searchsorted(np.cumsum(p), rng.random_sample())), m - 1)
        cents.append(X[j].astype(np.float64))
        dj = ((X - X[j]) ** 2).sum(1)
        near = np.minimum(near, dj)
    C = np.array(cents)
    F = np.asarray(fixed, np.float64) if fixed is not None and len(fixed) else np.zeros((0, d))
    # --- Lloyd
    prev = None
    for it in range(iters):
        allc = np.concatenate([C, F]).astype(np.float32)
        idx, dist = _assign(X, allc)
        if prev is not None and np.array_equal(idx, prev):
            break
        prev = idx
        sel = idx < k
        wsum = np.bincount(idx[sel], weights=wts[sel], minlength=k)
        for dim in range(d):
            C_new = np.bincount(idx[sel], weights=wts[sel] * X[sel, dim], minlength=k)
            nz = wsum > 0
            C[nz, dim] = C_new[nz] / wsum[nz]
        empty = np.where(wsum <= 0)[0]
        if len(empty):
            err = dist * wts
            order = np.argsort(-err)
            for e, j in zip(empty, order[:len(empty)]):
                C[e] = X[j]
    return C


def quantize_palette(rgba, n, pix=ARGB4444, seed=0, iters=15):
    """Palette (n, 4) uint8 RGBA for an image, k-means on the distinct colours (weighted by use).
    Colours are first snapped to the entry format `pix` so the palette is representable."""
    a = np.asarray(rgba, np.uint8).reshape(-1, 4)
    if pix in (0, 1, 2):
        a = words_to_rgba(rgba_to_words(a, pix), pix)
    key = (a[:, 0].astype(np.uint32) << 24) | (a[:, 1].astype(np.uint32) << 16) | (a[:, 2].astype(np.uint32) << 8) \
        | a[:, 3].astype(np.uint32)
    uk, counts = np.unique(key, return_counts=True)
    cols = np.stack([(uk >> 24) & 255, (uk >> 16) & 255, (uk >> 8) & 255, uk & 255], -1).astype(np.uint8)
    if len(cols) <= n:
        out = np.zeros((n, 4), np.uint8)
        out[:len(cols)] = cols
        return out
    X = cols.astype(np.float32) / 255.0
    C = kmeans(X, counts.astype(np.float64), n, iters=iters, seed=seed)
    out = np.clip(np.rint(C * 255.0), 0, 255).astype(np.uint8)
    if pix in (0, 1, 2):
        out = words_to_rgba(rgba_to_words(out, pix), pix)
    return out


def _pack4(words):
    w = np.asarray(words).astype(np.uint64)
    return w[..., 0] | (w[..., 1] << np.uint64(16)) | (w[..., 2] << np.uint64(32)) | (w[..., 3] << np.uint64(48))


def _feat(words, pix):
    """block words (n, 4) -> float32 (n, 16) feature vectors (RGBA/255 of the 4 texels)."""
    rgba = words_to_rgba(words, pix) if pix != YUV422 else None
    return (rgba.reshape(len(words), 16).astype(np.float32)) / 255.0


def _feat_to_words(F, pix):
    rgba = np.clip(np.rint(F.reshape(-1, 4, 4) * 255.0), 0, 255).astype(np.uint8)
    return rgba_to_words(rgba, pix).reshape(-1, 4)


def vq_quantize(blocks, ncodes, pix, orig_cb=None, orig_idx=None, reserve=0.25, seed=0, iters=12,
                force_changed=None):
    """Build a VQ codebook + index list for `blocks` (nb, 4) uint16 texel words.

    Without `orig_cb`/`orig_idx` the codebook is trained from scratch (exact when the image has at most
    `ncodes` distinct blocks).  With them the ORIGINAL codebook is preserved: blocks that did not change keep
    their code, changed blocks use exact matches / nearest codes, and the free codebook slots (plus slots freed by
    merging the cheapest pairs of old codes until about `reserve` * ncodes are free) are trained on the changed
    blocks.  Returns (codebook (ncodes, 4) uint16, indices (nb,) int64, info dict)."""
    blocks = np.asarray(blocks, np.uint16)
    nb = len(blocks)
    info = {'mode': 'scratch', 'changed_blocks': nb, 'merged_codes': 0, 'new_codes': 0}
    if orig_cb is None or orig_idx is None:
        uniq, inv, counts = np.unique(blocks, axis=0, return_inverse=True, return_counts=True)
        inv = inv.reshape(-1)
        if len(uniq) <= ncodes:
            cb = np.zeros((ncodes, 4), np.uint16)
            cb[:len(uniq)] = uniq
            info['exact'] = True
            return cb, inv.astype(np.int64), info
        X = _feat(uniq, pix)
        C = kmeans(X, counts.astype(np.float64), ncodes, iters=iters, seed=seed)
        cb = _feat_to_words(C, pix)
        idx_u, _ = _assign(X, _feat(cb, pix))
        info['exact'] = False
        return cb, idx_u[inv].astype(np.int64), info

    # ---------------- incremental / preserving mode
    orig_cb = np.asarray(orig_cb, np.uint16).copy()
    orig_idx = np.asarray(orig_idx, np.int64)
    ocb_blocks = orig_cb[orig_idx]
    same = (blocks == ocb_blocks).all(1)
    if force_changed is not None:
        same &= ~force_changed
    info['mode'] = 'preserve'
    if same.all():
        info['changed_blocks'] = 0
        return orig_cb, orig_idx.copy(), info
    cb = orig_cb
    idx = orig_idx.copy()
    ch = ~same
    info['changed_blocks'] = int(ch.sum())
    cuniq, cinv, ccount = np.unique(blocks[ch], axis=0, return_inverse=True, return_counts=True)
    cinv = cinv.reshape(-1)
    n_codes = len(cb)
    usage = np.bincount(idx[same], minlength=n_codes).astype(np.float64)
    keep = usage > 0
    # exact matches of changed vectors against any old code
    okeys = _pack4(cb)
    order = np.argsort(okeys, kind='stable')
    skeys = okeys[order]
    ck = _pack4(cuniq)
    pos = np.minimum(np.searchsorted(skeys, ck), len(skeys) - 1)
    hit = skeys[pos] == ck
    code_of = np.full(len(cuniq), -1, np.int64)
    code_of[hit] = order[pos[hit]]
    for ci in np.unique(code_of[hit]):
        keep[ci] = True
    np.add.at(usage, code_of[hit], ccount[hit])
    R = np.where(~hit)[0]
    if len(R):
        nfree = int((~keep).sum())
        need = len(R)
        want = min(need, max(nfree, int(ncodes * reserve)))
        remap = np.arange(n_codes)
        if nfree < want:
            fixed_ids = list(np.where(keep)[0])
            Fv = _feat(cb[fixed_ids], pix).astype(np.float64)
            wv = usage[fixed_ids].copy()
            alive = np.ones(len(fixed_ids), bool)
            to_free = want - nfree
            merged = 0
            while merged < to_free and alive.sum() > 1:
                A = np.where(alive)[0]
                Fa = Fv[A]
                d = _sqdist(Fa, Fa)
                wa = wv[A]
                cost = d * (wa[:, None] * wa[None, :] / (wa[:, None] + wa[None, :]))
                np.fill_diagonal(cost, np.inf)
                i, j = np.unravel_index(np.argmin(cost), cost.shape)
                a, b = A[i], A[j]
                if wv[a] < wv[b]:
                    a, b = b, a
                Fv[a] = (Fv[a] * wv[a] + Fv[b] * wv[b]) / (wv[a] + wv[b])
                wv[a] += wv[b]
                alive[b] = False
                remap[fixed_ids[b]] = fixed_ids[a]
                keep[fixed_ids[b]] = False
                merged += 1
            while True:                                   # resolve chains of merges
                r2 = remap[remap]
                if np.array_equal(r2, remap):
                    break
                remap = r2
            for t, cid in enumerate(fixed_ids):
                if alive[t]:
                    cb[cid] = _feat_to_words(Fv[t:t + 1].astype(np.float32), pix)[0]
            idx = remap[idx]
            code_of = np.where(code_of >= 0, remap[np.maximum(code_of, 0)], -1)
            info['merged_codes'] = merged
            usage = np.bincount(idx[same], minlength=n_codes).astype(np.float64)
        free_ids = np.where(~keep)[0]
        if len(R) <= len(free_ids):
            cb[free_ids[:len(R)]] = cuniq[R]
            code_of[R] = free_ids[:len(R)]
            info['new_codes'] = len(R)
        else:
            k = len(free_ids)
            X = _feat(cuniq[R], pix)
            Fx = _feat(cb[np.where(keep)[0]], pix)
            C = kmeans(X, ccount[R].astype(np.float64), k, fixed=Fx, iters=iters, seed=seed)
            cb[free_ids] = _feat_to_words(C, pix)
            info['new_codes'] = k
            keepers = np.concatenate([np.where(keep)[0], free_ids])
            tgt, _ = _assign(X, _feat(cb[keepers], pix))
            code_of[R] = keepers[tgt]
    idx[ch] = code_of[cinv]
    return cb, idx, info


# ------------------------------------------------------------ encoding
class Encoded:
    """Result of encode_ex: data (bytes), codebook, palette, info dict."""


def _as_rgba(image, w, h):
    a = image
    if hasattr(a, 'convert') and hasattr(a, 'size'):      # PIL image
        a = np.asarray(a.convert('RGBA'))
    a = np.asarray(a)
    if a.ndim == 2:
        a = np.stack([a, a, a, np.full_like(a, 255)], -1)
    if a.shape[2] == 3:
        a = np.concatenate([a, np.full(a.shape[:2] + (1,), 255, a.dtype)], -1)
    a = a.astype(np.uint8)
    if a.shape[0] != h or a.shape[1] != w:
        raise PVRError('image is %dx%d, texture is %dx%d' % (a.shape[1], a.shape[0], w, h))
    return a


def box_down(rgba):
    """2x2 box filter (round to nearest) for the mip chain; works on straight RGBA."""
    h, w = rgba.shape[:2]
    if h == 1 and w == 1:
        return rgba
    a = rgba.astype(np.int32)
    s = a.reshape(h // 2, 2, w // 2, 2, 4).sum((1, 3))
    return ((s + 2) // 4).astype(np.uint8)


def _nearest_palette(rgba, pal_rgba):
    """Index of the nearest palette entry for every pixel (exact colours resolve exactly)."""
    flat = rgba.reshape(-1, 4)
    key = (flat[:, 0].astype(np.uint32) << 24) | (flat[:, 1].astype(np.uint32) << 16) | \
        (flat[:, 2].astype(np.uint32) << 8) | flat[:, 3].astype(np.uint32)
    uk, inv = np.unique(key, return_inverse=True)
    cols = np.stack([(uk >> 24) & 255, (uk >> 16) & 255, (uk >> 8) & 255, uk & 255], -1).astype(np.float32)
    P = pal_rgba.astype(np.float32)
    # alpha counts double so transparent pixels do not map to opaque colours
    sc = np.array([1.0, 1.0, 1.0, 2.0], np.float32)
    j, _ = _assign(cols * sc, P * sc)
    return j[inv.reshape(-1)].reshape(rgba.shape[:2]).astype(np.uint8)


def encode_ex(image, pix=None, dat=None, w=None, h=None, original=None, palette=None, mips='auto',
              reserve=0.25, seed=0, retrain=False, new_palette=False):
    """Encode `image` (RGBA uint8 (h, w, 4), RGB, grey or PIL image) into the payload/file of the same format.

    original : bytes of the texture being replaced (a GBIX/PVRT file, or a raw payload when pix/dat/w/h are
               given).  Gives the format, the pad bytes, the GBIX/PVRT header and - for VQ - the codebook that
               is preserved wherever the image did not change.
    palette  : Palette / PVP bytes / (n,4) RGBA for paletted formats (kept as is unless new_palette=True)
    mips     : 'auto' (regenerate the lower mip levels by box filtering, or keep the original payload untouched
               when the full-size level did not change), 'regen' (always regenerate)
    retrain  : VQ - ignore the original codebook and train a new one from scratch
    new_palette : paletted - derive a fresh k-means palette from the image (result.palette)
    The result has exactly the original byte length (PVRError otherwise)."""
    orig_payload = None
    f = None
    if original is not None:
        original = bytes(original)
        pl, opix, odat, ow, oh, f = _resolve(original, pix, dat, w, h)
        pix, dat, w, h = opix, odat, ow, oh
        orig_payload = pl
    if None in (pix, dat, w, h):
        raise PVRError('encode needs pix, dat, w, h (or an original)')
    lay = Layout(pix, dat, w, h)
    rgba = _as_rgba(image, w, h)
    res = Encoded()
    res.info = {}
    res.palette = None
    res.codebook = None
    pal = _as_palette(palette)
    pre = bytes(orig_payload[lay.head:lay.head + lay.pre]) if orig_payload is not None and lay.pre else b'\0' * lay.pre
    post = bytes(orig_payload[lay.total - lay.post:lay.total]) if orig_payload is not None and lay.post else b'\0' * lay.post
    if orig_payload is not None and len(orig_payload) < lay.total:
        raise PVRError('original payload too short')

    if is_vq(dat):
        payload = _encode_vq(rgba, lay, orig_payload, pre, post, mips, reserve, seed, retrain, res)
    elif dat in PAL_FORMATS:
        payload = _encode_pal(rgba, lay, pal, new_palette, seed, res)
    else:
        payload = _encode_direct(rgba, lay, orig_payload, pre, mips, res)
    if len(payload) != lay.total:
        raise PVRError('internal: payload %d != %d' % (len(payload), lay.total))
    if orig_payload is not None and len(orig_payload) > lay.total:
        payload += bytes(orig_payload[lay.total:])         # keep trailing bytes of the original blob
    if f is not None:
        out = bytes(original[:f.data_off]) + payload + bytes(original[f.data_off + f.data_len:])
        if len(out) != len(original):
            raise PVRError('internal: file length changed')
        res.data = out
    else:
        res.data = payload
        if orig_payload is not None and len(payload) != len(orig_payload):
            raise PVRError('internal: payload length changed')
    return res


def encode(image, pix=None, dat=None, w=None, h=None, original=None, palette=None, **opts):
    """encode_ex(...).data - see encode_ex."""
    return encode_ex(image, pix, dat, w, h, original, palette, **opts).data


def _mip_chain(rgba, lay):
    """List of RGBA arrays full size first, regenerated by box filtering."""
    out = [rgba]
    for _ in range(len(lay.levels) - 1):
        out.append(box_down(out[-1]))
    return out


def _quantised_rgba(rgba, pix):
    return words_to_rgba(rgba_to_words(rgba, pix), pix)


def _encode_direct(rgba, lay, orig_payload, pre, mips, res):
    pix, dat = lay.pix, lay.dat
    if pix == YUV422:
        words0 = _yuv_encode(rgba)
        conv = lambda a: _yuv_encode(a)   # noqa: E731
    else:
        words0 = rgba_to_words(rgba, pix)
        conv = lambda a: rgba_to_words(a, pix)   # noqa: E731
    if orig_payload is not None and mips == 'auto' and len(lay.levels) > 1:
        lw, lh, off, nb = lay.levels[0]
        old0 = _read_direct(orig_payload, off, lw, lh, dat)
        if np.array_equal(old0, words0):
            res.info['mode'] = 'unchanged'
            return bytes(orig_payload[:lay.total])
    chain = [words0]
    if len(lay.levels) > 1:
        rg = _quantised_rgba(rgba, pix) if pix != YUV422 else rgba
        for _ in range(len(lay.levels) - 1):
            rg = box_down(rg)
            chain.append(conv(rg))
    parts = [b'\0' * lay.head, pre]
    for i in range(len(lay.levels) - 1, -1, -1):
        parts.append(_write_direct(chain[i], dat))
    res.info['mode'] = 'direct'
    return b''.join(parts)


def _encode_pal(rgba, lay, pal, new_palette, seed, res):
    dat = lay.dat
    nbits = index_bits(dat)
    ncol = 1 << nbits
    if new_palette or pal is None:
        if pal is None and not new_palette:
            raise PVRError('paletted texture: pass palette= (or new_palette=True)')
        entry_pix = pal.pix if pal is not None else (lay.pix if lay.pix in (0, 1, 2, 6) else ARGB4444)
        pal = Palette(quantize_palette(rgba, ncol, entry_pix if entry_pix != 6 else 2, seed=seed), entry_pix)
    res.palette = pal
    p = pal.rgba
    if len(p) < ncol:
        p = np.concatenate([p, np.zeros((ncol - len(p), 4), np.uint8)])
    idx0 = _nearest_palette(rgba, p[:len(pal.rgba)])
    chain = [idx0]
    if len(lay.levels) > 1:
        rg = rgba
        for _ in range(len(lay.levels) - 1):
            rg = box_down(rg)
            chain.append(_nearest_palette(rg, p[:len(pal.rgba)]))
    parts = []
    for i in range(len(lay.levels) - 1, -1, -1):
        parts.append(_write_direct(chain[i], dat))
    res.info['mode'] = 'palette'
    return b''.join(parts)


def _encode_vq(rgba, lay, orig_payload, pre, post, mips, reserve, seed, retrain, res):
    pix, dat = lay.pix, lay.dat
    ncodes = lay.ncodes
    words0 = rgba_to_words(rgba, pix)
    blocks0 = _vq_words_to_blocks(words0)
    ocb = oidx = None
    if orig_payload is not None:
        ocb = np.frombuffer(orig_payload, '<u2', ncodes * 4, 0).reshape(ncodes, 4)
        lw, lh, off, nb = lay.levels[0]
        grid = _read_indices(orig_payload, off, lw, lh)
        oidx = grid.reshape(-1).astype(np.int64)
        oob = oidx >= ncodes                    # indices past the codebook (see ext_codebook)
        if oob.any():
            old_blocks = ext_codebook(orig_payload, ncodes)[oidx]
            oidx = np.where(oob, 0, oidx)
        else:
            old_blocks = ocb[oidx]
            oob = None
        # block raster order = grid raster order
        if mips == 'auto' and not retrain:
            if np.array_equal(old_blocks, blocks0):
                res.info['mode'] = 'unchanged'
                res.codebook = ocb.copy()
                return bytes(orig_payload[:lay.total])
    else:
        oob = None
    if retrain:
        ocb = oidx = oob = None
    cb, idx, info = vq_quantize(blocks0, ncodes, pix, ocb, oidx, reserve=reserve, seed=seed, force_changed=oob)
    res.info.update(info)
    res.codebook = cb
    gh = gw = lay.w // 2
    grids = [idx.reshape(gh, gw)]
    if len(lay.levels) > 1:
        fcb = _feat(cb, pix)
        rg = _quantised_rgba(rgba, pix)
        for _ in range(len(lay.levels) - 1):
            rg = box_down(rg)
            wd = rgba_to_words(rg, pix)
            bl = _vq_words_to_blocks(wd)
            j, _d = _assign(_feat(bl, pix), fcb)
            lw = rg.shape[1]
            g = max(1, lw // 2)
            grids.append(j.reshape(g, g))
    parts = [cb.astype('<u2').tobytes(), pre]
    for i in range(len(lay.levels) - 1, -1, -1):
        parts.append(_write_indices(grids[i]))
    parts.append(post)
    return b''.join(parts)


# ------------------------------------------------------------ PNG helpers
def to_png(rgba, path):
    from PIL import Image
    Image.fromarray(np.asarray(rgba, np.uint8), 'RGBA').save(path)


def from_png(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert('RGBA')).copy()


# ------------------------------------------------------------ CLI
def _cli(argv):
    import argparse
    ap = argparse.ArgumentParser(description='decode/encode PVR textures')
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('decode', help='PVR file or raw payload -> PNG')
    d.add_argument('src')
    d.add_argument('png')
    d.add_argument('--raw', nargs=4, metavar=('PIX', 'DAT', 'W', 'H'), type=lambda s: int(s, 0))
    d.add_argument('--pvp')
    d.add_argument('--level', type=int, default=0)
    e = sub.add_parser('encode', help='PNG -> same-size replacement of an existing texture')
    e.add_argument('png')
    e.add_argument('original')
    e.add_argument('out')
    e.add_argument('--raw', nargs=4, metavar=('PIX', 'DAT', 'W', 'H'), type=lambda s: int(s, 0))
    e.add_argument('--pvp')
    e.add_argument('--retrain', action='store_true')
    i = sub.add_parser('info', help='describe a PVR file')
    i.add_argument('src')
    a = ap.parse_args(argv)
    if a.cmd == 'info':
        f = parse_file(open(a.src, 'rb').read())
        print(f)
        if f:
            print('expected payload', data_size(f.pix, f.dat, f.w, f.h), 'file payload', f.data_len)
        return 0
    kw = {}
    if a.raw:
        kw = dict(zip(('pix', 'dat', 'w', 'h'), a.raw))
    pal = parse_pvp(open(a.pvp, 'rb').read()) if a.pvp else None
    if a.cmd == 'decode':
        img = decode(open(a.src, 'rb').read(), palette=pal, level=a.level, **kw)
        to_png(img, a.png)
        return 0
    img = from_png(a.png)
    orig = open(a.original, 'rb').read()
    out = encode(img, original=orig, palette=pal, retrain=a.retrain, **kw)
    open(a.out, 'wb').write(out)
    return 0


if __name__ == '__main__':
    sys.exit(_cli(sys.argv[1:]))
