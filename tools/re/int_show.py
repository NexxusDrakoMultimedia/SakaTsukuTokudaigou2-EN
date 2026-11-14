"""Integrator helper: show the en text of records whose key (12 hex) / id0 is listed in build/integ/ww/width_violations.tsv."""
import json, sys
rows = [l.rstrip('\n').split('\t') for l in open('build/integ/ww/width_violations.tsv', encoding='utf8')][1:]
ids = [r[4] for r in rows]
for l in open('translation/FLOW_PRG__ESTABLIS.BIN.jsonl', encoding='utf8'):
    r = json.loads(l)
    if r['id'] in ids:
        print(r['id'], r['max_bytes'])
        print(r['en'].replace('\n', '|'))
        print(r['ja'].replace('\n', '|'))
