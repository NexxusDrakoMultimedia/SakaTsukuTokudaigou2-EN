"""pol: how many town short records exceed their slot (len(en)+1 > max_bytes) and which.  python -I -X utf8 tools/re/pol_over.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pol_list import recs
from collections import Counter
rs = list(recs()); over = [r for r in rs if len((r.get('en') or '').encode('cp932', 'replace')) + 1 > r['max_bytes']]
print(len(rs), Counter(r['max_bytes'] for r in rs), len(over))
for r in over[:60]: print(r['ctx'], r['ja'], r['en'], r['max_bytes'])
print(Counter(len(r['en']) for r in rs))
