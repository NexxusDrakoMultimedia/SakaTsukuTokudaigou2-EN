"""s7n: count en phrases around competition tokens.  usage: s7n_enscan2.py out.txt"""
import json, glob, os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rx = re.compile(r"((?:[A-Z][\w'.-]*\s){0,3}(?:Cup|Match|League|Tournament|Festival|Stage|Championship|Games|Qualif\w*|Finals?|Qualifiers)(?:\s[A-Z][\w'.-]*){0,2})")
c = collections.Counter()
ex = {}
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for ln in open(p, encoding='utf8'):
        if not ln.strip():
            continue
        r = json.loads(ln)
        en = (r.get('en') or '').replace('\n', ' ')
        for m in rx.finditer(en):
            s = m.group(1).strip()
            c[s] += 1
            ex.setdefault(s, r['id'])
with open(sys.argv[1], 'w', encoding='utf8') as fh:
    for s, n in sorted(c.items(), key=lambda kv: kv[0]):
        fh.write('%d\t%s\t%s\n' % (n, s, ex[s]))
print(len(c))
