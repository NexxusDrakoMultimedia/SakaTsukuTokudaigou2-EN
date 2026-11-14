"""s7t: list jsonl records whose English contains a western money-unit pattern (k / M / x10k / Y%d)."""
import glob, json, re, os
R = re.compile(r'(%[-0-9.]*[ds]\s?0*k\b|\bx10k|\b0k\b|%[-0-9.]*[ds]\s?M\b|Y\s?%[-0-9.]*[ds]|\d\s?k\b|%\w*d\s?k)')
for p in sorted(glob.glob(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/translation/*.jsonl')):
    for l in open(p, encoding='utf8'):
        try: o = json.loads(l)
        except Exception: continue
        en = o.get('en') or ''
        if R.search(en) and 'BCAST' not in o['id'] and 'HELP' not in o['id']:
            print(o['id'], '|', o['ja'][:40].replace('\n', '/'), '|', en[:60].replace('\n', '/'), '|', o.get('max_bytes'))
