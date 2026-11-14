"""Deterministic self-test for tools/bzlib.py and tools/overlay.py.

    python -I -X utf8 tools/test_bzlib.py [--full]

Synthetic tests always run.  Tests against extracted/ run when it exists
(--full: re-encode and header-rebuild every member on the disc).
"""
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bzlib      # noqa: E402
import overlay    # noqa: E402

ROOT = os.path.dirname(HERE)
EXTRACTED = os.path.join(ROOT, 'extracted')
fails = []
passes = 0


def check(cond, msg):
    global passes
    if cond:
        passes += 1
    else:
        fails.append(msg)
        print('FAIL:', msg)


# --- independent reference decoders (transcribed from the game's code, written
# --- in a deliberately different style from bzlib) -------------------------
def ref_bz(src):
    out = bytearray()
    pos = 0
    while True:
        fl = src[pos]
        pos += 1
        for bit in range(8):
            if (fl >> bit) & 1:
                out.append(src[pos])
                pos += 1
                continue
            b = src[pos]
            pos += 1
            if b >= 0x80:
                ln, d = (b & 7) + 2, 16 - ((b >> 3) & 15)
            else:
                b2 = src[pos]
                pos += 1
                if b2 == 0:
                    return bytes(out), pos
                ln, d = b2 + 1, 128 - b
            for _ in range(ln):
                out.append(out[len(out) - d])


def ref_bzw(src):
    out = bytearray()
    pos = 0
    while True:
        fl = src[pos] * 256 + src[pos + 1]
        pos += 2
        for bit in range(16):
            if (fl >> bit) & 1:
                out += src[pos:pos + 2]
                pos += 2
                continue
            lo, hi = src[pos], src[pos + 1]
            pos += 2
            if hi == 0:
                return bytes(out), pos
            for k in range(hi + 1):
                s = len(out) - 512 + lo * 2
                out += out[s:s + 2]


def corpus():
    r = random.Random(0x5A4B)
    c = {'empty': b'', 'one': b'A', 'two': b'AB', 'zeros': bytes(5000),
         'run': b'\xAA' * 1000 + b'xyz', 'rand': bytes(r.randrange(256) for _ in range(3000)),
         'abab': b'ab' * 700, 'text': (b'GBIX\x08\0\0\0 PVRT hello hello hello world ' * 200),
         'sjis': ('今回の優勝は、私のサッカー人生での\n'
                  '最大の栄光になるでしょうね。' * 50).encode('cp932')}
    lowent = bytearray()
    for _ in range(6000):
        lowent.append(r.choice(b'\0\0\0\1\2\3\x80\xff'))
    c['lowent'] = bytes(lowent)
    blk = bytes(r.randrange(256) for _ in range(128))
    c['dist128'] = blk * 10
    blk = bytes(r.randrange(256) for _ in range(512))
    c['dist512'] = blk * 6
    c['len256'] = b'\x01\x02\x03\x04' + b'\x07' * 700
    return c


def test_crc():
    check(bzlib.crc16(b'123456789') == 0x906E, 'crc16 check value (CRC-16/X-25 of "123456789" = 0x906E)')
    check(bzlib.crc16(b'') == 0, 'crc16 of empty')


def test_handmade_streams():
    # flag bits LSB first: 1,1,1 (lits A B C), 0 (match), 0 (end) -> 0x07
    # 1-byte token: dist 3 => dddd = 13, len 3 => lll = 1  => 1 1101 001 = 0xE9
    s = bytes([0x07]) + b'ABC' + bytes([0xE9]) + b'\x00\x00'
    check(bzlib.decompress_bz(s, 6) == b'ABCABC', 'bz handmade 1-byte token')
    s = bytes([0x07]) + b'ABC' + bytes([127, 4]) + b'\x00\x00'
    check(bzlib.decompress_bz(s, 8) == b'ABCCCCCC', 'bz handmade overlap 2-byte token')
    s = bytes([0x03]) + b'AB' + bytes([5, 0])
    check(bzlib.decompress_bz(s, 2) == b'AB', 'bz end marker is b2==0 regardless of b1')
    s = struct.pack('>H', 0x0003) + b'ABCD' + bytes([255, 2]) + b'\x00\x00'
    check(bzlib.decompress_bzw(s, 10) == b'ABCD' + b'CD' * 3, 'bzw handmade overlap')
    s = struct.pack('>H', 0x0003) + b'ABCD' + bytes([0, 0])
    check(bzlib.decompress_bzw(s, 4) == b'ABCD', 'bzw end marker is hi==0')
    for bad in (b'\x07AB', b''):
        try:
            bzlib.decompress_bz(bad, None)
            check(False, 'truncated bz stream must raise')
        except bzlib.DecodeError:
            check(True, '')
    try:
        bzlib.decompress_bz(bytes([0x00, 0xFF]) + b'\0\0', None)
        check(False, 'distance beyond output must raise')
    except bzlib.DecodeError:
        check(True, '')
    try:
        bzlib.decompress_bz(bytes([0x03]) + b'AB' + bytes([5, 0]), 3)
        check(False, 'orig_size mismatch must raise')
    except bzlib.DecodeError:
        check(True, '')


