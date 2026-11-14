"""l10 ctx patterns: bytes of ctx by pattern in the WORKING form (read-only)."""
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pat = collections.Counter()
cnt = collections.Counter()
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    for line in open(p, encoding='utf-8'):
        c = json.loads(line).get('ctx')
        if not isinstance(c, str):
            continue
        k = re.sub(r'[0-9a-f]+(?=[\]/@ \[.]|$)', '#', c)
        k = re.sub(r'(?<=[=@\[])[0-9a-f.]+', '#', k)
        pat[k] += len(c)
        cnt[k] += 1
for k, v in pat.most_common(25):
    print('%10d %7d %s' % (v, cnt[k], k))
