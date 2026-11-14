"""sk2_money_texts.py : print every %m record (id, en) and flag suspicious wording: stray 'Y' prefix, 'bn', 'M ', 'K ', decimals, 'million', 'yen' next to %m."""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
n = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        en = r.get('en') or ''
        if '%m' not in en:
            continue
        n += 1
        flags = []
        if re.search(r'Y%m|Y\s*%m|%m\s*(bn|M\b|K\b|million|billion|yen)', en, re.I):
            flags.append('WESTERN?')
        if re.search(r'\bY\d|\bY[0-9.,]+(bn|M|K)', en):
            flags.append('LITERAL-Y')
        if re.search(r'%m\s*Oku|%m\s*Man', en):
            flags.append('UNIT-DOUBLED')
        print('%s %s | %s' % (r.get('id'), ','.join(flags), en.replace('\n', ' / ')))
print('total', n, file=sys.stderr)
