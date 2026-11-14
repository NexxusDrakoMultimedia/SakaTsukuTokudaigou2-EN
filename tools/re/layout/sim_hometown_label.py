"""Execute HOMETOWN.BIN's list-label builder (FUN at 0x8c2d2a50) in the SH-4 simulator (tools/sh4sim.py) to prove what the
Hometown region / prefecture / town lists do with an English string (docs/layout-issues.md section 1).

    python -I -X utf8 tools/re/layout/sim_hometown_label.py [STRING ...]

For each string it prints the text buffer the routine hands to the window constructor (0x8c2dcc5c, called at 0x8c2d2b50)
for (a) the ORIGINAL overlay and (b) the overlay patched by tools/layoutpatch.py.  Nothing here touches the disc or an emulator.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sh4sim  # noqa: E402

BASE = 0x8c2d0000
FN = 0x8c2d2a50
STOP = 0x8c2d2b4e          # the 'mov.l @(..),r3 ; jsr @r3' that passes the finished buffer (r14) to the window constructor
STRLEN = (0x8c014de4, 0x8c014df2)
STRNCPY = (0x8c013294, 0x8c0132c2)
MEMCPY = 0x8c013814        # struct copy helper: r0 bytes from @r2 to @r1 (register convention of the compiler)


def label(ovl, first, text):
    m = sh4sim.Machine()
    m.load(0x8c010000, first)
    m.load(BASE, ovl)
    m.native = [STRLEN, STRNCPY]

    def memcpy(mm):
        for i in range(mm.R[0]):
            mm.mem[(mm.R[1] + i) & 0xFFFFFFFF] = mm.rb(mm.R[2] + i)
    m.ext_ret[MEMCPY] = memcpy
    sp = 0x8cf00000
    sptr = 0x8c900000
    for i, b in enumerate(text + b'\0'):
        m.mem[sptr + i] = b
    m.R[15] = sp
    m.R[4] = sptr
    m.PR = 0x8c000010
    m.run(FN, STOP + 2)
    buf = bytes(m.rb(m.R[14] + i) for i in range(32))
    return buf.split(b'\0')[0]


def main():
    first = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    orig = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
    import layoutpatch
    patched = layoutpatch.patch_hometown(orig)
    words = [w.encode('cp932') for w in (sys.argv[1:] or ['Tohoku', 'Kanto', 'Kansai', 'Kyushu', 'Hokkaido', 'Nara', 'Aioi', 'Okinawa'])]
    words += [x.encode('cp932') for x in ['東北', '関東', '近畿', '北海道', '相生市']]
    for w in words:
        a = label(orig, first, w)
        b = label(patched, first, w)
        print('%-12r original -> %-30r patched -> %r' % (w.decode('cp932'), a.decode('cp932', 'replace'), b.decode('cp932', 'replace')))


if __name__ == '__main__':
    main()
