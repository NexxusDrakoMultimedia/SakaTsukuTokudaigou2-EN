"""skeptic scan of translation/refit overlays: charset, caps, consistency (same ja -> same en), capitalisation, DB drift.
read only; prints a report."""
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BAD = set('\\~@=#%<>{}|^`')


def main():
    recs = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl'))):
        for ln in open(f, encoding='utf-8'):
            ln = ln.strip()
            if ln:
                r = json.loads(ln)
                r['_f'] = os.path.basename(f)
                recs.append(r)
    print('records', len(recs))
    db = {}
    for f in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
        for ln in open(f, encoding='utf-8'):
            ln = ln.strip()
            if ln:
                r = json.loads(ln)
                db[r['id']] = r
    bad = collections.Counter()
    by_ja = collections.defaultdict(collections.Counter)
    for r in recs:
        en = r['en']
        if any(ord(c) < 32 or ord(c) > 126 for c in en):
            bad['nonascii'] += 1
            print('NONASCII', r['id'], repr(en))
        if any(c in BAD for c in en):
            bad['badchar'] += 1
            print('BADCHAR', r['id'], repr(en))
        if en != en.strip() or '  ' in en:
            bad['space'] += 1
            print('SPACE', r['id'], repr(en))
        if r['cls'] == 'person' and en and not en[0].isupper():
            bad['lower'] += 1
            print('LOWER', r['id'], repr(en), r['ja'])
        if r['cls'] == 'person' and len(en) > 12:
            bad['len12'] += 1
        d = db.get(r['id'])
        if d is None:
            bad['nodb'] += 1
        elif d['ja'] != r['ja']:
            bad['jamismatch'] += 1
        if d is not None and d.get('skip'):
            bad['skipped_db'] += 1
        by_ja[r['ja']][r['en']] += 1
    print('bad counters', dict(bad))
    inc = {j: c for j, c in by_ja.items() if len(c) > 1}
    print('ja with >1 refit en:', len(inc))
    for j, c in list(inc.items())[:40]:
        print('  ', j, dict(c))
    # same ja in DB (any en) vs refit, tallying DB en that stay unrefit
    dbja = collections.defaultdict(collections.Counter)
    refid = {r['id'] for r in recs}
    for i, d in db.items():
        if d['ja'] in by_ja and i not in refid:
            dbja[d['ja']][d['en']] += 1
    left = {j: c for j, c in dbja.items()}
    print('ja that still keep old en in other (non-refit) records:', len(left))
    tot = sum(sum(c.values()) for c in left.values())
    print('  such records', tot)
    for j, c in sorted(left.items(), key=lambda kv: -sum(kv[1].values()))[:40]:
        print('  ', j, '->refit', dict(by_ja[j]), ' kept:', dict(c))
    # multi-word person forms: list a sample with order
    mw = sorted({(r['ja'], r['en']) for r in recs if r['cls'] == 'person' and ' ' in r['en']})
    print('multiword person forms', len(mw))
    for j, e in mw[:30]:
        print('  ', j, '=>', e)
    allp = sorted({(r['ja'], r['en']) for r in recs if r['cls'] == 'person'})
    print('distinct person', len(allp))
    # suspicious: en shorter than ja kana count (unlikely) / all caps
    for j, e in allp:
        if e.isupper() and len(e) > 3:
            print('ALLCAPS', j, e)


main()
