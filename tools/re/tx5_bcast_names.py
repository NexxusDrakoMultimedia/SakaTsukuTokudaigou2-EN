"""tx5: show the segments of the 'name' clips of BCAST.BIN.  python -I -X utf8 tools/re/tx5_bcast_names.py [N]"""
import os, sys, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textfmt_bcast as B

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
rows = B.read_headers()
shown = 0
pref = collections.Counter()
nseg = collections.Counter()
for sec, h in rows:
    name, segs = B.header_segments(h)
    if not name.startswith('name'):
        continue
    stem = name.split('\\')[1].rsplit('.', 1)[0]
    parts = stem.split('_')
    pref['_'.join(parts[:3])[:12]] += 1
    nseg[len(segs)] += 1
    if shown < N and len(segs) > 1 and shown % 1 == 0:
        print(stem, [(hex(o), s, r.decode('cp932', 'replace')) for o, s, r in segs])
        shown += 1
print(nseg)
kinds = collections.Counter(p.split('_')[1] if '_' in p else p for p in pref)
print(len(pref), list(pref.items())[:60])
