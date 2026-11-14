import glob, json, os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
seen = collections.OrderedDict()
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        if not line.strip():
            continue
        r = json.loads(line)
        ja = r.get('ja') or ''
        en = r.get('en') or ''
        if ('円' in ja or '万' in ja or '億' in ja) and '%m' not in en:
            k = (ja, en)
            seen.setdefault(k, []).append(r['id'].split('#')[0].split('/')[-1] + '#' + r['id'].split('#')[1] + ' mb=%s' % r.get('max_bytes'))
for (ja, en), ids in seen.items():
    s = ('%r -> %r  x%d  %s' % (ja[:60], en[:70], len(ids), ids[0])).encode('ascii', 'backslashreplace').decode()
    sys.stdout.write(s + '\n')
