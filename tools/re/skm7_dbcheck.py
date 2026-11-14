"""skm7_dbcheck.py: every translation/*.jsonl line parses; the 8 skm7 records hold the new text.  Read only."""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bad = n = 0
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    for ln in open(p, encoding='utf-8'):
        if ln.strip():
            n += 1
            try:
                json.loads(ln)
            except ValueError:
                bad += 1
print('records %d, bad lines %d' % (n, bad))
