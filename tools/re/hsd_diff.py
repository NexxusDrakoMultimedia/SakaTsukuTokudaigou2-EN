"""hsd: diff SCDRF.BIN / SEARCH.BIN between original, bis_e and a texture disc.
usage: hsd_diff.py DISCA DISCB FILE   (FILE like FLOW_PRG/SCDRF.BIN); also prints vs extracted/ original.  Read-only."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D

def rd(disc, rel):
    src = D.Source(os.path.join(ROOT, 'build', 'trial', disc), disc)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    r = files['/' + rel.upper()]
    return src.read(r.lba, r.size)

def ranges(a, b, gap=8):
    out = []
    for j in range(min(len(a), len(b))):
        if a[j] != b[j]:
            if out and j - out[-1][1] <= gap:
                out[-1][1] = j + 1
            else:
                out.append([j, j + 1])
    return out

def main(argv):
    a, b, rel = argv[1], argv[2], argv[3]
    A = rd(a, rel); B = rd(b, rel)
    O = open(os.path.join(ROOT, 'extracted', rel), 'rb').read()
    print('sizes', len(A), len(B), len(O))
    print('ranges', a, 'vs', b)
    for lo, hi in ranges(A, B):
        print('  %x..%x (%d)' % (lo, hi, hi - lo))
    print('ranges', a, 'vs original')
    rg = ranges(A, O)
    print(' count', len(rg))
    print('ranges', b, 'vs original')
    rg = ranges(B, O)
    print(' count', len(rg))
    open(os.path.join(ROOT, 'build', 'hsd', rel.replace('/', '_') + '.' + a), 'wb').write(A)
    open(os.path.join(ROOT, 'build', 'hsd', rel.replace('/', '_') + '.' + b), 'wb').write(B)

main(sys.argv)
