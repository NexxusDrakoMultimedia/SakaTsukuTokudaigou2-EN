"""End-to-end validation of the joint model: fill EVERY overlay record with synthetic English (same model as joint.py:
per-category empirical ratio, equal Japanese -> equal English), write it to build/synth_full/, and run the real
pipeline (tools/build_patch.py build_patches, dry: no disc) with repack on/off and share none/dup.
  python -I -X utf8 tools/re/capacity/synth/fullrun.py [scale]          (default 0.85)
The numbers can be compared with joint_out.txt (planner only): they must agree."""
import sys, os, json, glob, time, importlib.util, collections
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('joint', os.path.join(here, 'joint.py'))
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)
import build_patch as BP     # noqa: E402  (joint.py put tools/ on sys.path and chdir'd to the repo root)
import textdb as T

scale = float(sys.argv[1]) if len(sys.argv) > 1 else 0.85
emp = J.emp_ratios()
out = os.path.join('build', 'synth_full')
os.makedirs(out, exist_ok=True)
for f in glob.glob(os.path.join(out, '*.jsonl')):
    os.remove(f)
n_en = 0
for p in sorted(glob.glob('translation/*.jsonl')):
    name = os.path.basename(p)
    if not name.startswith(('FLOW_PRG__', 'ATFIRST__')):
        continue
    with open(p, encoding='utf8') as f, open(os.path.join(out, name), 'w', encoding='utf8', newline='\n') as g:
        for line in f:
            r = json.loads(line)
            raw = T.encode_text(r['ja'])
            cat = J.RC.category(dict(r, file=name[:-6]))
            fct = J.quant(emp[cat], J.uhash(raw)) * scale
            n = max(1, int(round(fct * (len(raw) + 1))) - 1)
            r['en'] = J.dummy(raw, n).decode('ascii')
            n_en += 1
            g.write(json.dumps(r, ensure_ascii=False) + '\n')
print('scale %.2f: %d overlay records filled' % (scale, n_en))
for label, kw in (('legacy textdb per-string', dict(repack=False)),
                  ('repack share=none cross-pool', dict(repack=True, share='none')),
                  ('repack share=dup  cross-pool', dict(repack=True, share='dup'))):
    t0 = time.time()
    res = BP.build_patches(out, **kw)
    t = res.totals()
    over = sum(f.new_size - f.old_size for f in res.files if f.changed)
    print('%-30s applied %6d failed %6d (%.1f %%) skipped %d, in_place %d relocated %d, files changed %d, size growth %d, %.0fs' % (
        label, t['applied'], t['failed'], 100.0 * t['failed'] / n_en, t['skipped'], t['in_place'], t['relocated'],
        t['files_changed'], over, time.time() - t0))
