"""pol: odd-shape census of the composed club names, produced by the REAL patched composer of a built dump (SH-4 simulator).

    python -I -X utf8 tools/re/pol_shapes.py DUMPDIR [--list N]

Runs every town + word pair in modes 0 and 1 and every prefecture + word pair in modes 2 and 3 (143k composer runs, same harness and the same
checks as tools/re/ovf_sim.py --all: any problem is reported and gives exit code 1), then counts the shapes that look wrong:
    '. .'  a cut that landed on a dot or on a blank after a dot ('N. . Topolino')
    '-.'   a cut right after a hyphen ('Minami-. Arpe')
    '..'   two dots
    ' .'   a cut right after a blank ('Tane . Sting')
and the number of cut results.  Exit code 0 only when there are no problems and no odd shapes.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ovf_sim as OVF  # noqa: E402

SHAPES = (b'. .', b'-.', b'..', b' .', b'- ')


def main():
    dump = sys.argv[1]
    nlist = int(sys.argv[sys.argv.index('--list') + 1]) if '--list' in sys.argv else 0
    first = open(os.path.join(OVF.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    im = open(os.path.join(dump, 'FLOW_PRG', 'BPMATCH.BIN'), 'rb').read()
    comp = OVF.Composer(im, first)
    towns, prefs, pool = comp.tables()
    problems = []
    cutn = Counter()
    odd = Counter()
    ex = []
    runs = 0
    for t in range(1, len(towns) + 1):
        for w in range(len(pool)):
            for mode in (0, 1):
                out, trunc = OVF.check_one(comp, 'town', t, w, mode, towns, prefs, pool, True, problems)
                runs += 1
                cutn['town'] += trunc
                for s in SHAPES:
                    if s in out:
                        odd[s.decode()] += 1
                        if len(ex) < nlist:
                            ex.append((towns[t - 1], pool[w], out))
    for p in range(0, 49):
        for w in range(len(pool)):
            for mode in (2, 3):
                out, trunc = OVF.check_one(comp, 'pref', p, w, mode, towns, prefs, pool, True, problems)
                runs += 1
                cutn['pref'] += trunc
                for s in SHAPES:
                    if s in out:
                        odd['pref ' + s.decode()] += 1
    print('dump %s: runs %d, problems %d %s' % (dump, runs, len(problems), problems[:2] or ''))
    print('cut results (modes 0+1 count each pair twice): town %d, pref %d' % (cutn['town'], cutn['pref']))
    print('odd shapes:', dict(odd) or 'none', 'total', sum(odd.values()))
    for e in ex:
        print('  ', e)
    return 0 if not problems and not odd else 1


if __name__ == '__main__':
    sys.exit(main())
