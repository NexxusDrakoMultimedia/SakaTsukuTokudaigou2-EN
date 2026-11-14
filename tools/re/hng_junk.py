"""hng: records whose English is a placeholder ('-', 'x', ...) or that sit in an orphan slot whose Japanese looks like binary data decoded as cp932
(rare kanji only).  usage: hng_junk.py [SOURCE-substring]"""
import glob, json, os, sys
from collections import Counter
src = sys.argv[1] if len(sys.argv) > 1 else ''
cnt = Counter(); rows = []
for p in sorted(glob.glob(os.path.join('translation', '*.jsonl'))):
    if src not in p:
        continue
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        en = r.get('en') or ''
        if en.strip() in ('-', '--', '.', '?', '*', '/') or (len(en) <= 2 and r.get('orphan')):
            cnt[os.path.basename(p)] += 1
            rows.append((r['id'], r.get('max_bytes'), r['ja'], en, r.get('ctx'), r.get('skip')))
for r in rows[:80]:
    print(r)
print(len(rows), 'rows'); print(cnt.most_common(30))
