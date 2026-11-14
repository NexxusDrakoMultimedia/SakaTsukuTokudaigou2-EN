"""s8fg: extract named files from several discs into build/s8fg/<disc>/ (read-only on discs) and list which differ.
usage: s8fg_extract.py FILE [FILE...]     (FILE like FLOW_PRG/SCDRF.BIN)
discs: orig (repo root tracks), hsk_full1 (build/trial/hsk_full1), s8e_nofix (build/trial), prop10c (build/trial)
"""
import os
import sys
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D  # noqa: E402

DISCS = {
    'orig': (ROOT, None),
    'hsk_full1': (os.path.join(ROOT, 'build', 'trial', 'hsk_full1'), 'hsk_full1'),
    's8e_nofix': (os.path.join(ROOT, 'build', 'trial'), 's8e_nofix'),
    'prop10c': (os.path.join(ROOT, 'build', 'trial'), 'prop10c'),
}


def main(argv):
    names = argv[1:]
    out = os.path.join(ROOT, 'build', 's8fg')
    res = {}
    for dn, (d, n) in DISCS.items():
        src = D.Source(d, n)
        _p, _rl, _rs, recs = D.read_filesystem(src)
        files = {r.path.upper(): r for r in recs if not r.isdir}
        for nm in names:
            r = files.get('/' + nm.upper())
            if r is None:
                print('missing', dn, nm)
                continue
            data = src.read(r.lba, r.size)
            p = os.path.join(out, dn, nm)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as f:
                f.write(data)
            res[(dn, nm)] = data
        src.close()
    for nm in names:
        print(nm)
        for dn in DISCS:
            d = res.get((dn, nm))
            if d is not None:
                print('  %-10s %8d %s' % (dn, len(d), hashlib.md5(d).hexdigest()[:10]))


main(sys.argv)