def test_roundtrips():
    cp = corpus()
    for name, plain in cp.items():
        for method in bzlib.METHODS:
            data = plain
            if method == '-bzw-' and len(data) % 2:
                data += b'\0'
            pk = bzlib.compress(data, method)
            back = bzlib.decompress(pk, len(data), method)
            check(back == data, 'round trip %s %s' % (name, method))
            if method == '-bz--':
                r, used = ref_bz(pk)
                check(r == data and used == len(pk), 'ref decoder agrees (bz) %s, consumed all' % name)
            elif method == '-bzw-':
                r, used = ref_bzw(pk)
                check(r == data and used == len(pk), 'ref decoder agrees (bzw) %s, consumed all' % name)
    z = bzlib.compress(bytes(10000), '-bz--')
    check(len(z) < 400, 'zeros compress well bz (%d bytes)' % len(z))
    z = bzlib.compress(bytes(10000), '-bzw-')
    check(len(z) < 400, 'zeros compress well bzw (%d bytes)' % len(z))
    try:
        bzlib.compress(b'abc', '-bzw-')
        check(False, 'bzw odd length must raise')
    except ValueError:
        check(True, '')
    # the encoder must never emit a 2-byte token with b2 == 0 except the end
    # token (that would terminate the real decoder early): covered by the
    # reference decoder consuming exactly the whole stream above.


def test_header():
    plain = b'hello world ' * 30
    rec = bzlib.pack_member('tex.pvr', plain, '-bz--', mtime=0x3B690000)
    check(len(rec) % 4 == 0, 'record padded to 4')
    m = bzlib.parse_member(rec, 0)
    check(m is not None and m.name == 'tex.pvr' and m.method == '-bz--' and m.hdr_crc_ok is True,
          'parse_member of built record, header CRC ok')
    check(m.extract() == plain, 'built member extracts')
    check(m.packed_size == len(m.packed) and m.orig_size == len(plain), 'sizes in header')
    ms, tail = bzlib.parse_archive(rec + b'\0' * 12 + rec)
    check(len(ms) == 2 and tail == len(rec) * 2 + 12, 'parse_archive skips zero padding')


def disc_tests(full):
    if not os.path.isdir(EXTRACTED):
        print('(extracted/ not present: disc tests skipped)')
        return
    p = os.path.join(EXTRACTED, 'GAME', 'BINDFLAG.BIN')
    if os.path.exists(p):
        d = open(p, 'rb').read()
        m = next(bzlib.iter_members(d))
        check(m.name == 'tex.pvr' and m.method == '-bz--' and m.packed_size == 4153 and m.orig_size == 6176,
              'BINDFLAG first member header (tex.pvr -bz-- 4153 -> 6176)')
        plain = m.extract()
        check(plain[:4] == b'GBIX' and plain[4:8] == b'\x08\0\0\0' and b'PVRT' in plain[:0x40],
              'BINDFLAG tex.pvr plaintext starts GBIX .. PVRT')
        check(bzlib.crc16(plain) == m.crc16, 'BINDFLAG tex.pvr crc16')
        check(m.hdr_crc_ok is True, 'BINDFLAG header CRC verifies')
        check(bzlib.build_header(m.name_raw, m.method, m.packed_size, m.orig_size, m.mtime, m.crc16,
                                 hdrlen=m.hdrlen, ext=m.ext, reserved=m.reserved) == m.header,
              'build_header reproduces BINDFLAG first header byte-for-byte')
        check(bzlib.build_header(m.name_raw, m.method, m.packed_size, m.orig_size, m.mtime, m.crc16) == m.header,
              'default ext layout also reproduces it')
    p = os.path.join(EXTRACTED, 'FLOW_PRG', 'MEETING.BIN')
    if os.path.exists(p):
        d = open(p, 'rb').read()
        o = overlay.unpack_overlay(d)
        check(o['load_addr'] == 0x8C2D0000 and o['text_proven'], 'MEETING overlay base 0x8c2d0000 text-proven')
        check(overlay.pack_overlay(o) == d, 'MEETING pack_overlay(unpack_overlay(x)) == x')
        s = overlay.read_cstr(o, 0x8C2D0000 + 0x3f204)
        check(s.decode('cp932').startswith('今回の優勝は'), 'MEETING string at 0x3f204 decodes')
        ptr = struct.unpack_from('<I', d, 0x2366c)[0]
        check(ptr - o['load_addr'] == 0x3f244, 'MEETING pointer table entry 0x2366c -> 0x3f244')

    n_h = n_rt = 0
    files = []
    for root, _, fs in os.walk(EXTRACTED):
        for f in sorted(fs):
            if f in ('BCAST.BIN', '_filelist.tsv'):
                continue
            files.append(os.path.join(root, f))
    files.sort()
    step = 1 if full else 9
    for path in files[::step]:
        if os.path.getsize(path) > 4_000_000 and not full:
            continue
        d = open(path, 'rb').read()
        for k, m in enumerate(bzlib.parse_archive(d)[0]):
            hb = bzlib.build_header(m.name_raw, m.method, m.packed_size, m.orig_size, m.mtime, m.crc16,
                                    hdrlen=m.hdrlen, ext=m.ext, reserved=m.reserved)
            n_h += 1
            if hb != m.header:
                check(False, 'header rebuild mismatch %s @%d' % (path, m.offset))
            if full or k < 3:
                if m.orig_size <= 300_000 and (m.method != '-bzw-' or m.orig_size % 2 == 0):
                    plain = m.extract()
                    rec = bzlib.member_record(m, plain)
                    m2 = bzlib.parse_member(rec, 0)
                    ok = m2 is not None and m2.extract() == plain and m2.name == m.name and m2.hdr_crc_ok
                    n_rt += 1
                    if not ok:
                        check(False, 're-encode round trip failed %s @%d' % (path, m.offset))
    check(n_h > 0, 'some headers rebuilt')
    print('disc: %d headers rebuilt byte-identical, %d members re-encoded and re-parsed (full=%s)' % (n_h, n_rt, full))


def main():
    full = '--full' in sys.argv
    test_crc()
    test_handmade_streams()
    test_roundtrips()
    test_header()
    disc_tests(full)
    print('%d checks passed, %d failed' % (passes, len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
