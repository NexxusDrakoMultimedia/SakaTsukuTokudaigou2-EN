"""Read-only: how reliably can ONE function of the statically linked tsString library be found in every overlay?

    python -I -X utf8 tools/re/ptk_famscan.py

Takes the first N bytes of a library function in MEETING.BIN (base 0x8c2d0000), masks every displacement field that depends on the
link address (pc-relative mov.w/mov.l @(disp,pc) = 9nxx/Dnxx, bsr/bra = Bxxx/Axxx, bt/bf(/s) = 89/8B/8D/8F xx; the literal-pool
words are NOT part of the compared bytes), and counts the matches in every FLOW_PRG/ATFIRST image.  The same method is what a
table-driven patcher would use to locate a patch family (tools/moneypatch.py does it with a sha1 of the masked bytes).
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BASE = 0x8C2D0000

FUNCS = [
    ('layout/draw      FUN_8c2de294', 0x8C2DE294, 64),
    ('window ctor      FUN_8c2de988', 0x8C2DE988, 64),
    ('text setter      FUN_8c2de1f4', 0x8C2DE1F4, 64),
    ('string->codes    FUN_8c2ddeea', 0x8C2DDEEA, 64),
    ('string->codes    (24 B head)', 0x8C2DDEEA, 24),
    ('string->codes    (12 B head)', 0x8C2DDEEA, 12),
    ('format expander  FUN_8c2df128', 0x8C2DF128, 64),
    ('money function   (moneypatch)', 0x8C2DDA68, 64),
]


def mask(b):
    o = bytearray(b)
    for i in range(0, len(o) - 1, 2):
        hi = o[i + 1] >> 4
        if hi in (0x9, 0xD, 0xA, 0xB):
            o[i] = 0
            if hi in (0xA, 0xB):
                o[i + 1] &= 0xF0
        elif hi == 0x8 and (o[i + 1] & 0xF) in (0x9, 0xB, 0xD, 0xF):
            o[i] = 0
    return bytes(o)


def main():
    files = sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')) + glob.glob(os.path.join(ROOT, 'extracted', 'ATFIRST', '*.BIN')))
    imgs = {}
    for p in files:
        imgs[os.path.relpath(p, os.path.join(ROOT, 'extracted')).replace('\\', '/')] = open(p, 'rb').read()
    ref = imgs['FLOW_PRG/MEETING.BIN']
    print('%d overlay images searched' % len(imgs))
    for name, addr, n in FUNCS:
        off = addr - BASE
        key = mask(ref[off:off + n])
        hits = {}
        variants = set()
        for k, d in imgs.items():
            found = []
            for o in range(0, len(d) - n, 2):
                if d[o:o + 2] != ref[off:off + 2]:
                    continue
                if mask(d[o:o + n]) == key:
                    found.append(o)
            if found:
                hits[k] = found
        multi = [k for k, v in hits.items() if len(v) > 1]
        print('%-34s head %d B: found in %3d images (%d copies), images with >1 copy: %s' % (name, n, len(hits), sum(len(v) for v in hits.values()), multi))


if __name__ == '__main__':
    main()
