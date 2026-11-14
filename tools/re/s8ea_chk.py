"""s8ea: non-ASCII / over-budget / control-code check of the English of the given sources (translation/*.jsonl).
usage: s8ea_chk.py SRC [SRC...]     (SRC like FLOW_PRG__EVENT.BIN)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for s in sys.argv[1:]:
    n = bad = 0
    for ln in open(os.path.join(ROOT, 'translation', s + '.jsonl'), encoding='utf-8'):
        r = json.loads(ln)
        en = r.get('en') or ''
        if not en or r.get('skip'):
            continue
        n += 1
        p = []
        if any(ord(c) > 126 or (ord(c) < 32 and c != '\n') for c in en):
            p.append('non-ascii/ctl')
        mb = r.get('max_bytes') or 0
        if mb and len(en.encode('cp932', 'replace')) + 1 > mb and not r.get('slot'):
            p.append('over %d>%d' % (len(en) + 1, mb))
        if p:
            bad += 1
            if bad <= 15:
                print(s, r['id'], p, repr(en[:60]))
    print(s, 'checked', n, 'flagged', bad)
