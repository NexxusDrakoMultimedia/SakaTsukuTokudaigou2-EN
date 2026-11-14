"""Propagate decided English to records of the same Japanese that still have none.
   python -I -X utf8 tools/re/propagate_en.py [--apply] [--report FILE]

Background: tools/transmerge.py writes an item's English to every record with that ja *at merge time*.  Records added
later by textdb extract (recarray / hwptr extractors) therefore stayed empty although the same Japanese text was
translated in another table.  For every record with an empty en (and no skip flag) whose ja has English elsewhere, this
picks the LONGEST known English form that fits the record's slot (fixed records: len(cp932 bytes) + 1 <= max_bytes) and writes it.
Records for which no known form fits are listed (the report) for a ladder rewrite.  Without --apply nothing is written.
"""
import collections, glob, json, os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
apply = '--apply' in sys.argv
report = None
if '--report' in sys.argv:
    report = sys.argv[sys.argv.index('--report') + 1]

files = sorted(glob.glob(os.path.join(root, 'translation', '*.jsonl')))
data = {}
forms = collections.defaultdict(collections.Counter)
for f in files:
    with open(f, encoding='utf8', newline='') as fh:
        lines = fh.read().split('\n')
    recs = []
    for ln in lines:
        recs.append(json.loads(ln) if ln.strip() else None)
    data[f] = (lines, recs)
    for r in recs:
        if r and (r.get('en') or '').strip() and not r.get('skip'):
            forms[r['ja']][r['en']] += 1


def nbytes(s):
    return len(s.encode('cp932', errors='replace')) + 1


def fixed_slot(r):
    ctx = r.get('ctx') or ''
    return r.get('fmt') in ('recarr', 'hwptr') or 'in-place only' in ctx or 'orphan' in ctx


filled = unfit = 0
unfit_rows = []
for f, (lines, recs) in data.items():
    changed = False
    for i, r in enumerate(recs):
        if not r or (r.get('en') or '').strip() or r.get('skip'):
            continue
        cand = forms.get(r['ja'])
        if not cand:
            continue
        mb = r.get('max_bytes')
        ok = [e for e in cand if (not fixed_slot(r) or mb is None or nbytes(e) <= mb)]
        if not ok:
            unfit += 1
            unfit_rows.append((r['id'], r['ja'], mb, sorted(cand, key=len)[:3]))
            continue
        # longest fitting form; ties: most used, then alphabetical
        best = sorted(ok, key=lambda e: (-len(e), -cand[e], e))[0]
        r['en'] = best
        lines[i] = json.dumps(r, ensure_ascii=False, separators=(',', ':'))
        filled += 1
        changed = True
    if changed and apply:
        tmp = f + '.tmp'
        with open(tmp, 'w', encoding='utf8', newline='') as fh:
            fh.write('\n'.join(lines))
        os.replace(tmp, f)
print('%s: filled %d records, %d records have no fitting form' % ('APPLIED' if apply else 'dry run', filled, unfit))
if report:
    with open(report, 'w', encoding='utf8') as fh:
        for row in unfit_rows:
            fh.write('\t'.join(str(x) for x in row) + '\n')
    print('report:', report)
