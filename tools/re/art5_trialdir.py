"""art5_trialdir - copy only the group-5 texture files (all dup copies) into build/art5/trial_tex."""
import os, sys, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
dst = os.path.join(L.ART, 'trial_tex')
shutil.rmtree(dst, ignore_errors=True)
n = 0
for i, m in L.MAN.items():
    for f, tid in m['copies']:
        s = os.path.join(L.TEXDIR, *f.split('/'), tid + '.pvr')
        if not os.path.exists(s):
            continue
        d = os.path.join(dst, *f.split('/'), tid + '.pvr')
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(s, d)
        n += 1
print('copied', n)
