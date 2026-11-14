"""s7n: why a forms.tsv unit of mine was not placed (static checks of tools/re/rfit_gen.gen_candidates).

usage: s7n_unfit.py JA [JA ...]       prints one line per distinct (reason) with the number of records, for the first alternative
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import rfit_gen as G  # noqa: E402
import build_patch as BP  # noqa: E402

by_src = BP.load_tdb('translation')
forms = [f for f in G.parse_forms(os.path.join(ROOT, 'translation', 'refit', 'forms.tsv')) if f['ja'] in sys.argv[1:]]
cands, unfit = G.gen_candidates(by_src, forms, False)
c = collections.Counter((x.rec['ja'], x.new, x.kind, x.free) for x in cands)
print('CANDIDATES (pass the static checks):')
for k, v in sorted(c.items()):
    print('  ', k, v)
u = collections.Counter((rec['ja'], new, why[:110]) for rec, new, why in unfit if rec['ja'] in sys.argv[1:])
print('UNFIT (static):')
for k, v in sorted(u.items()):
    print('  ', k, v)
