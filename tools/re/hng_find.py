"""hng: search translation records.  usage: hng_find.py REGEX [SOURCE-substring] [--ja]   (regex on en, or on ja with --ja)"""
import glob, json, os, re, sys
a = [x for x in sys.argv[1:] if not x.startswith('--')]
pat = re.compile(a[0], re.I)
src = a[1] if len(a) > 1 else ''
fld = 'ja' if '--ja' in sys.argv else 'en'
for p in sorted(glob.glob(os.path.join('translation', '*.jsonl'))):
    if src not in p:
        continue
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        if pat.search(r.get(fld) or ''):
            print(r['id'], '|', r.get('max_bytes'), '|', repr(r['en'])[:200], '|', r['ja'][:30].replace('\n', '/'))
