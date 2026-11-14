"""hng: list translation records whose en contains a token (default %m); usage hng_grep_m.py [TOKEN] [SOURCE-substring]"""
import glob
import json
import os
import sys

tok = sys.argv[1] if len(sys.argv) > 1 else '%m'
src = sys.argv[2] if len(sys.argv) > 2 else ''
for p in sorted(glob.glob(os.path.join('translation', '*.jsonl'))):
    if src not in p:
        continue
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        if tok in (r.get('en') or ''):
            print(r['id'], '|', r.get('max_bytes'), '|', repr(r['en']), '|', r['ja'][:40].replace('\n', '/'))
