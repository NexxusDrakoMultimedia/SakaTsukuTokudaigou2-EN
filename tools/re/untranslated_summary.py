"""Summarise records without English: per source file and per ctx kind, and distinct ja with no en anywhere.
   python -I -X utf8 tools/re/untranslated_summary.py [N_EXAMPLES]"""
import collections, glob, json, os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
nex = int(sys.argv[1]) if len(sys.argv) > 1 else 5
by_src = collections.Counter()
by_kind = collections.Counter()
skip_cnt = 0
distinct_missing = {}
ja_has_en = set()
ex = collections.defaultdict(list)
rows = []
for f in sorted(glob.glob(os.path.join(root, 'translation', '*.jsonl'))):
    with open(f, encoding='utf8') as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if (r.get('en') or '').strip():
                ja_has_en.add(r['ja'])
            else:
                rows.append((os.path.basename(f), r))
for src, r in rows:
    if r.get('skip'):
        skip_cnt += 1
        continue
    kind = (r.get('ctx') or '').split(' ')[0] or '-'
    has = r['ja'] in ja_has_en
    by_src[(src, has)] += 1
    by_kind[(kind, has)] += 1
    if not has:
        distinct_missing[r['ja']] = r['id']
    if len(ex[(kind, has)]) < nex:
        ex[(kind, has)].append((r['id'], r['ja'][:30]))
print('skip-flagged records without en:', skip_cnt)
print('records without en, not skipped, ja translated elsewhere (True) or not (False):')
for (k, h), n in by_kind.most_common(25):
    print('  %-24s %-5s %7d  e.g. %s' % (k, h, n, ex[(k, h)][:3]))
print('top sources:')
for (s, h), n in by_src.most_common(25):
    print('  %-40s %-5s %d' % (s, h, n))
print('distinct ja with no en anywhere:', len(distinct_missing))
