"""skp (skeptic): en strings (visible, non-debug) with a leading run of 2+ blanks, grouped by file; read-only."""
import glob, json, os, re, collections
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'translation')
c = collections.Counter(); ex = {}
for f in sorted(glob.glob(os.path.join(root, '*.jsonl'))):
    for line in open(f, encoding='utf-8'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        en = r.get('en') or ''
        for ln in en.split('\n'):
            if re.match(r'^  +\S', ln):
                k = os.path.basename(f)[:-6]
                c[k] += 1
                ex.setdefault(k, []).append((r['id'].split('#')[-1], ln[:50]))
for k, v in c.most_common():
    print(k, v, ex[k][:3])
