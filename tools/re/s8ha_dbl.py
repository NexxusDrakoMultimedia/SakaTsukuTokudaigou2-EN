"""s8ha: list EVENT.BIN English records that contain two or more blanks in a row (blank-run candidates for the align cave)."""
import json, sys
n = 0
for line in open('translation/FLOW_PRG__EVENT.BIN.jsonl', encoding='utf-8'):
    r = json.loads(line)
    en = r.get('en') or ''
    if '  ' in en:
        n += 1
        if n <= 40:
            print(r['id'], repr(en[:100]))
print(n)
