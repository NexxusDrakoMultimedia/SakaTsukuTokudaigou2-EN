"""s8ea: compact view of s8ea_ptrdiff for printable strings: 'offset  A -> B' (one line each), flags non-prefix changes.

usage: s8ea_ptrcmp.py NAME [BASE]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(ROOT, 'build', 's8ea', 'dump')


def cstr(d, o):
    e = d.find(b'\0', o)
    return d[o:e if e >= 0 else o + 200][:200]


def printable(s):
    return len(s) > 0 and all(32 <= c < 127 or c == 10 for c in s)


def main(argv):
    name = argv[1]
    base = int(argv[2], 16) if len(argv) > 2 else 0x8c2d0000
    a = open(os.path.join(D, 'A_' + name), 'rb').read()
    b = open(os.path.join(D, 'B_' + name), 'rb').read()
    n = len(a)
    for o in range(0, n - 3, 4):
        va = struct.unpack_from('<I', a, o)[0]
        vb = struct.unpack_from('<I', b, o)[0]
        if not (base <= va < base + n and base <= vb < base + n):
            continue
        sa, sb = cstr(a, va - base), cstr(b, vb - base)
        if sa == sb or not (printable(sa) and printable(sb)):
            continue
        flag = '' if sb.startswith(sa) or sa.startswith(sb[:3]) else '  <<<'
        print('%#x %s -> %s%s' % (o, sa.decode().replace('\n', '\\n')[:60], sb.decode().replace('\n', '\\n')[:60], flag))


if __name__ == '__main__':
    main(sys.argv)
