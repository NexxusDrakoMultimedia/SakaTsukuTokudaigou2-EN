"""skeptic: composed club name overflow, DB words vs refit words (cut=2 helper: town[:-2]? as in field-widths 2.3)"""
import json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def rd(p):
    return [json.loads(l) for l in open(os.path.join(ROOT, p), encoding='utf-8') if l.strip()]
towns = [r['en'] for r in rd('translation/FLOW_PRG__HOMETOWN.BIN.jsonl') if 'tbl@43858[' in (r.get('ctx') or '')]
ov = {r['id']: r['en'] for r in rd('translation/refit/FLOW_PRG__AUTOSAVE.BIN.jsonl')}
words, new = [], []
for r in rd('translation/FLOW_PRG__AUTOSAVE.BIN.jsonl'):
    if 'tbl@247a8[' in (r.get('ctx') or ''):
        words.append(r['en']); new.append(ov.get(r['id'], r['en']))
print(len(towns), len(words))
for name, ws in (('old', words), ('refit', new)):
    for cut in (0, 2):
        over = sum(1 for t in towns for w in ws if len(t) - cut + len(w) > 13)
        print(name, 'cut', cut, over, 'of', len(towns) * len(ws), '%.1f%%' % (100.0 * over / (len(towns) * len(ws))), 'max word', max(map(len, ws)))
print(sorted((o, n) for o, n in zip(words, new) if o != n))
