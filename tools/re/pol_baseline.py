"""pol: the same odd-shape census as pol_shapes.py, but with the reference rule (ovf_sim.reference) on a town table built from a
translation jsonl copy: the 'before' / 'after' number for translation/FLOW_PRG__HOMETOWN.BIN.jsonl without building a disc.
The 1,248 table slots are resolved through the ORIGINAL overlay's pointer table (extracted/FLOW_PRG/HOMETOWN.BIN, file 0x43854, 1-based)
to the record id `#<hex offset>`, so records that two slots share are counted for both.
    python -I -X utf8 tools/re/pol_baseline.py DUMPDIR TOWNS.jsonl     (DUMPDIR only supplies the club-word pool)"""
import json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ovf_sim as OVF
from collections import Counter
dump, jl = sys.argv[1], sys.argv[2]
first = open(os.path.join(OVF.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
comp = OVF.Composer(open(os.path.join(dump, 'FLOW_PRG', 'BPMATCH.BIN'), 'rb').read(), first)
_, _, pool = comp.tables()
orig = open(os.path.join(OVF.ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
byid = {}
for l in open(jl, encoding='utf-8'):
    if l.strip():
        r = json.loads(l); byid[r['id']] = r['en']
towns = []
for k in range(1, 1249):
    off = struct.unpack_from('<I', orig, 0x43854 + 4 * k)[0] - 0x8c2d0000
    towns.append(byid['FLOW_PRG/HOMETOWN.BIN#%x' % off].encode('cp932'))
odd = Counter(); cut = 0
for t in towns:
    for w in pool:
        for wf in (False, True):
            res = OVF.reference(t, w, wf, True)
            if not wf and res != t + b' ' + w: cut += 1
            for s in (b'. .', b'-.', b'..', b' .', b'- '):
                if s in res: odd[s.decode()] += 1
print('reference census of', jl, ': cut pairs (mode 0)', cut, 'odd shapes', dict(odd), 'total', sum(odd.values()))
