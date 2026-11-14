"""extra_sources.py [TDB] FMT S : sources carrying recarr records of that stride (docs/uncovered-text.md)."""
import glob, json, os, re, sys
tdb, S = sys.argv[1], sys.argv[2]
out = {}
for p in sorted(glob.glob(os.path.join(tdb, '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        if '"recarr"' in line:
            r = json.loads(line)
            m = re.match(r'recarray S=(\d+) n=(\d+) W=(\d+)', r['ctx'])
            if m.group(1) == S:
                out.setdefault(r['id'].rsplit('#', 1)[0], set()).add(m.group(3))
print(S, sorted((k, sorted(v)) for k, v in out.items()))
