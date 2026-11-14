"""hrd skeptic: control check over every RAM dump in build/emu.

usage: hrd_sk_ctl.py [DUMP ...]
For each 16 MB dump: slot 1 descriptor / base (is SCDRF loaded?), the member header at 0x8c2fff38 (data CRC16 vs header,
computed with an INDEPENDENT bitwise CRC-16 here and with bzlib.crc16), the list handle 0x8c33b780, the window pointer
0x8c33b76c and its field +0xf8, the error-print gate byte 0x8c230bd6.  Read-only.
"""
import glob
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bzlib            # noqa: E402

BASE = 0x8c000000


def crc16_arc(b):
    """CRC-16/ARC (poly 0xA001 reflected, init 0), bit by bit: independent of bzlib's table."""
    c = 0
    for x in b:
        c ^= x
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c


def w(ram, a):
    return struct.unpack_from('<I', ram, a - BASE)[0]


def main(argv):
    dumps = argv[1:] or sorted(glob.glob(os.path.join(ROOT, 'build', 'emu', '*ram*.bin')))
    for p in dumps:
        ram = open(p, 'rb').read()
        if len(ram) != 0x1000000:
            print('%s: size %#x, skipped' % (os.path.basename(p), len(ram)))
            continue
        arr = w(ram, 0x8c230804)
        s1 = struct.unpack_from('<24I', ram, arr - BASE + 0x60)
        print('%s: slot1 desc %08x base %08x' % (os.path.basename(p), s1[17], s1[18]))
        if s1[17] != 0x8c2ebec4:
            print('    SCDRF not loaded in slot 1')
            continue
        o = 0x8c2fff38 - BASE
        hl = struct.unpack_from('<H', ram, o)[0]
        meth = ram[o + 2:o + 7]
        packed, orig, _mt, crc = struct.unpack_from('<IIIH', ram, o + 7)
        data = ram[o + hl:o + hl + packed]
        # the game's CRC is not CRC-16/ARC: bzlib.crc16 is the one that reproduces the header value of every original member
        print('    member: hdrlen %#x method %r packed %d orig %d header crc16 %04x | data crc16 bzlib %04x (arc %04x, not the game\'s) -> %s' % (
            hl, meth, packed, orig, crc, bzlib.crc16(data), crc16_arc(data), 'OK' if bzlib.crc16(data) == crc else 'STALE'))
        win = w(ram, 0x8c33b76c)
        print('    list handle @8c33b780 = %08x ; window @8c33b76c = %08x ; window+0xf8 = %s ; gate 8c230bd6 = %d' % (
            w(ram, 0x8c33b780), win, '%08x' % w(ram, win + 0xf8) if 0x8c000000 <= win < 0x8cffff00 else '-', ram[0x230bd6]))
        h = w(ram, 0x8c33b780)
        if 0x8c000000 <= h < 0x8cfffff8:
            print('    handle -> %08x %08x (records ptr, count)' % (w(ram, h), w(ram, h + 4)))


main(sys.argv)
