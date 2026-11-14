"""s8ea: over every overlay of the two discs, list the pointer words that are LITERAL-POOL words (loaded by a `mov.l @(d,pc),rn`)
and whose target moved between hsk_full1 (A) and prop10c (B).  These are relocated strings the CODE addresses directly (possibly
as the base of a stride array: base + idx * stride).

usage: s8ea_allptr.py [FILTER]       writes a table: overlay, literal offset, A value, B value, A string (first 24 bytes), the instruction after the load
Read-only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import discbuild as D            # noqa: E402
from s8ea_diff import load       # noqa: E402

BASE_LOW = 0x8c2d0000


def pick_base(b):
    """overlay load address: the candidate (0x8c2d0000 or 0x8c4d0000) with more aligned words pointing into the image"""
    best, bn = 0x8c2d0000, -1
    for cand in (0x8c2d0000, 0x8c4d0000):
        c = 0
        for o in range(0, min(len(b), 0x40000) - 3, 4):
            v = struct.unpack_from('<I', b, o)[0]
            if cand <= v < cand + len(b):
                c += 1
        if c > bn:
            best, bn = cand, c
    return best


def cstr(d, o):
    e = d.find(b'\0', o)
    return d[o:e if 0 <= e - o < 60 else o + 24]


def main(argv):
    flt = argv[1].upper() if len(argv) > 1 else ''
    sa, fa = load('hsk_full1')
    sb, fb = load('prop10c')
    for p in sorted(fa):
        if not p.startswith('/FLOW_PRG/') or not p.endswith('.BIN') or flt not in p:
            continue
        ra, rb = fa[p], fb[p]
        a = sa.read(ra.lba, ra.size)
        b = sb.read(rb.lba, rb.size)
        if a == b:
            continue
        n = len(a)
        global BASE_LOW
        BASE_LOW = int(os.environ.get("S8EA_BASE", "0"), 16) or pick_base(b)
        # literal words: collect loads
        lits = {}
        for o in range(0, n - 1, 2):
            w = struct.unpack_from('<H', b, o)[0]
            if w >> 12 == 0xD:
                lo = ((o + 4) & ~3) + (w & 0xFF) * 4
                if lo + 4 <= n:
                    lits.setdefault(lo, []).append(o)
        for lo in sorted(lits):
            va = struct.unpack_from('<I', a, lo)[0]
            vb = struct.unpack_from('<I', b, lo)[0]
            if va == vb:
                continue
            if not (BASE_LOW <= va < BASE_LOW + n and BASE_LOW <= vb < BASE_LOW + n):
                continue
            sa_ = cstr(a, va - BASE_LOW)
            sb_ = cstr(b, vb - BASE_LOW)
            if os.environ.get('S8EA_ONLYDIFF') and sa_ == sb_:
                continue
            ld = lits[lo][0]
            nxt = ' '.join('%04x' % struct.unpack_from('<H', b, ld + 2 + 2 * k)[0] for k in range(5))
            print('%s lit=%#x %#x->%#x A=%r B=%r loadat=%#x next=%s' % (p[10:], lo, va, vb, sa_[:24], sb_[:24], ld, nxt))


if __name__ == '__main__':
    main(sys.argv)
