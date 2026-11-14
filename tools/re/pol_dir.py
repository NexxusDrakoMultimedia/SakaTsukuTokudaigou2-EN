"""pol: show town short records whose ja starts with a direction/up/down/mid kanji, plus -mura/-Is forms.  python -I -X utf8 tools/re/pol_dir.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pol_list import recs
for r in recs():
    ja = r['ja']; en = r.get('en') or ''
    if ja[0] in '北南東西上下中新' or ja.endswith('島') and len(ja) <= 3:
        print(r['ctx'].split('[')[1].split('/')[0], ja, en, r.get('max_bytes'))
