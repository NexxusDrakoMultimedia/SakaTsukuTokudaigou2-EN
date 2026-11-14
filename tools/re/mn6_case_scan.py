"""mn6_case_scan.py: records whose `en` contains the words Oku / Man (money units) in any case form; prints the distinct contexts.  Read only."""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mn6_db  # noqa: E402

PAT = re.compile(r'(?<![A-Za-z])(Oku|OKU|Man|MAN)(?![A-Za-z])')
cnt = collections.Counter()
ex = {}
for rid, r in mn6_db.records(lambda r: bool(PAT.search(r.get('en') or ''))):
    for m in PAT.finditer(r['en']):
        ctx = r['en'][max(0, m.start() - 6):m.end() + 4].replace('\n', '\\n')
        key = (m.group(1), re.sub(r'\d+', '9', ctx))
        cnt[key] += 1
        ex.setdefault(key, rid)
for (w, ctx), n in sorted(cnt.items(), key=lambda x: (x[0][0], -x[1])):
    print('%4d  %-4s %-30r %s' % (n, w, ctx, ex[(w, ctx)]))
