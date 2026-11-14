"""tx5 skeptic: quality scan of translation/BCAST__BCAST.BIN.jsonl English."""
import json, re, collections, sys
rows=[json.loads(l) for l in open('translation/BCAST__BCAST.BIN.jsonl',encoding='utf8')]
print(len(rows), rows[0])
en=[r for r in rows if r.get('en')]
print('en',len(en))
bad=collections.Counter()
ex=collections.defaultdict(list)
for r in en:
    t=r['en']
    mb=r.get('max_bytes')
    if re.search(r'[^\x20-\x7e]',t): bad['nonascii']+=1; ex['nonascii'].append(t)
    if re.search(r'[　-鿿＀-￯]',t): bad['jp']+=1; ex['jp'].append(t)
    if mb and len(t.encode('cp932','replace'))>mb: bad['over']+=1; ex['over'].append((len(t),mb,t))
    if '\n' in t: bad['nl']+=1
    if re.search(r'\b(san|sama|kun)\b',t,re.I): bad['honor']+=1; ex['honor'].append(t)
    if '  ' in t.strip(): bad['dblspace']+=1; ex['dblspace'].append(t)
    if t!=t.strip(): bad['ws']+=1
    if re.search(r'\bdummy\b|\?\?',t): bad['q']+=1; ex['q'].append(t)
print(bad)
for k,v in ex.items(): print(k,v[:6])
ctx=collections.Counter(r['ctx'].split(' ')[0] for r in rows); print(ctx.most_common(8))
for r in rows:
    if '水沼' in r['ja'] or '静観' in r['ja']: print(r)
