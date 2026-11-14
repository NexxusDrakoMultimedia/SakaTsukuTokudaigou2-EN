"""Lower bound of the EXTERNAL bytes (append / bank) that the movable strings need, per English scale.
joint.py counts the English size of the strings that the greedy planner reverts to Japanese; moving a string out of its pool
also frees its place in the pool, so the real external need is smaller: the pool deficit  sum_pools max(0, need - cap)
(no cross-pool moves; each pool is independent) is the minimum number of bytes that must live outside the pools.
  python -I -X utf8 tools/re/capacity/synth/deficit.py [scale ...]
Then compare with budgets: L3 bank 259,771 B and per-overlay append_cons (build/memmap/overlays.tsv)."""
import sys, os, collections, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('joint', os.path.join(here, 'joint.py')); J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
R, RC, PC = J.R, J.RC, J.PC
scales = [float(x) for x in sys.argv[1:]] or [1.0, 0.95, 0.90, 0.85, 0.80]
emp = J.emp_ratios()
rows = [r for r in RC.load() if RC.is_ov(r)]
catof = {r['id']: RC.category(r) for r in rows}
imgs = PC.load_all('full')
bud = J.budgets()
for scale in scales:
    out = {}
    for share in ('none', 'dup'):
        tot = 0; per = {}
        for source, img, strs, ptrs in imgs:
            enc = {}
            for s in strs:
                cat = catof.get('%s#%x' % (source, s.off), 'label')
                n = max(1, int(round(J.quant(emp[cat], J.uhash(s.raw)) * scale * (len(s.raw) + 1))) - 1)
                enc[s.off] = J.dummy(s.raw, n)
            pl = R.plan_pools(strs, enc, share=share, cross_pool=False)
            d = sum(p.deficit0 for p in pl.pools)
            per[source] = d; tot += d
        out[share] = (tot, per)
    # per-overlay budgets after the 259,771 B bank is spent on the biggest deficits last (simple fill: cons first)
    for share in ('none', 'dup'):
        tot, per = out[share]
        short = 0; over = []
        for source, d in per.items():
            row = bud.get(source)
            cons = int(row['append_cons']) if (row and row['append_cons'] and not source.endswith(J.SPECIAL_NO_APPEND)) else 0
            if d > cons:
                short += d - cons; over.append((d - cons, source.split('/')[-1][:-4], d, cons))
        over.sort(reverse=True)
        print('scale %.2f share=%-4s: sum of pool deficits %8d B | not covered by per-overlay append_cons: %7d B (%s) -> bank 259,771 B %s' % (
            scale, share, tot, short, ', '.join('%s %d/%d' % (n, d, c) for _, n, d, c in over[:6]),
            'COVERS it' if short <= 259771 else 'does NOT cover it'))
