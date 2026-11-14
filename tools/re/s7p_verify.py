"""s7p_verify - end-to-end check of the club-name plate textures written under translation/textures/GAME/:
for ALLLOGOS.BIN, BINDLOGO.BIN and BINDNAME.BIN apply every written .pvr (all of them, any owner) to the extracted file with
texinject.replace_textures (policy 'exact'), then extract every replaced texture again, compare byte for byte, decode it, and run the
stale stored-member guard.  Prints a short report; exit 1 on any failure.
usage: s7p_verify.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
import pvr, texinject

bad = 0
for f in ('ALLLOGOS.BIN', 'BINDLOGO.BIN', 'BINDNAME.BIN'):
    d = os.path.join(ROOT, 'translation', 'textures', 'GAME', f)
    repl = {}
    for fn in sorted(os.listdir(d)):
        if fn.endswith('.pvr'):
            repl[fn[:-4]] = open(os.path.join(d, fn), 'rb').read()
    src = open(os.path.join(ROOT, 'extracted', 'GAME', f), 'rb').read()
    new, infos = texinject.replace_textures(src, repl, 'exact')
    ok = len(new) == len(src)
    n = 0
    for tid, blob in repl.items():
        back = texinject.extract_pvr(new, tid)
        if back != blob:
            print(f, tid, 'EXTRACT MISMATCH'); ok = False
        a = pvr.decode(back)
        if a.shape != (128, 128, 4):
            print(f, tid, 'bad decode shape', a.shape); ok = False
        n += 1
    stale = texinject.stale_stored_members(src, new)
    if stale:
        print(f, 'STALE stored members', stale); ok = False
    print('%-13s %3d textures replaced, length %s, stale stored members %d -> %s' % (f, n, 'kept' if len(new) == len(src) else 'CHANGED', len(stale), 'OK' if ok else 'FAIL'))
    bad += 0 if ok else 1
sys.exit(1 if bad else 0)
