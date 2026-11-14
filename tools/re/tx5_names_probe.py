"""tx5: how many BCAST name-clip readings are hiragana / half-width katakana, and how many hw ones already have English in the DB.
python -I -X utf8 tools/re/tx5_names_probe.py"""
import os, sys, json, glob, re, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
lex = collections.defaultdict(collections.Counter)
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    if 'BCAST' in p:
        continue
    for ln in open(p, encoding='utf8'):
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get('en') and re.fullmatch(r'[｡-ﾟ]+', r['ja']):
            lex[r['ja']][r['en']] += 1
print('hw lexicon', len(lex))
recs = [json.loads(l) for l in open(os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl'), encoding='utf8')]
byclip = collections.defaultdict(list)
for r in recs:
    m = re.match(r'clip (name\\\S+) seg (\d+)/', r['ctx'])
    if m:
        byclip[m.group(1)].append(r)
kinds = collections.Counter()
miss = []
for clip, rs in byclip.items():
    s0 = rs[0]['ja']
    if re.fullmatch(r'[ぁ-ゖー]+', s0):
        kinds['hira'] += 1
    elif re.fullmatch(r'[｡-ﾟ]+', s0):
        kinds['hw'] += 1
        if s0 in lex:
            kinds['hw_in_lex'] += 1
        else:
            miss.append(s0)
    else:
        kinds['other'] += 1
        print('other', clip, [x['ja'] for x in rs])
print(kinds)
print(miss[:60])
ex = [(k, lex[k].most_common(1)[0][0]) for k in list(lex)[:30]]
print(ex)
