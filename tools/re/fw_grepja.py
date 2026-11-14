"""fw_grepja.py SUBSTRING [GLOB-substring-of-source]: print source id and Japanese text of every translation record whose ja contains SUBSTRING (read-only)."""
import glob, json, sys
sub = sys.argv[1]
flt = sys.argv[2] if len(sys.argv) > 2 else ''
seen = set()
for p in sorted(glob.glob('translation/*.jsonl')):
    if flt and flt not in p:
        continue
    for ln in open(p, encoding='utf8'):
        r = json.loads(ln)
        if sub in r['ja']:
            k = r['ja']
            tag = '' if k not in seen else ' (dup)'
            seen.add(k)
            if tag:
                continue
            print(r['id'], '|', r['ja'].replace('\n', '/')[:110], '|', r['en'].replace('\n', '/')[:80])
