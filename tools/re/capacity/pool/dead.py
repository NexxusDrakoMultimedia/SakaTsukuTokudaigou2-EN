"""Dead-space candidates adjacent to pools: unreferenced ASCII-only runs (debug text) that touch a pool.
-> results/dead.json.  A run is NUL-terminated printable ASCII >= 6 chars, outside accepted strings, whose
start offset is not the target of any in-image aligned pointer ('unreferenced')."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import textrepack as R
RUN = re.compile(rb'(?<![\x20-\x7e])[\x20-\x7e]{6,}(?=\x00)')
out = {}
samples = {}
for source, img, strs, ptrs in load_all():
    d = img.data
    cov = bytearray(len(d))
    for s in strs:
        for k in range(s.off, s.end + 1):
            cov[k] = 1
    tgt = set(ptrs.values())
    runs = {m.start(): m.end() for m in RUN.finditer(d) if not cov[m.start()]}
    pools, _ = R.find_pools(strs)
    after = before = 0
    n_after = n_before = 0
    ends = {e: s0 for s0, e in runs.items()}
    for p in pools:
        pos = p.z
        while pos in runs and pos not in tgt:
            e = runs[pos]
            after += e + 1 - pos
            n_after += 1
            pos = e + 1
            while pos < len(d) and d[pos] == 0 and pos not in tgt and pos not in runs:
                pos += 1
        pos = p.a - 1                       # NUL just before the pool, run ends at pos
        while pos in ends and ends[pos] not in tgt:
            st = ends[pos]
            before += pos + 1 - st
            n_before += 1
            pos = st - 1
    ref = [(a, e) for a, e in runs.items() if a in tgt]
    unref = [(a, e) for a, e in runs.items() if a not in tgt]
    out[source] = dict(runs=len(runs), runs_bytes=sum(e + 1 - a for a, e in runs.items()), unref=len(unref),
                       unref_bytes=sum(e + 1 - a for a, e in unref), adj_after=after, adj_after_n=n_after,
                       adj_before=before, adj_before_n=n_before, pools=len(pools))
    if source in ('FLOW_PRG/MEETING.BIN', 'FLOW_PRG/EVENT.BIN', 'FLOW_PRG/CHALMODE.BIN'):
        samples[source] = [d[a:e].decode('ascii')[:60] for a, e in unref[:15]]
json.dump(dict(per=out, samples=samples), open(os.path.join(HERE, 'results', 'dead.json'), 'w'), indent=0, ensure_ascii=False)
t = lambda k: sum(v[k] for v in out.values())
print('images', len(out), 'ascii runs', t('runs'), 'bytes', t('runs_bytes'), 'unreferenced', t('unref'), t('unref_bytes'),
      'adjacent after pool', t('adj_after'), '(%d runs)' % t('adj_after_n'), 'adjacent before pool', t('adj_before'), '(%d runs)' % t('adj_before_n'))
for s, v in samples.items():
    print(s, v[:8])
