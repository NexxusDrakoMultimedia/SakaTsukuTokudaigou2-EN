"""skd_ids2: list the real ids inside the ranges of the checklist and the ids it does not mention.  Read-only."""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
groups = json.load(open(os.path.join(ROOT, 'build', 'art', 'groups.json'), encoding='utf-8'))['groups']
text = open(os.path.join(ROOT, 'docs', 'playtest-checklist.md'), encoding='utf-8').read()
sec = text.split('## 5.')[1].split('## 6.')[0]
for l in sec.splitlines():
    if not re.match(r'\| [1-7] ', l):
        continue
    n = int(l[2]); g = set(groups[n - 1]['ids']); cell = l.split('|')[3]; ment = set()
    for m in re.finditer(r'\b(\d{5})(?:-(\d{5}))?', cell):
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        if b > a:
            print(n, m.group(0), '-> real ids', sorted(i for i in g if a <= int(i) <= b))
        ment.update('%05d' % v for v in range(a, b + 1))
    print(n, 'unmentioned', sorted(g - ment))
print([ (i,) for i in ['03570','03571'] if any(i in g['ids'] for g in groups)])
