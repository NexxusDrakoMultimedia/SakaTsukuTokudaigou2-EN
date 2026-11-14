"""ovf_skeptic_count: independent count of town + word pairs over the 13 character limit, from a built dump (usage: DUMPDIR)."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ovf_sim as OVF  # noqa: E402

im = open(os.path.join(sys.argv[1], 'FLOW_PRG', 'BPMATCH.BIN'), 'rb').read()
towns, prefs, pool = OVF.Composer(im).tables()
pairs = len(towns) * len(pool)
for lim in (13, 14, 15):
    print('over %d with blank: %d, without blank: %d, of %d' % (lim, sum(1 for t in towns for w in pool if len(t) + 1 + len(w) > lim),
          sum(1 for t in towns for w in pool if len(t) + len(w) > lim), pairs))
print('max town', max(map(len, towns)), 'max word', max(map(len, pool)))
