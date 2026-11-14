"""skeptic: list distinct person refit forms by why-class for eyeballing."""
import glob, json, os, collections, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
seen = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl'))):
    for ln in open(f, encoding='utf-8'):
        if ln.strip():
            r = json.loads(ln)
            if r['cls'] == 'person':
                seen[(r['ja'], r['en'])] = r['why']
cls = collections.defaultdict(list)
for (j, e), w in seen.items():
    cls[w.split(';')[0].split('(')[0][:30]].append((j, e))
for w, l in sorted(cls.items(), key=lambda kv: -len(kv[1])):
    print(w, len(l))
    for j, e in sorted(l)[:int(sys.argv[1]) if len(sys.argv) > 1 else 12]:
        print('   ', j, e)
