#!/usr/bin/env python
"""FONT.BIN reader/writer, glyph mapping, renderer and PNG contact sheets.

Format and findings: docs/font.md.
Run:  python -I -X utf8 tools/font.py <command> [args]     (see main() below)
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bzlib  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GLYPH_W = GLYPH_H = 24
GLYPH_BYTES = 288          # 24*24 px, 4 bpp, high nibble = left pixel, 0 = ink, 15 = paper
NGLYPH = 0xE40             # 3648
HALF_W, HALF_H = 12, 24
HALF_BYTES = 144           # 12*24 px at 4 bpp
NHALF = 160


# ------------------------------------------------------------------ PNG
def write_png(path, w, h, rows):
    """Gray 8-bit PNG.  rows: list of h bytes-like objects of length w."""
    raw = b''.join(b'\0' + bytes(r) for r in rows)

    def ch(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0))
                + ch(b'IDAT', zlib.compress(raw, 9)) + ch(b'IEND', b''))


def read_png(path):
    """Minimal PNG reader (8-bit gray/RGB/RGBA/gray+alpha, not interlaced).
    Returns (w, h, rows of gray ints)."""
    d = open(path, 'rb').read()
    assert d[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    p = 8
    idat = b''
    w = h = ct = 0
    while p < len(d):
        n, t = struct.unpack('>I4s', d[p:p + 8])
        body = d[p + 8:p + 8 + n]
        if t == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', body)
            assert bd == 8 and il == 0 and ct in (0, 2, 4, 6), 'unsupported PNG'
        elif t == b'IDAT':
            idat += body
        p += 12 + n
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    rows = []
    q = 0
    for _ in range(h):
        f = raw[q]
        cur = bytearray(raw[q + 1:q + 1 + stride])
        q += 1 + stride
        for i in range(stride):
            a = cur[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                cur[i] = (cur[i] + a) & 255
            elif f == 2:
                cur[i] = (cur[i] + b) & 255
            elif f == 3:
                cur[i] = (cur[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 255
        prev = cur
        rows.append([cur[x * ch] for x in range(w)])
    return w, h, rows


# ------------------------------------------------------------------ nibbles
def nibbles(g):
    p = bytearray()
    for b in g:
        p.append(b >> 4)
        p.append(b & 15)
    return p


def pack_nibbles(p):
    return bytes((p[i] << 4) | p[i + 1] for i in range(0, len(p), 2))


# ------------------------------------------------------------------ container
class Font:
    """FONT.BIN.

    glyphs  : 3648 plain 288-byte bitmaps (24x24, 4 bpp)
    packed  : the original packed (-bz- stream) bytes of each glyph; unchanged glyphs
              are written back from here so an unmodified font round-trips byte-exact
    tail    : everything after the glyph data (the 160 half-width 12x24 glyphs, raw)
    """

    def __init__(self, data=None):
        self.glyphs = []
        self.packed = []
        self.tail = b''
        self.hdr = None
        if data is not None:
            self.parse(data)

    @classmethod
    def load(cls, path=None):
        path = path or os.path.join(ROOT, 'extracted', 'FONT.BIN')
        with open(path, 'rb') as f:
            return cls(f.read())

    def parse(self, d):
        n, off0, base, end = struct.unpack_from('<4I', d, 0)
        if off0 != 0x10 or base != 0x10 + 4 * n:
            raise ValueError('unexpected FONT.BIN header')
        offs = list(struct.unpack_from('<%dI' % n, d, 0x10))
        offs.append(end - base)
        self.packed = [bytes(d[base + offs[i]:base + offs[i + 1]]) for i in range(n)]
        self.glyphs = [bzlib.decompress_bz(p, GLYPH_BYTES) for p in self.packed]
        self.tail = bytes(d[end:])
        self.hdr = (n, off0, base, end)
        return self

    def build(self, recompress=False):
        """Rebuild the file.  Glyphs whose bitmap is unchanged reuse their original
        packed bytes (byte-exact); changed/new glyphs go through bzlib.compress_bz;
        recompress=True recompresses everything."""
        n = len(self.glyphs)
        base = 0x10 + 4 * n
        body = bytearray()
        offs = []
        for i, g in enumerate(self.glyphs):
            if len(g) != GLYPH_BYTES:
                raise ValueError('glyph %d has %d bytes' % (i, len(g)))
            offs.append(len(body))
            p = self.packed[i] if i < len(self.packed) else None
            if recompress or p is None or bzlib.decompress_bz(p, GLYPH_BYTES) != g:
                p = bzlib.compress_bz(g)
            body += p
        out = bytearray(struct.pack('<4I', n, 0x10, base, base + len(body)))
        out += struct.pack('<%dI' % n, *offs)
        out += body
        out += self.tail
        return bytes(out)

    # convenience
    def half(self):
        t = self.tail
        return [t[i * HALF_BYTES:(i + 1) * HALF_BYTES] for i in range(NHALF)]

    def set_half(self, i, g):
        assert len(g) == HALF_BYTES
        t = bytearray(self.tail)
        t[i * HALF_BYTES:(i + 1) * HALF_BYTES] = g
        self.tail = bytes(t)

    def set_glyph(self, i, g):
        assert len(g) == GLYPH_BYTES
        self.glyphs[i] = bytes(g)


# ------------------------------------------------------------------ half-width block
def half_index(b):
    """Single byte -> index into the half-width block (game FUN_8c15e9c6/FUN_8c15eca4:
    c-0x20 below 0xa0, else c-0x40).  Bytes 0x20-0x7f -> 0..95, 0xa0-0xdf -> 96..159.
    0x80-0x9f are SJIS lead bytes and never reach this path."""
    if 0x20 <= b < 0x80:
        return b - 0x20
    if 0xA0 <= b <= 0xDF:
        return b - 0x40
    return None


def half_byte(i):
    return i + 0x20 if i < 96 else i + 0x40


# ------------------------------------------------------------------ SJIS -> glyph index
# Transcribed from the game: 1ST_READ.BIN function at 0x8c15e7a0 (library slot 0x8c1593ac);
# the same code is statically linked into the overlays' text engines.
EXTRA_TABLE = [  # u16 table at 0x8c169f04 in 1ST_READ; glyph index = 3530 + position
    0x994e, 0x997a, 0x9b90, 0x9bd4, 0x9c41, 0x9c61, 0x9dd7, 0x9de3, 0x9e65, 0x9e8a, 0x9f86, 0x9fba,
    0xe056, 0xe05f, 0xe1c1, 0xe245, 0xe54d, 0xe555, 0xe777, 0xe7b2, 0x9779, 0xe8f2, 0x9b89, 0x9bbd,
    0x9bc1, 0x9e77, 0xe06b, 0xe78e, 0xe3c4, 0x99dd, 0x9a42, 0x9a6b, 0x9ca8, 0x9cdf, 0x9d58, 0x9d9b,
    0xe079, 0xe0a0, 0xe0f8, 0xe1c9, 0xe345, 0xe6c3, 0xe753, 0xe74f, 0xe75d, 0xe7b3, 0xfab1, 0xe54d,
    0x9df0, 0x9b8f, 0x9dc9]
EXTRA_BASE = 0xDCA         # 3530
FALLBACK = 0x17            # glyph the game uses for unmappable codes


def sjis_to_index(code, nglyph=NGLYPH):
    if code > 0x9890:
        try:
            return EXTRA_BASE + EXTRA_TABLE.index(code)
        except ValueError:
            return FALLBACK
    lead, trail = code >> 8, code & 0xFF
    t = trail - 0x41 if trail >= 0x7F else trail - 0x40
    if lead == 0x88:
        idx = 406 + trail
    elif lead > 0x88:
        idx = (lead - 0x89) * 188 + 659 + t
    else:
        idx = (lead - 0x81) * 188 + t
    if idx < 0 or idx >= nglyph:
        return FALLBACK
    return idx


_INV = None


def _inverse():
    global _INV
    if _INV is None:
        inv = {}
        for lead in range(0x81, 0x99):
            for trail in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
                try:
                    bytes([lead, trail]).decode('cp932')
                except UnicodeDecodeError:
                    continue
                code = (lead << 8) | trail
                i = sjis_to_index(code)
                if i != FALLBACK and i not in inv:
                    inv[i] = code
        for k, code in enumerate(EXTRA_TABLE):
            inv.setdefault(EXTRA_BASE + k, code)
        _INV = inv
    return _INV


def index_to_sjis(i):
    """The (first) valid cp932 code that selects glyph i, or None."""
    return _inverse().get(i)


def index_to_char(i):
    c = index_to_sjis(i)
    return None if c is None else bytes([c >> 8, c & 255]).decode('cp932')


def text_to_glyphs(s):
    """cp932-encode s and walk it as the game's string compiler (overlay FUN_8c2e059e) does:
    returns [('f', glyph_index) | ('h', half_index) | ('c', control byte)].
    (The '#..#' / '@' / '=' escape syntax of the engine is not interpreted here.)"""
    b = s.encode('cp932')
    out = []
    i = 0
    while i < len(b):
        c = b[i]
        if c < 0x21:
            out.append(('c', c))
            i += 1
        elif (0x81 <= c <= 0x9F) or c >= 0xE0:
            if i + 1 >= len(b):
                break
            out.append(('f', sjis_to_index((c << 8) | b[i + 1])))
            i += 2
        else:
            out.append(('h', half_index(c)))
            i += 1
    return out


# ------------------------------------------------------------------ rendering
def blank_canvas(w, h, v=255):
    return [bytearray([v]) * w for _ in range(h)]


def blit(img, x, y, nib, w, h, scale=1):
    for yy in range(h):
        for xx in range(w):
            v = nib[yy * w + xx] * 17
            for sy in range(scale):
                row = img[(y + yy) * scale + sy]
                for sx in range(scale):
                    row[(x + xx) * scale + sx] = v


_DIG = {
    '0': '111101101101111', '1': '010110010010111', '2': '111001111100111', '3': '111001111001111',
    '4': '101101111001001', '5': '111100111001111', '6': '111100111101111', '7': '111001001001001',
    '8': '111101111101111', '9': '111101111001111', 'a': '010101111101101', 'b': '110101110101110',
    'c': '011100100100011', 'd': '110101101101110', 'e': '111100110100111', 'f': '111100110100100',
    'x': '101101010101101', ' ': '000000000000000'}


def label(img, x, y, s, v=0):
    for ch in s:
        pat = _DIG.get(ch.lower(), _DIG[' '])
        for k, bit in enumerate(pat):
            if bit == '1':
                img[y + k // 3][x + k % 3] = v
        x += 4


def render_text(font, s, scale=1, pad=4, line_h=28):
    """Lay out s ('\\n' separates lines) like the game: full-width glyphs advance 24 px,
    half-width glyphs 12 px (fixed).  Returns (w, h, rows)."""
    lines = s.split('\n')
    halves = font.half()
    W = max(sum(24 if k == 'f' else 12 for k, _ in text_to_glyphs(l)) for l in lines) + 2 * pad
    H = line_h * len(lines) + 2 * pad
    img = blank_canvas(W * scale, H * scale)
    for li, l in enumerate(lines):
        x = pad
        y = pad + li * line_h
        for kind, v in text_to_glyphs(l):
            if kind == 'f':
                if v < len(font.glyphs):
                    blit(img, x, y, nibbles(font.glyphs[v]), 24, 24, scale)
                x += 24
            elif kind == 'h':
                if v is not None:
                    blit(img, x, y, nibbles(halves[v]), 12, 24, scale)
                x += 12
            else:
                x += 12
    return W * scale, H * scale, img


def contact_sheet(get, gw, gh, cols, rows, start, scale):
    """get(i) -> nibble list or None.  Index labels (hex of first glyph in the row) at left."""
    mx, my = 30, 2
    cw, ch = gw + 1, gh + 1
    W = mx + cols * cw
    H = my + rows * ch
    img = blank_canvas(W * scale, H * scale, 225)
    for k in range(cols * rows):
        nib = get(start + k)
        if nib is None:
            continue
        blit(img, mx + (k % cols) * cw, my + (k // cols) * ch, nib, gw, gh, scale)
    for r in range(rows):
        label(img, 1, (my + r * ch) * scale + 2, '%04x' % (start + r * cols))
    return W * scale, H * scale, img


SAMPLE = ('サッカークラブをつくろう！\n'
          'Ｊリーグ　プロサッカークラブ育成ゲーム\n'
          '監督　選手　契約　移籍　試合結果　年俸\n'
          'ひらがな カタカナ 漢字 ＡＢＣ１２３\n'
          'Half-width: The quick brown fox 0123456789 ｱｲｳｴｵ')


def make_sheets(font, outdir, scale=2):
    made = []
    per = 32 * 24
    n_all = len(font.glyphs)
    for s0 in range(0, n_all, per):
        n = min(per, n_all - s0)
        rows = (n + 31) // 32
        W, H, img = contact_sheet(lambda i: nibbles(font.glyphs[i]) if i < n_all else None,
                                  24, 24, 32, rows, s0, scale)
        p = os.path.join(outdir, 'full_%04d-%04d.png' % (s0, s0 + n - 1))
        write_png(p, W, H, img)
        made.append(p)
    hg = font.half()
    W, H, img = contact_sheet(lambda i: nibbles(hg[i]) if i < NHALF else None, 12, 24, 32, 5, 0, 3)
    p = os.path.join(outdir, 'half.png')
    write_png(p, W, H, img)
    made.append(p)
    W, H, img = render_text(font, SAMPLE, scale=2)
    p = os.path.join(outdir, 'sample_ja.png')
    write_png(p, W, H, img)
    made.append(p)
    return made


# ------------------------------------------------------------------ edit sheets (PNG import/export)
def export_edit_sheet(font, path, half=False):
    """Raw gray8 sheet without grid: 32 cells per row, cell = glyph size; glyph i at
    (i % 32, i // 32).  0 = ink, 255 = paper (nibble * 17)."""
    gs, gw, gh = (font.half(), 12, 24) if half else (font.glyphs, 24, 24)
    rows = (len(gs) + 31) // 32
    img = blank_canvas(32 * gw, rows * gh, 255)
    for i, g in enumerate(gs):
        blit(img, (i % 32) * gw, (i // 32) * gh, nibbles(g), gw, gh)
    write_png(path, 32 * gw, rows * gh, img)


def import_edit_sheet(font, path, half=False):
    """Read a sheet written by export_edit_sheet (possibly edited) into font; gray is
    quantised to 4 bit (v >> 4).  Returns the number of glyphs that changed."""
    w, h, rows = read_png(path)
    gw, gh = (12, 24) if half else (24, 24)
    n = NHALF if half else len(font.glyphs)
    assert w == 32 * gw and h >= ((n + 31) // 32) * gh, 'sheet size mismatch'
    cur = font.half() if half else font.glyphs
    changed = 0
    for i in range(n):
        x0, y0 = (i % 32) * gw, (i // 32) * gh
        g = pack_nibbles([rows[y0 + y][x0 + x] >> 4 for y in range(gh) for x in range(gw)])
        if g != cur[i]:
            changed += 1
            if half:
                font.set_half(i, g)
            else:
                font.set_glyph(i, g)
    return changed


# ------------------------------------------------------------------ analysis helpers
def is_blank(g):
    return all(b == 0xFF for b in g)


def used_chars_from_translation(tdir=None):
    """Set of non-ASCII characters appearing in translation/*.jsonl 'ja' fields."""
    import glob
    import json
    tdir = tdir or os.path.join(ROOT, 'translation')
    used = {}
    for fn in sorted(glob.glob(os.path.join(tdir, '*.jsonl'))):
        with open(fn, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ja = json.loads(line).get('ja', '')
                except ValueError:
                    continue
                for c in ja:
                    if ord(c) > 0x7F:
                        used[c] = used.get(c, 0) + 1
    return used


def usage_report(font, tdir=None):
    used = used_chars_from_translation(tdir)
    idx_used = {}
    unmapped = {}
    for c, n in used.items():
        try:
            b = c.encode('cp932')
        except UnicodeEncodeError:
            unmapped[c] = n
            continue
        if len(b) == 2:
            i = sjis_to_index((b[0] << 8) | b[1])
            if i == FALLBACK and (b[0] << 8 | b[1]) != index_to_sjis(FALLBACK):
                unmapped[c] = n
            idx_used[i] = idx_used.get(i, 0) + n
    nonblank = [i for i in range(len(font.glyphs)) if not is_blank(font.glyphs[i])]
    unused_nonblank = [i for i in nonblank if i not in idx_used]
    unused_kanji = [i for i in unused_nonblank if i >= 565]
    blank = [i for i in range(len(font.glyphs)) if is_blank(font.glyphs[i])]
    return dict(chars=len(used), idx_used=idx_used, unmapped=unmapped, nonblank=nonblank,
                unused_nonblank=unused_nonblank, unused_kanji=unused_kanji, blank=blank)


# ------------------------------------------------------------------ DPFONT (browser fonts, secondary)
DP_SIZES = {'S18': 18, 'S20': 20, 'S24': 24, 'S26': 26}
DP_COUNT = 7808


def dp_index(code):
    """Cell index inside DPFONT/*.DAT for a two-byte SJIS code (INFERRED, see docs/font.md):
    (lead - 0x81 [lead<=0x9f] or lead - 0xc1) * 188 + trail index (0x7f skipped)."""
    lead, trail = code >> 8, code & 0xFF
    t = trail - 0x41 if trail >= 0x7F else trail - 0x40
    return (lead - (0x81 if lead <= 0x9F else 0xC1)) * 188 + t


def dp_glyph(data, i, size):
    """2 bpp, MSB first, rows padded to whole bytes.  Returns list of rows (values 0..3,
    3 = full ink)."""
    stride = (size * 2 + 7) // 8
    g = data[i * stride * size:(i + 1) * stride * size]
    rows = []
    for y in range(size):
        px = []
        for b in g[y * stride:(y + 1) * stride]:
            px += [(b >> 6) & 3, (b >> 4) & 3, (b >> 2) & 3, b & 3]
        rows.append(px[:size])
    return rows


def dp_sheet(path, data, size, start, cols=40, rows=30):
    W, H = cols * (size + 1), rows * (size + 1)
    img = blank_canvas(W, H, 225)
    for k in range(cols * rows):
        if start + k >= DP_COUNT:
            break
        g = dp_glyph(data, start + k, size)
        x0, y0 = (k % cols) * (size + 1), (k // cols) * (size + 1)
        for y in range(size):
            for x in range(size):
                img[y0 + y][x0 + x] = 255 - g[y][x] * 85
    write_png(path, W, H, img)


def cmd_dpfont(args):
    out = os.path.join(ROOT, 'build', 'font')
    for name, size in DP_SIZES.items():
        fn = os.path.join(ROOT, 'extracted', 'DPFONT', name + 'RM04P.DAT')
        d = _read(fn)
        stride = (size * 2 + 7) // 8
        print(name, len(d), 'bytes; glyph %d bytes; glyphs = %s' % (stride * size, len(d) / (stride * size)))
        dp_sheet(os.path.join(out, 'dp_%s_0000.png' % name), d, size, 0)
        dp_sheet(os.path.join(out, 'dp_%s_1410.png' % name), d, size, 1410)


# ------------------------------------------------------------------ CLI
def _read(path):
    with open(path, 'rb') as f:
        return f.read()


def cmd_info(args):
    fn = args[0] if args else os.path.join(ROOT, 'extracted', 'FONT.BIN')
    d = _read(fn)
    f = Font(d)
    n, off0, base, end = f.hdr
    print('file', fn, len(d), 'bytes')
    print('header: count=%d (0x%x) table@0x%x glyph_data@0x%x half_block@0x%x' % (n, n, off0, base, end))
    print('packed glyph data %d bytes (avg %.1f per glyph); half block %d bytes = %d glyphs of 12x24'
          % (end - base, (end - base) / n, len(f.tail), len(f.tail) // HALF_BYTES))
    blanks = sum(1 for g in f.glyphs if is_blank(g))
    print('full-width glyphs: %d (blank %d, non-blank %d)' % (n, blanks, n - blanks))


def cmd_roundtrip(args):
    ok = True
    for fn in (['extracted/FONT.BIN', 'extracted/ATFIRST/FONT.BIN'] if not args else args):
        p = fn if os.path.isabs(fn) else os.path.join(ROOT, fn)
        d = _read(p)
        f = Font(d)
        b1 = f.build()
        print(fn, 'rebuild (reuse packed): identical =', b1 == d, len(b1), len(d))
        ok &= (b1 == d)
        b2 = f.build(recompress=True)
        g2 = Font(b2)
        same = g2.glyphs == f.glyphs and g2.tail == f.tail
        print(fn, 'recompress all: size %d (orig %d, %+d), decoded glyphs+tail identical = %s, '
              'identical to original file = %s' % (len(b2), len(d), len(b2) - len(d), same, b2 == d))
        ok &= same
    # modified-glyph check
    f = Font(_read(os.path.join(ROOT, 'extracted', 'FONT.BIN')))
    f.set_glyph(3600, bytes((i * 7) & 255 for i in range(GLYPH_BYTES)))
    f.set_half(1, bytes((i * 3) & 255 for i in range(HALF_BYTES)))
    g = Font(f.build())
    ch = g.glyphs[3600] == f.glyphs[3600] and g.half()[1] == f.half()[1]
    others = all(g.glyphs[i] == f.glyphs[i] for i in range(len(g.glyphs)) if i != 3600)
    print('modified glyph write/read back ok =', ch, '; others untouched =', others)
    ok &= ch and others
    print('ROUNDTRIP', 'OK' if ok else 'FAILED')
    return 0 if ok else 1


def cmd_sheets(args):
    out = os.path.join(ROOT, 'build', 'font')
    f = Font.load()
    for p in make_sheets(f, out):
        print(p)


def cmd_sample(args):
    f = Font.load()
    s = args[0] if args else SAMPLE
    out = os.path.join(ROOT, 'build', 'font', 'sample.png')
    W, H, img = render_text(f, s.replace('\\n', '\n'), scale=2)
    write_png(out, W, H, img)
    print(out, W, H)


def cmd_export(args):
    f = Font.load()
    out = args[0] if args else os.path.join(ROOT, 'build', 'font')
    os.makedirs(out, exist_ok=True)
    export_edit_sheet(f, os.path.join(out, 'edit_full.png'))
    export_edit_sheet(f, os.path.join(out, 'edit_half.png'), half=True)
    print('wrote edit_full.png (768x2736, glyph i at col i%32,row i//32) and edit_half.png (384x120)')


def cmd_import(args):
    """import <src FONT.BIN> <full.png|-> <half.png|-> <out FONT.BIN>"""
    src, full, half, out = args
    f = Font(_read(src))
    if full != '-':
        print('full glyphs changed:', import_edit_sheet(f, full))
    if half != '-':
        print('half glyphs changed:', import_edit_sheet(f, half, half=True))
    b = f.build()
    with open(out, 'wb') as fh:
        fh.write(b)
    print('wrote', out, len(b), 'bytes')


def cmd_map(args):
    """map <text>: show how the engine resolves each character."""
    f = Font.load()
    for k, v in text_to_glyphs(args[0]):
        print(k, v, index_to_char(v) if k == 'f' else '')


def cmd_usage(args):
    f = Font.load()
    r = usage_report(f)
    print('distinct non-ASCII chars in translation/*.jsonl ja fields:', r['chars'])
    print('glyph indices used by them:', len(r['idx_used']))
    print('chars that cannot be drawn (not in cp932 or fall back to glyph 23):', len(r['unmapped']),
          ''.join(sorted(r['unmapped']))[:200])
    print('non-blank glyphs:', len(r['nonblank']), '; non-blank but unused by scanned text:',
          len(r['unused_nonblank']), '(of which kanji idx>=565:', len(r['unused_kanji']), ')')
    print('blank glyph slots:', len(r['blank']))


COMMANDS = {'info': cmd_info, 'roundtrip': cmd_roundtrip, 'sheets': cmd_sheets, 'sample': cmd_sample,
            'export': cmd_export, 'import': cmd_import, 'map': cmd_map, 'usage': cmd_usage,
            'dpfont': cmd_dpfont}


def main(argv):
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(__doc__)
        print('commands:', ', '.join(COMMANDS))
        return 2
    r = COMMANDS[argv[1]](argv[2:])
    return r or 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
