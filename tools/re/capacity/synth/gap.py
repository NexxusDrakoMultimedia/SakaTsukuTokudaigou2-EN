"""Where does the real pipeline differ from the planner-only model (joint.py)?  Per overlay: strings that stay Japanese
in build_patches (repack on, share none) vs. movable+fixed overflow predicted by textrepack.plan_pools.
  python -I -X utf8 tools/re/capacity/synth/gap.py [scale]"""
import sys, os, json, glob, importlib.util, collections
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('joint', os.path.join(here, 'joint.py'))
J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
import build_patch as BP
import textdb as T, textrepack as R

scale = float(sys.argv[1]) if len(sys.argv) > 1 else 0.85
emp = J.emp_ratios()
tdb = os.path.join('build', 'synth_gap'); os.makedirs(tdb, exist_ok=True)
for f in glob.glob(os.path.join(tdb, '*.jsonl')):
    os.remove(f)
for p in sorted(glob.glob('translation/*.jsonl')):
    nm = os.path.basename(p)
    if not nm.startswith(('FLOW_PRG__', 'ATFIRST__')):
        continue
    with open(p, encoding='utf8') as f, open(os.path.join(tdb, nm), 'w', encoding='utf8', newline='\n') as g:
        for line in f:
            r = json.loads(line)
            raw = T.encode_text(r['ja'])
            cat = J.RC.category(dict(r, file=nm[:-6]))
            n = max(1, int(round(J.quant(emp[cat], J.uhash(raw)) * scale * (len(raw) + 1))) - 1)
            r['en'] = J.dummy(raw, n).decode('ascii')
            g.write(json.dumps(r, ensure_ascii=False) + '\n')
res = BP.build_patches(tdb, repack=True, share='none')
pipe = {f.iso[1:]: f for f in res.files if f.kind == 'overlay'}
tot_p = tot_m = 0
rows = []
for source, f in sorted(pipe.items()):
    img = T.load_image(source)
    strs, ptrs, x = T.extract_image(img)
    # same english as written to the tdb
    recs = {}
    for line in open(os.path.join(tdb, source.replace('/', '__') + '.jsonl'), encoding='utf8'):
        r = json.loads(line); recs[int(r['id'].rsplit('#', 1)[1], 16)] = r['en'].encode('ascii')
    enc = {s.off: recs[s.off] for s in strs}
    pl = R.plan_pools(strs, enc, share='none', cross_pool=True)
    m = len(pl.reverted) + len(pl.fixed_overflow)
    tot_p += len(f.failed); tot_m += m
    if len(f.failed) != m:
        rows.append((source, len(f.failed), m, len(strs)))
print('scale %.2f: pipeline failed %d, planner (same English) %d' % (scale, tot_p, tot_m))
for r in rows[:20]:
    print('  differs: %s pipeline %d planner %d (of %d strings)' % r)
