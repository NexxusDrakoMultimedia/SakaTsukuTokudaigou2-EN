"""skp: independent odd-shape census of the composed club names (own regexes, not pol_shapes.py), plus table checks, on a built dump.
    python -I -X utf8 tools/re/skp_census.py DUMPDIR [--dup]
Uses the SH-4 simulator's REAL composer (ovf_sim.Composer) for every town+word pair in modes 0 and 1.  Odd = the town part (before/after the cut
dot) contains anything but letters, a lone '.' that follows a letter, any doubled blank/dot, a leading/trailing blank, '-' or a digit."""
import os, re, sys
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ovf_sim as OVF
dump = sys.argv[1]
first = open(os.path.join(OVF.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
comp = OVF.Composer(open(os.path.join(dump, 'FLOW_PRG', 'BPMATCH.BIN'), 'rb').read(), first)
towns, prefs, pool = comp.tables()
bad = [t for t in towns if not re.fullmatch(rb'[A-Za-z]+\.?', t)]
print('towns', len(towns), 'pool', len(pool), 'town forms not letters-only (optionally one trailing dot):', len(bad), bad[:12])
print('pool words with non-letters:', [w for w in pool if not re.fullmatch(rb'[A-Za-z]+', w)][:10])
odd = re.compile(rb'[^A-Za-z]\.|\.\.|  |^ | $|-|[0-9]|\.[A-Za-z]|[A-Za-z]\.[A-Za-z]')
n = 0; cnt = Counter(); mx = 0; ex = []; problems = []
for t in range(1, len(towns) + 1):
    for w in range(len(pool)):
        for mode in (0, 1):
            out, trunc = OVF.check_one(comp, 'town', t, w, mode, towns, prefs, pool, True, problems)
            n += 1; mx = max(mx, len(out))
            if odd.search(out):
                cnt['odd'] += 1
                if len(ex) < 8: ex.append((towns[t - 1], pool[w], out))
            if trunc and mode == 0: cnt['cut'] += 1
print('runs', n, 'problems', len(problems), 'odd', cnt['odd'], 'cut pairs (mode 0)', cnt['cut'], 'of', len(towns) * len(pool), 'longest', mx)
print(ex)
if '--dup' in sys.argv:
    g = defaultdict(list)
    for i, t in enumerate(towns, 1): g[t].append(i)
    d = {k: v for k, v in g.items() if len(v) > 1}
    print('duplicate short forms:', len(d), 'distinct forms', len(g))
