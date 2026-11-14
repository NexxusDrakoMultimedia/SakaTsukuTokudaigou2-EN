import json, re, os, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
T, P, W = [], [], []
for l in open(os.path.join(ROOT, 'translation', 'FLOW_PRG__HOMETOWN.BIN.jsonl'), encoding='utf-8'):
    r = json.loads(l); c = r.get('ctx') or ''
    m = re.match(r'tbl@([0-9a-f]+)\[(\d+)/(\d+)\]', c)
    if 'tbl@422c8' in c: W.append(r['en']); continue
    if not m: continue
    if m.group(1) == '43858' or m.group(3) in ('1270', '1268'): T.append(r['en'])
    elif False: W.append(r['en'])
print(len(T), len(W), sorted(W, key=len)[-5:], max(map(len, W)))
tl = collections.Counter(len(t) for t in T)
print(sorted(tl.items()))
ml = max(len(t) for t in T) + 1 + max(map(len, W)); print('max composed', ml)
tot = over = 0
for t in set(T):
    for w in W:
        tot += 1; over += len(t) + 1 + len(w) > 13
print('composed >13 chars: %d of %d' % (over, tot))
