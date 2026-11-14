"""s8ha: time make_patches over all overlays, align off / default / snap-all; list what differs from align off."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fontpatch as FP
t0 = time.time()
off, r0 = FP.make_patches(FP.read_extracted, align_fix=False)
print('off', round(time.time() - t0, 1), len(off))
for mode in ('default', 'snap-all', 'snap-only', 'panel-only'):
    t0 = time.time()
    on, r1 = FP.make_patches(FP.read_extracted, align_fix=mode)
    diff = {k: sum(1 for a, b in zip(off[k], on[k]) if a != b) for k in on if on[k] != off.get(k)}
    print(mode, round(time.time() - t0, 1), 'differing files', len(diff), 'snap', r1['snap'], 'panel', [x[0] for x in r1['panel']])
    if len(diff) < 8:
        print('   ', diff)
