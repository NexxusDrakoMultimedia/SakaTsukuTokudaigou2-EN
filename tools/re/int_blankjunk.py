"""int: make the junk-orphan blanking PERMANENT in translation/*.jsonl (integrator, after the skh finding).

An orphan record (no pointer) whose English is a placeholder ('-', 'Plot', 'Misc', 'Bow', '?', '----' ...) or one of the known
code-zone overwrites is binary data or machine code that was mis-decoded as cp932.  The build writes every record with a non-empty
'en', so these overwrote data tables and (EVENT#dbf2) code.  The build keeps the original bytes when 'en' is empty, so we set
en = "" and skip = true (same rule as tools/re/skh_mkskip.py, which writes a copy).

usage: int_blankjunk.py [--dry]      changed files are first copied one by one into build/int/db_bak/ (never overwritten).
"""
import glob
import json
import os
import re
import shutil
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PLACEHOLDERS = {'-', 'Plot', 'Misc', 'Bow'}
CODE = {('FLOW_PRG/ENDING.BIN', 0x29fb9), ('FLOW_PRG/NENREP.BIN', 0x162), ('FLOW_PRG/NEWMONTH.BIN', 0x40290),
        ('FLOW_PRG/NEWMONTH.BIN', 0x84ad6), ('FLOW_PRG/NEWS_ED.BIN', 0xb99), ('FLOW_PRG/YOUTH.BIN', 0x4d9e)}


def is_junk(r):
    if not r.get('orphan') or r.get('skip') or not (r.get('en') or '').strip():
        return False
    path, off = r['id'].split('#')
    return r['en'] in PLACEHOLDERS or bool(re.match(r'^[-_.?*/ ]+$', r['en'])) or (path, int(off, 16)) in CODE


def main(argv):
    dry = '--dry' in argv
    bak = os.path.join(ROOT, 'build', 'int', 'db_bak')
    cnt = Counter()
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        out = []
        n = 0
        for ln in open(p, encoding='utf-8', newline=''):
            r = json.loads(ln)
            if is_junk(r):
                r['skip'] = True
                r['en'] = ''
                ln = json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n'
                n += 1
            out.append(ln)
        if n:
            cnt[os.path.basename(p)] = n
            if not dry:
                os.makedirs(bak, exist_ok=True)
                b = os.path.join(bak, os.path.basename(p))
                if not os.path.exists(b):
                    shutil.copy2(p, b)
                with open(p, 'w', encoding='utf-8', newline='') as f:
                    f.writelines(out)
    print('blanked %d records in %d files%s' % (sum(cnt.values()), len(cnt), ' (dry run)' if dry else ''))


if __name__ == '__main__':
    main(sys.argv)
