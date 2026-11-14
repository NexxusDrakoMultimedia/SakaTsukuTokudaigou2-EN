"""s8ea: byte-range diff of hsk_full1 vs prop10c (flat or per-dir layout), file by file.

usage: s8ea_diff.py [--files PATTERN] [--quiet] [--dump DIR PATH]
Read-only.  --dump DIR PATH writes both versions of PATH (A_*, B_*) into DIR.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import discbuild as D            # noqa: E402
from skh_discdiff import ranges  # noqa: E402

T = os.path.join(ROOT, 'build', 'trial')


def load(name):
    d = os.path.join(T, name)
    if not os.path.exists(os.path.join(d, name + ' (Track 1).bin')):
        d = T
    src = D.Source(d, name)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    return src, {r.path.upper(): r for r in recs if not r.isdir}


def main(argv):
    pat = argv[argv.index('--files') + 1].upper() if '--files' in argv else None
    sa, fa = load('hsk_full1')
    sb, fb = load('prop10c')
    if '--dump' in argv:
        i = argv.index('--dump')
        out, p = argv[i + 1], '/' + argv[i + 2].upper().lstrip('/')
        for tag, s, f in (('A', sa, fa), ('B', sb, fb)):
            r = f[p]
            data = s.read(r.lba, r.size)
            fn = os.path.join(out, tag + '_' + p.strip('/').replace('/', '__'))
            open(fn, 'wb').write(data)
            print(fn, len(data))
        return
    print('only hsk:', sorted(set(fa) - set(fb))[:20])
    print('only prop10c:', sorted(set(fb) - set(fa))[:20])
    n = 0
    for p in sorted(set(fa) & set(fb)):
        if pat and pat not in p:
            continue
        ra, rb = fa[p], fb[p]
        da = sa.read(ra.lba, ra.size)
        db = sb.read(rb.lba, rb.size)
        if da == db:
            continue
        n += 1
        rg = ranges(da, db)
        tot = sum(e - s for s, e in rg)
        print('%-34s size %d/%d  ranges %d  bytes %d' % (p, ra.size, rb.size, len(rg), tot))
        if '--quiet' not in argv:
            for s, e in rg[:600]:
                print('      %#08x-%#08x (%d)' % (s, e, e - s))
    print('changed files: %d' % n)


if __name__ == '__main__':
    main(sys.argv)
