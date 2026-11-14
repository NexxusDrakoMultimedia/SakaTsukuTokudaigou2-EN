"""s7p_dbnames - for every club-name plate line (Japanese from groups_v3.json) list the English the string tables/DB use
for the same name (translation/*.jsonl, matched after NFKC so half-width kana equal full-width).
usage: s7p_dbnames.py [--all]"""
import json, glob, os, re, sys, unicodedata, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
nk = lambda s: unicodedata.normalize('NFKC', s)
idx = collections.defaultdict(collections.Counter)
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    for line in open(p, encoding='utf8'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        ja = r.get('ja')
        if ja and r.get('en') is not None and len(ja) <= 24 and '\n' not in ja:
            idx[nk(ja)][r['en']] += 1
d = json.load(open(os.path.join(ROOT, 'build', 'art', 'groups_v3.json'), encoding='utf8'))
for pk in d['packages']:
    if pk['key'] not in ('B', 'C', 'D'):
        continue
    for it in pk.get('items', []):
        ja = it.get('ja') or ''
        if int(it['id']) in range(13825, 13839):
            continue
        for part in [x.strip() for x in ja.split('/')]:
            base = nk(part)
            keys = [base, base.replace('代表', ''), base.replace('FC', ''), base.replace('Stars', 'スターズ'), base.replace('Legs.', 'レジェンズ')]
            hit = []
            for k in keys:
                if k in idx:
                    hit.append((k, idx[k].most_common(3)))
            print(it['id'], part, '->', hit[:2] if hit else 'none')
