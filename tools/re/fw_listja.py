"""fw_listja.py SOURCE [N]: first N message-like translation records (ja has full-width kana, length >= 8) of one source file,
id + ja + en (read-only helper of the field-width study)."""
import json
import sys

p = 'translation/%s.jsonl' % sys.argv[1].replace('/', '__')
n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
c = 0
for ln in open(p, encoding='utf8'):
    r = json.loads(ln)
    ja = r['ja']
    if len(ja) >= 8 and any('ぁ' <= ch <= 'ヿ' for ch in ja) and not r.get('fmt') and not r.get('orphan'):
        print(r['id'][-9:], '|', ja.replace('\n', '/')[:90], '|', r['en'].replace('\n', '/')[:60])
        c += 1
        if c >= n:
            break
