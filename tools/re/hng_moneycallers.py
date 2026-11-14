"""hng: list every caller of the money function (the one the jp cave replaces) in the original overlays, with the instructions that
set up the arguments, so that the size of the destination buffer can be judged by eye.

usage: hng_moneycallers.py OVERLAY [OVERLAY ...]     (e.g. EVENT HOMETOWN)   or   --all  (one summary line per call site)
Read-only: reads extracted/ only.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import capstone as cs                                   # noqa: E402
import moneypatch as MP                                 # noqa: E402

md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)


def ins(d, o, base):
    w = struct.unpack_from('<H', d, o)[0]
    i = list(md.disasm(d[o:o + 2], base + o))
    t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
    if w >> 12 == 0xD:
        t += '   ; =%#x' % struct.unpack_from('<I', d, ((o + 4) & ~3) + (w & 0xFF) * 4)[0]
    elif w >> 12 == 9:
        t += '   ; =%#x' % struct.unpack_from('<H', d, o + 4 + (w & 0xFF) * 2)[0]
    return w, t


def find_base(d, off):
    best = None
    for base in range(0x8c2b0000, 0x8cd60000, 0x10000):
        pat = struct.pack('<I', base + off)
        n = 0
        i = d.find(pat)
        while i >= 0:
            if i % 4 == 0:
                n += 1
            i = d.find(pat, i + 1)
        if n and (best is None or n > best[1]):
            best = (base, n)
    return best


def callers(d, fn_off):
    out = []
    fb = find_base(d, fn_off)
    base = fb[0] if fb else 0x8c2d0000
    # direct bsr
    for o in range(0, len(d) - 1, 2):
        w = struct.unpack_from('<H', d, o)[0]
        if w >> 12 == 0xB:
            disp = w & 0xFFF
            if disp & 0x800:
                disp -= 0x1000
            if o + 4 + disp * 2 == fn_off:
                out.append(('bsr', o))
    # literal + jsr
    lits = set()
    pat = struct.pack('<I', base + fn_off)
    i = d.find(pat)
    while i >= 0:
        if i % 4 == 0:
            lits.add(i)
        i = d.find(pat, i + 1)
    for o in range(0, len(d) - 1, 2):
        w = struct.unpack_from('<H', d, o)[0]
        if w >> 12 == 0xD and ((o + 4) & ~3) + (w & 0xFF) * 4 in lits:
            rn = (w >> 8) & 15
            # find the jsr @rn after it
            for p in range(o + 2, min(o + 80, len(d) - 1), 2):
                w2 = struct.unpack_from('<H', d, p)[0]
                if (w2 & 0xF0FF) == 0x400B and ((w2 >> 8) & 15) == rn:
                    out.append(('jsr', p))
                    break
    return sorted(set(out), key=lambda x: x[1]), base


def main(argv):
    show = []
    names = [a for a in argv if not a.startswith('--')]
    if '--all' in argv:
        names = [os.path.basename(r)[:-4] for r in MP.overlay_paths() if r.startswith('FLOW_PRG/')]
    for n in names:
        rel = 'FLOW_PRG/%s.BIN' % n
        d = MP.read_extracted(rel)
        sites = [s for s in MP.find_sites(d, rel) if s['variant'] == 'A']
        for s in sites:
            cl, base = callers(d, s['off'])
            print('== %s: money function at file %#x (load %#x), %d caller(s)' % (n, s['off'], base + s['off'], len(cl)))
            for kind, p in cl:
                lines = [(o,) + ins(d, o, base) for o in range(max(0, p - 0x24), p + 6, 2)]
                print('  %s at %#x (%#x):' % (kind, p, base + p))
                if '--all' in argv:
                    continue
                for o, w, t in lines:
                    print('     %#08x  %s' % (o, t))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
