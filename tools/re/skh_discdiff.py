"""skh (skeptic of the hang owner): byte-level diff of two built trial discs, file by file.

usage: skh_discdiff.py A B [--files PATTERN] [--min N]
  A, B are trial disc names (build/trial/NAME/NAME.gdi).  For every file present in both: same size?  differing byte ranges
  (merged when closer than 8 bytes).  Prints one line per changed file and, for the files that are not whole-file texture
  replacements, the ranges, so that an unexplained change (not a money hook, composer, cave or text) can be spotted.
Read-only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D            # noqa: E402


def load(name):
    src = D.Source(os.path.join(ROOT, 'build', 'trial', name), name)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    return src, files


def ranges(a, b, gap=8):
    out = []
    n = min(len(a), len(b))
    i = 0
    # coarse skip with 4 KiB blocks, then byte scan
    while i < n:
        if a[i:i + 4096] == b[i:i + 4096] and i + 4096 <= n:
            i += 4096
            continue
        end = min(i + 4096, n)
        for j in range(i, end):
            if a[j] != b[j]:
                if out and j - out[-1][1] <= gap:
                    out[-1][1] = j + 1
                else:
                    out.append([j, j + 1])
        i = end
    if len(a) != len(b):
        out.append([n, max(len(a), len(b))])
    return out


def main(argv):
    na, nb = argv[1], argv[2]
    pat = None
    if '--files' in argv:
        pat = argv[argv.index('--files') + 1].upper()
    sa, fa = load(na)
    sb, fb = load(nb)
    only_a = sorted(set(fa) - set(fb))
    only_b = sorted(set(fb) - set(fa))
    print('files only in %s: %s' % (na, only_a[:10]))
    print('files only in %s: %s' % (nb, only_b[:10]))
    nchg = 0
    for p in sorted(set(fa) & set(fb)):
        if pat and pat not in p:
            continue
        ra, rb = fa[p], fb[p]
        if ra.size == rb.size and ra.lba == rb.lba:
            pass
        da = sa.read(ra.lba, ra.size)
        db = sb.read(rb.lba, rb.size)
        if da == db and ra.lba == rb.lba:
            continue
        nchg += 1
        rg = ranges(da, db)
        tot = sum(e - s for s, e in rg)
        print('%-34s size %d/%d lba %d/%d  ranges %d  bytes %d' % (p, ra.size, rb.size, ra.lba, rb.lba, len(rg), tot))
        if '--quiet' not in argv and (len(rg) <= 400 or pat):
            for s, e in rg[:400]:
                print('      %#08x-%#08x (%d)' % (s, e, e - s))
    print('changed files: %d' % nchg)


if __name__ == '__main__':
    main(sys.argv)
