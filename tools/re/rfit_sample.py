"""rfit_sample: print a deterministic sample of the refit candidates by authority (review helper, read-only).

    python -I -X utf8 tools/re/rfit_sample.py [N]
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import rfit_gen as G  # noqa: E402


def main(argv):
    n = int(argv[0]) if argv else 60
    by_src = G.BP.load_tdb('translation')
    forms = G.parse_forms(os.path.join(ROOT, 'translation', 'refit', 'forms.tsv'))
    cands, unfit = G.gen_candidates(by_src, forms, True)
    by = {}
    for c in cands:
        by.setdefault(c.why.split(' (was')[0], {})[c.unit] = c
    rnd = random.Random(7)
    for why, units in sorted(by.items(), key=lambda kv: -len(kv[1])):
        items = sorted(units.values(), key=lambda c: c.unit)
        print('## %s: %d distinct forms' % (why, len(items)))
        if why.startswith(('name from', 'Hepburn')):
            for c in rnd.sample(items, min(n, len(items))):
                print('  %s  %r -> %r  [%s]' % (c.rec['ja'], c.rec['en'], c.new, c.kind))
    print('## unfit (static):')
    seen = set()
    for rec, new, why in unfit:
        k = (rec['ja'], new)
        if k in seen:
            continue
        seen.add(k)
        if len(seen) <= 40:
            print('  %s %r -> %r: %s' % (rec['ja'], rec['en'], new, why[:90]))


if __name__ == '__main__':
    main(sys.argv[1:])
