"""Who are the FIXED (non-relocatable) strings that overflow?  Same English model as joint.py.
  python -I -X utf8 tools/re/capacity/synth/fixedcat.py [scale ...]"""
import sys, os, collections, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('joint', os.path.join(here, 'joint.py')); J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
R, RC, PC = J.R, J.RC, J.PC
scales = [float(x) for x in sys.argv[1:]] or [1.0, 0.85, 0.80]
emp = J.emp_ratios()
rows = [r for r in RC.load() if RC.is_ov(r)]
catof = {r['id']: RC.category(r) for r in rows}
imgs = PC.load_all('full')
for scale in scales:
    byc = collections.Counter(); byc_en = collections.Counter(); tot = collections.Counter()
    by_src = collections.Counter(); distinct = set()
    for source, img, strs, ptrs in imgs:
        for s in strs:
            if R.is_movable(s):
                continue
            cat = catof.get('%s#%x' % (source, s.off), 'label')
            f = J.quant(emp[cat], J.uhash(s.raw)) * scale
            n = max(1, int(round(f * (len(s.raw) + 1))) - 1)
            tot[cat] += 1
            if n + 1 > s.max_bytes:
                byc[cat] += 1; byc_en[cat] += n + 1; by_src[source.split('/')[-1]] += 1; distinct.add(s.raw)
    print('scale %.2f: fixed strings %d, overflowing %d (%d distinct JP texts), EN bytes %d' % (scale, sum(tot.values()), sum(byc.values()), len(distinct), sum(byc_en.values())))
    print('   by category (overflowing/fixed total):', {c: '%d/%d' % (byc[c], tot[c]) for c in sorted(tot)})
    print('   top overlays:', by_src.most_common(6))
