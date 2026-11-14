"""List the live tsString windows of a RAM dump with their decoded text (docs/layout-issues.md section 8, measurement recipe).

    python -I -X utf8 tools/re/layout/wintext.py build/emu/<dump>.bin [FILTER]

For every window object (found by its sprite-template copy, like tools/re/font/livewin.py) prints cells (+0x3c, the wrap width:
2*cells-1 half-width characters per line when +0x45 is 1), advance (+0x3e), origin (+0x4a/+0x4c), code count (+0x22) and the codes
decoded (half-width byte, `_` = blank, `\\n` newline, `[xxxx]` = full-width glyph index).  FILTER = substring of the decoded text.
Take the dump while the screen in question (Event list, player card, sponsor list) is up: the window that holds the clipped name
shows its real width and whether the missing letters are in the code array (clip at draw time) or absent (clip at copy time).
Read-only; does not start an emulator.
"""
import os
import struct
import sys

PAT_FULL = struct.pack('<10H', 24, 24, 0, 0, 0, 0, 191, 191, 0, 0)[:16]
PAT_HALF = struct.pack('<8H', 12, 24, 0, 0, 0, 0, 95, 191)


def windows(d):
    i = d.find(PAT_FULL)
    while i >= 0:
        if d[i + 0x14:i + 0x14 + 16] == PAT_HALF and i >= 0x6c:
            o = i - 0x6c

            def g(off, f='B'):
                return struct.unpack_from('<' + f, d, o + off)[0]
            n = g(0x22, 'H')
            p = g(0x30, 'I')
            txt = ''
            if 0x8c000000 <= p < 0x8d000000 and n < 400:
                for c in struct.unpack_from('<%dH' % n, d, p - 0x8c000000):
                    if c & 0x8000:
                        txt += chr(c & 0x7f) if 0x20 <= (c & 0x7f) < 0x7f else '?'
                    elif c & 0x2000:
                        txt += '\\n' if (c & 0xff) == 10 else ('_' if (c & 0xff) == 0x20 else '<%02x>' % (c & 0xff))
                    else:
                        txt += '[%04x]' % c
            yield dict(addr=0x8c000000 + o, cells=g(0x3c), flag45=g(0x45), adv=g(0x3e), x=g(0x4a, 'h'), y=g(0x4c, 'h'), n=n, text=txt)
        i = d.find(PAT_FULL, i + 1)


def main():
    path = sys.argv[1]
    flt = sys.argv[2] if len(sys.argv) > 2 else ''
    with open(path, 'rb') as f:
        d = f.read()
    for w in windows(d):
        if flt in w['text']:
            print('obj %08x cells=%d flag45=%d adv=%d x=%d y=%d n=%d %r' % (
                w['addr'], w['cells'], w['flag45'], w['adv'], w['x'], w['y'], w['n'], w['text']))


if __name__ == '__main__':
    main()
