"""pol: list the town short records (tbl@43858) whose English contains a space, hyphen or dot (they make odd club-name cuts).
python -I -X utf8 tools/re/pol_list.py"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def recs():
    with open(os.path.join(ROOT, 'translation', 'FLOW_PRG__HOMETOWN.BIN.jsonl'), encoding='utf-8') as fh:
        for i, line in enumerate(fh):
            r = json.loads(line)
            if 'tbl@43858[' in (r.get('ctx') or ''):
                yield r
if __name__ == '__main__':
    n = 0
    for r in recs():
        en = r.get('en') or ''
        if any(c in en for c in ' -.'):
            n += 1
            print(r['id'], r['ctx'], r['ja'], repr(en), r.get('max_bytes'))
    print(n)
