"""skp: list exact-duplicate town short forms with their Japanese names and table gaps (same-prefecture ones are close together)
    python -I -X utf8 tools/re/skp_dups2.py"""
import json, os, re
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rows = {}
for l in open(os.path.join(ROOT, 'translation', 'FLOW_PRG__HOMETOWN.BIN.jsonl'), encoding='utf-8'):
    if not l.strip(): continue
    r = json.loads(l); m = re.search(r'tbl@43858\[(\d+)/1270\]', r.get('ctx') or '')
    if m: rows[int(m.group(1))] = (r['ja'], r['en'])
g = defaultdict(list)
for k, (ja, en) in rows.items(): g[en].append((k, ja))
for en, v in sorted(g.items()):
    if len(v) > 1 and len({j for _, j in v}) > 1:
        print(repr(en), v)
