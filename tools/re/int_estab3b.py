"""Integrator: second pass of int_estab3.py: records of FLOW_PRG/ESTABLIS.BIN with the same ja as an already fixed record
get the same en (the DB keeps twin records, winwidth merges them by ja)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import translib as T
path = os.path.join('translation', 'FLOW_PRG__ESTABLIS.BIN.jsonl')
recs = [(l, json.loads(l) if l.strip() else None) for l in open(path, encoding='utf-8', newline='')]
good = {}
for l, r in recs:
    if r and '%m' in r['ja'] and r['en'].count('\n') == 3 and r['en'].startswith(('Discounted', 'Upgrade the', 'Adding a', 'Removal', 'Sponsor', 'Changing', 'Floodlights')):
        good[r['ja']] = r
out = []; n = 0
for l, r in recs:
    if r and r['ja'] in good and r['en'] != good[r['ja']]['en'] and r['en'].count('\n') >= 4:
        g = good[r['ja']]
        assert len(g['en'].encode('cp932')) + 1 <= r['max_bytes'], r['id']
        r['en'] = g['en']
        l = json.dumps(r, ensure_ascii=False, separators=(',', ':')) + ('\n' if l.endswith('\n') else '')
        n += 1
        print('fixed', r['id'])
    out.append(l)
T.write_atomic(path, ''.join(out))
print('edited', n)
