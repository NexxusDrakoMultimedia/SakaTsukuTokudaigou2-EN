import glob, json, os, re, collections, sys
sys.path.insert(0, os.path.dirname(__file__))
import hnmg_scan as S
cnt = collections.Counter(); ex = {}
for f in sorted(glob.glob(os.path.join(S.ROOT, 'translation', '*.jsonl'))):
    for line in open(f, encoding='utf-8'):
        if not line.strip(): continue
        r = json.loads(line)
        if r['en'].endswith('-gun') or '-gun' in r['en'] or (r['ja'].endswith(('郡','群')) and len(r['ja'])<=5):
            key = (os.path.basename(f)[:20] if 'HOMETOWN' in f else 'other', re.sub(r'\[\d+/', '[i/', re.sub(r'tbl@[0-9a-f]+', 'tbl@X', r.get('ctx',''))), r['en'].endswith('-gun'))
            cnt[key] += 1; ex.setdefault(key, (os.path.basename(f), r))
for k, v in cnt.most_common():
    print(v, k, ex[k][0], ex[k][1]['id'], ex[k][1]['ja'], ex[k][1]['en'], ex[k][1]['max_bytes'])
