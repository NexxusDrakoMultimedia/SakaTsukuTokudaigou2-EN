import glob, json, os, random, sys
tdb = sys.argv[1]
fmt = sys.argv[2]
seen = {}
for p in sorted(glob.glob(os.path.join(tdb, '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        if '"fmt":"%s"' % fmt in line:
            r = json.loads(line)
            seen.setdefault(r['ja'], r['id'])
random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
ks = list(seen)
print(len(ks), 'distinct')
print(' | '.join(random.sample(ks, min(120, len(ks)))))
