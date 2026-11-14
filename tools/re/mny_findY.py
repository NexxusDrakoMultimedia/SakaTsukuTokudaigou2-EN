"""mny_findY.py : list English records that still carry a western money text (Y10M, Y1.5bn, Y30K, 200 million yen ...) in translation/.
    python -I -X utf8 tools/re/mny_findY.py"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import translib as T          # noqa: E402

RX = re.compile(r'Y\s*[\d,.]+\s*(?:k|K|M|bn|T|x10k)?\b|\d[\d,.]* (?:million|billion|trillion) yen|Y%\d*d|%d00M|%d0K|%d0k')
db = T.load_db(T.resolve_path('translation'))
n = 0
for fi, li, r in db.records():
    en = r.get('en') or ''
    if RX.search(en) and not r.get('skip'):
        n += 1
        print('%s\t%s\t%s' % (r['id'], en.replace('\n', '|'), r['ja'].replace('\n', '|')))
print(n, 'records')
