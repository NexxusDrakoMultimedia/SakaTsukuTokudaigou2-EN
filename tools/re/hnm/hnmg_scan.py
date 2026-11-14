"""gun-removal scan: municipality pointer-table records (tbl@..[i/1270]) across FLOW_PRG translation files."""
import glob, json, os, re, collections, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
def load():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'translation', 'FLOW_PRG__*.jsonl'))):
        for ln, line in enumerate(open(f, encoding='utf-8')):
            if not line.strip():
                continue
            r = json.loads(line)
            if re.search(r'tbl@[0-9a-f]+\[\d+/1270\]', r.get('ctx', '')):
                out.append((f, ln, r))
    return out
if __name__ == '__main__':
    recs = load()
    files = collections.Counter(os.path.basename(f) for f, _, _ in recs)
    print(len(recs), len(files), sorted(set(files.values())))
    ja = collections.defaultdict(set)
    for f, _, r in recs:
        ja[r['ja']].add(r['en'])
    multi = {k: v for k, v in ja.items() if len(v) > 1}
    print('ja with >1 en:', len(multi))
    for k, v in list(multi.items())[:60]:
        print(k, sorted(v))
    kinds = collections.Counter()
    for f, _, r in recs:
        kinds[(r['ja'][-1:], r['en'].endswith('-gun'))] += 1
    print(kinds.most_common(30))
    print(collections.Counter(re.sub(r'\[.*', '', r['ctx']) for _, _, r in recs).most_common(10))
    print(collections.Counter(r['max_bytes'] for _, _, r in recs))
    print({k: sorted(r for r in v)[:3] for k, v in []})
