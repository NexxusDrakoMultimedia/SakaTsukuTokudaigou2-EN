"""s8ft: extract one file from trial discs into a directory (read-only on the discs).
usage: s8ft_extract.py OUTDIR PATH  (PATH like /FLOW_PRG/SCDRF.BIN)  -> OUTDIR/<disc>__<basename>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D  # noqa: E402

DISCS = {'hsk_full1': os.path.join(ROOT, 'build', 'trial', 'hsk_full1'),
         's8e_nofix': os.path.join(ROOT, 'build', 'trial'),
         'prop10c': os.path.join(ROOT, 'build', 'trial')}


def main(argv):
    out, path = argv[1], '/' + argv[2].upper().lstrip('/')
    os.makedirs(out, exist_ok=True)
    for name, d in DISCS.items():
        src = D.Source(d, name)
        _p, _rl, _rs, recs = D.read_filesystem(src)
        for r in recs:
            if not r.isdir and r.path.upper() == path:
                data = src.read(r.lba, r.size)
                fn = os.path.join(out, '%s__%s' % (name, os.path.basename(path)))
                with open(fn, 'wb') as f:
                    f.write(data)
                print(name, r.lba, r.size, fn)
        src.close()


main(sys.argv)
