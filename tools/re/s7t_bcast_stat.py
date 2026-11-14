"""s7t: BCAST translation coverage by clip prefix; show untranslated ones containing a keyword."""
import os
import json, re, sys, collections
p = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/translation/BCAST__BCAST.BIN.jsonl'
tot = collections.Counter(); done = collections.Counter(); miss = []
kw = sys.argv[1] if len(sys.argv) > 1 else '放送席'
for l in open(p, encoding='utf8'):
    o = json.loads(l)
    m = re.search(r'clip (\w+)[\\]', o.get('ctx', ''))
    k = m.group(1) if m else '?'
    tot[k] += 1
    if o.get('en'): done[k] += 1
    elif kw in o['ja']: miss.append((o['id'], o['ja'][:60], o.get('ctx', '')[:50], o.get('skip')))
for k in sorted(tot): print(k, done[k], '/', tot[k])
print(len(miss), 'untranslated with', kw)
for x in miss[:15]: print(x)
