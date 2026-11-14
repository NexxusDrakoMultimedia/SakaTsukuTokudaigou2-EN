"""mn6_rt.py: does mn6_db.dump(json.loads(line)) reproduce every line of every translation file byte for byte?  Read only."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mn6_db  # noqa: E402

bad = tot = 0
for p in sorted(glob.glob(os.path.join(mn6_db.TRANS, '*.jsonl'))):
    for ln in open(p, encoding='utf-8', newline=''):
        s = ln.rstrip('\r\n')
        if not s.strip():
            continue
        tot += 1
        if mn6_db.dump(json.loads(s)) != s:
            bad += 1
            if bad < 4:
                print(p, s[:150])
print('lines', tot, 'not round-tripping', bad)
