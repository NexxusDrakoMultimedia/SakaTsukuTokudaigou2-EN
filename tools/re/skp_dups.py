"""skp: do the 107 new town short forms create new duplicate forms (compared with the old forms)?  python -I -X utf8 tools/re/skp_dups.py DUMPDIR"""
import os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ovf_sim as OVF, pol_apply as A
from pol_old import OLD
dump = sys.argv[1]
first = open(os.path.join(OVF.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
comp = OVF.Composer(open(os.path.join(dump, 'FLOW_PRG', 'BPMATCH.BIN'), 'rb').read(), first)
towns = comp.tables()[0]
ok = 0
oor = [k for k in A.NEW if k >= len(towns)]
print("keys beyond the composer table:", oor)
for k, (ja, new) in [(k, v) for k, v in A.NEW.items() if k < len(towns)]:
    if towns[k] != new.encode(): print('MISMATCH idx', k, towns[k], new)
    else: ok += 1
print('table entries equal to pol_apply.NEW:', ok, 'of', len(A.NEW))
def dups(tb):
    g = defaultdict(list)
    for i, t in enumerate(tb, 1): g[t.rstrip(b'.')[:7]].append(i)
    return sum(1 for v in g.values() if len(v) > 1), sum(len(v) for v in g.values() if len(v) > 1)
old = list(towns)
for k in [k for k in A.NEW if k < len(towns)]: old[k] = OLD[k][1].encode()
def exact(tb):
    g = defaultdict(list)
    for i, t in enumerate(tb, 1): g[t].append(i)
    return {k: v for k, v in g.items() if len(v) > 1}
eo, en = exact(old), exact(towns)
print('exact dup groups old', len(eo), 'new', len(en))
newonly = {k: v for k, v in en.items() if k not in eo}
print('new-only dup groups:', len(newonly))
for k, v in list(newonly.items())[:20]: print('  ', k, v, [OLD[i][0] if i in OLD else '' for i in v])
