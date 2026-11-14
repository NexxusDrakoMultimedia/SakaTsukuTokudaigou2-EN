import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import art4_specs, art4_specs_b
out = []
for n, j in art4_specs.JOBS.items():
    for f, t in [(j['file'], j['tid'])] + list(j.get('dups', [])):
        out.append('%s/%s.pvr' % (f, t))
        print(n, f, t)
open(os.path.join(HERE, 'art4sk_list.txt'), 'w').write('\n'.join(out) + '\n')
