"""s7n: find DB records by regex on en or ja.  usage: s7n_find.py (en|ja) REGEX [maxlen]"""
import json, glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
fld, rx = sys.argv[1], re.compile(sys.argv[2])
ml = int(sys.argv[3]) if len(sys.argv) > 3 else 140
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for ln in open(p, encoding='utf8'):
        if not ln.strip():
            continue
        r = json.loads(ln)
        if rx.search(r.get(fld) or ''):
            print(r['id'], '|', r['ja'].replace('\n', '\n')[:ml], '|', (r.get('en') or '').replace('\n', '\n')[:ml], '|', r.get('max_bytes'), '|', (r.get('ctx') or '')[:45])
