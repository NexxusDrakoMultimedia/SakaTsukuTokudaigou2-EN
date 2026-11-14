"""skp: every record that carries one of the 107 new town forms fits its slot, is letters-only, and has no space/hyphen/dot.  python -I -X utf8 tools/re/skp_slots.py"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
import pol_apply as A
newja = {v[0]: v[1] for v in A.NEW.values()}
n = bad = tight = 0
for fn in sorted(os.listdir(os.path.join(ROOT, 'translation'))):
    if not fn.endswith('.jsonl'): continue
    for l in open(os.path.join(ROOT, 'translation', fn), encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l)
        if 'tbl@' in (r.get('ctx') or '') and r['ja'] in newja:
            n += 1
            if r['en'] != newja[r['ja']] or not re.fullmatch(r'[A-Z][a-z]+', r['en']) or len(r['en'].encode('cp932')) + 1 > r['max_bytes']:
                bad += 1; print('BAD', fn, r['id'], r['en'], r['max_bytes'])
            if len(r['en']) + 1 == r['max_bytes']: tight += 1
print('records', n, 'bad', bad, 'exactly full slot', tight)
