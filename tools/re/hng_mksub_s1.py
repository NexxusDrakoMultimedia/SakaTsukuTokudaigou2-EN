"""hng: split build/int/tsub/s1 (the 44 non-ETC_DATA textures that hang) into three subsets u1..u3.

u1 = SCDRF.BIN + SEARCH.BIN (the scout screen sheets); u2 = DRAFT*.ZAR, NEWCON, RECON; u3 = everything else of s1.
Usage: python -I -X utf8 tools/re/hng_mksub_s1.py
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'build', 'int', 'tsub', 's1')
OUT = os.path.join(ROOT, 'build', 'int', 'tsub')


def group(rel):
    p = rel.split('/')
    if len(p) >= 2 and p[0] == 'FLOW_PRG':
        if p[1] in ('SCDRF.BIN', 'SEARCH.BIN'):
            return 'u1'
        if p[1].startswith('DRAFT') or p[1] in ('NEWCON.BIN', 'RECON.BIN'):
            return 'u2'
    return 'u3'


def main():
    for g in ('u1', 'u2', 'u3'):
        d = os.path.join(OUT, g)
        if os.path.isdir(d):
            shutil.rmtree(d)
    counts = {}
    for dp, _dn, fn in os.walk(SRC):
        for f in fn:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, SRC).replace('\\', '/')
            g = group(rel)
            dst = os.path.join(OUT, g, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(full, dst)
            counts.setdefault(g, []).append(rel)
    for g in sorted(counts):
        print(g, len(counts[g]))
        for r in sorted(counts[g]):
            print('   ', r)


if __name__ == '__main__':
    main()
