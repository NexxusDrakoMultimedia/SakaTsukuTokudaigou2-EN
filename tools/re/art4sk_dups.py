import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import art4_specs, art4_specs_b
seen = set()
for n, j in art4_specs.JOBS.items():
    tgt = [(j['file'], j['tid'])] + list(j.get('dups', []))
    for f, t in tgt:
        if (f, t) in seen: continue
        seen.add((f, t))
        r = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, '..', 'texinject.py'), 'dups', f, t], capture_output=True, text=True, cwd=os.path.join(HERE, '..', '..'))
        print('##', n, f, t); print(r.stdout.strip()[:600], r.stderr.strip()[:200])
