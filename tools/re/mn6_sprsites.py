"""mn6_sprsites.py: for the sprintf-based money formats (ABROAD FIRE PLNUMSET SELNAT INVEST GAME) find the literal-pool word of libc `sprintf` (0x8c014d80)
that the call of the format uses.  A call site = `mov.l @(d,pc),rF` loading the format address, then (within 12 words) `jsr @rX`; rX is traced back to
its pool load.  Read only.   python -I -X utf8 tools/re/mn6_sprsites.py"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import moneypatch as MP      # noqa: E402
import textdb                # noqa: E402

CASES = {'FLOW_PRG/ABROAD.BIN': (0x2c7f4, 0x2c804), 'FLOW_PRG/FIRE.BIN': (0x205a4, 0x205b4), 'FLOW_PRG/PLNUMSET.BIN': (0x34fdc, 0x34fec),
         'FLOW_PRG/SELNAT.BIN': (0x1cbec, 0x1cbfc), 'FLOW_PRG/INVEST.BIN': (0x110ac, 0x110c4, 0x110d8), 'FLOW_PRG/GAME.BIN': (0x1a9b90, 0x1a9b98, 0x1a9ba0, 0x1a9b88),
         'FLOW_PRG/G_INCOME.BIN': (0x266dc,)}


def hw(d, o):
    return d[o] | d[o + 1] << 8


def pt(d, o):
    return ((o + 4) & ~3) + (hw(d, o) & 0xFF) * 4


for rel, offs in CASES.items():
    d = MP.read_extracted(rel)
    base = textdb.load_image(rel).base
    want = {base + o for o in offs}
    for o in range(0, len(d) - 2, 2):
        if (hw(d, o) >> 12) != 0xD:
            continue
        t = pt(d, o)
        if t + 4 > len(d) or struct.unpack_from('<I', d, t)[0] not in want:
            continue
        fmtva = struct.unpack_from('<I', d, t)[0]
        # the call: first jsr within 14 words
        for k in range(o + 2, o + 30, 2):
            w = hw(d, k)
            if (w & 0xF0FF) == 0x400B:
                rx = (w >> 8) & 15
                src = None
                for j in range(k - 2, max(0, k - 900), -2):
                    wj = hw(d, j)
                    if (wj >> 12) == 0xD and ((wj >> 8) & 15) == rx:
                        src = j
                        break
                if src is not None:
                    p = pt(d, src)
                    print('%-24s fmt %#x ld@%#x jsr@%#x  pool@%#x = %08x' % (rel.split('/')[-1], fmtva - base, o, k, p, struct.unpack_from('<I', d, p)[0]))
                break
