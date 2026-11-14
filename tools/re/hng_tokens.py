"""hng: compare the printf-style and name tokens of every translated record with the Japanese (ordered), and flag the unusual ones.

usage: hng_tokens.py [SOURCE-substring]
Tokens compared (ordered list): %s %d %D %m %f %% and any other %x, #sname# #YOU# #tkNN# #...#, @X/ and @ colour spans are counted.
Read-only on translation/*.jsonl.
"""
import glob
import json
import os
import re
import sys
from collections import Counter

TOK = re.compile(r'%[A-Za-z%]|#[A-Za-z]+[0-9]*#|#tk\d+#|<br>')
src = sys.argv[1] if len(sys.argv) > 1 else ''
bad = Counter()
n = 0
for p in sorted(glob.glob(os.path.join('translation', '*.jsonl'))):
    if src not in p:
        continue
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        en = r.get('en') or ''
        if not en or r.get('skip'):
            continue
        n += 1
        a, b = TOK.findall(r['ja']), TOK.findall(en)
        if a != b:
            bad[os.path.basename(p)] += 1
            if bad[os.path.basename(p)] <= 6:
                print('%s | ja %s | en %s | %r' % (r['id'], a, b, en[:70]))
print('records with English checked:', n, ' token list differs:', sum(bad.values()))
for k, v in bad.most_common(15):
    print('  %-40s %d' % (k, v))
