"""s8ea: for an overlay dump pair (A=hsk_full1, B=prop10c): every aligned pointer word (value inside the image) whose pointed
string differs between A and B.  Output: file offset of the pointer word, then the A text and B text.

usage: s8ea_ptrdiff.py NAME [BASE] [--same-ptr]    (NAME like FLOW_PRG__EVENT.BIN)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(ROOT, 'build', 's8ea', 'dump')


def cstr(d, o):
    e = d.find(b'\0', o)
    return d[o:e if e >= 0 else o + 200][:400]


def main(argv):
    name = argv[1]
    base = int(argv[2], 16) if len(argv) > 2 and not argv[2].startswith('--') else 0x8c2d0000
    a = open(os.path.join(D, 'A_' + name), 'rb').read()
    b = open(os.path.join(D, 'B_' + name), 'rb').read()
    n = len(a)
    out = []
    for o in range(0, n - 3, 4):
        va = struct.unpack_from('<I', a, o)[0]
        vb = struct.unpack_from('<I', b, o)[0]
        ina = base <= va < base + n
        inb = base <= vb < base + n
        if not (ina and inb):
            continue
        sa, sb = cstr(a, va - base), cstr(b, vb - base)
        if sa != sb:
            out.append((o, va, vb, sa, sb))
    for o, va, vb, sa, sb in out:
        print('%#x %#x->%#x\n   A %s\n   B %s' % (o, va, vb, sa.decode('cp932', 'replace')[:160].replace('\n', '\\n'),
                                                   sb.decode('cp932', 'replace')[:160].replace('\n', '\\n')))
    print('total', len(out))


if __name__ == '__main__':
    main(sys.argv)
