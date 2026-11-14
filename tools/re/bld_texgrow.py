"""bld_texgrow: for every texture under translation/textures, would it fit its slot (policy exact) and may its container grow?
    python -I -X utf8 tools/re/bld_texgrow.py            (read only; prints only the textures that do not fit)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
import texinject as T
groups = T.load_textures_dir(os.path.join(ROOT, 'translation', 'textures'), os.path.join(ROOT, 'extracted'))
n = bad = 0
for cont in sorted(groups):
    for tid in sorted(groups[cont], key=str):
        n += 1
        fc = T.fit_check(cont, tid, groups[cont][tid])
        if not fc['fits']:
            bad += 1
            print('%-24s %-14s over %5d  slot %6d  growable=%s' % (cont, tid, fc['over'], fc['slot'], fc['growable']))
print('%d textures, %d over their slot' % (n, bad))
