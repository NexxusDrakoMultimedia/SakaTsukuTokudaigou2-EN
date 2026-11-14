"""skd_ids: skeptic check of the ids named in docs/playtest-checklist.md section 5 against build/art/groups.json.
Read-only.  Usage: python -I -X utf8 tools/re/skd_ids.py"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
groups = json.load(open(os.path.join(ROOT, 'build', 'art', 'groups.json'), encoding='utf-8'))['groups']
gid = {}
for i, g in enumerate(groups, 1):
    gid[i] = set(g['ids'])
text = open(os.path.join(ROOT, 'docs', 'playtest-checklist.md'), encoding='utf-8').read()
sec = text.split('## 5.')[1].split('## 6.')[0]
rows = [l for l in sec.splitlines() if re.match(r'\| [1-7] ', l)]
for l in rows:
    n = int(l[2])
    cell = l.split('|')[3]
    ids = set()
    for m in re.finditer(r'\b(\d{5})(?:-(\d{5}))?', cell):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        for v in range(a, b + 1):
            ids.add('%05d' % v)
    unknown = sorted(i for i in ids if i not in gid[n])
    other = sorted(i for i in unknown if any(i in gid[k] for k in gid if k != n))
    print('group', n, 'named', len(ids), 'in group', len(ids) - len(unknown), 'not in group', unknown, 'in other group', other)
    print('   group ids not mentioned:', len(gid[n] - ids))
tex = set()
for dp, dn, fn in os.walk(os.path.join(ROOT, 'translation', 'textures')):
    tex.update(fn)
print('texture files', len(tex), sorted(tex)[:3])
