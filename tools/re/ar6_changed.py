"""ar6_changed: list texture files under translation/textures that differ from build/ar6/texbak (the snapshot taken at the start of ar6)."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
A = os.path.join(ROOT, 'build', 'ar6', 'texbak'); B = os.path.join(ROOT, 'translation', 'textures')
for dp, dn, fn in os.walk(B):
    for f in fn:
        p = os.path.join(dp, f); r = os.path.relpath(p, B); q = os.path.join(A, r)
        if not os.path.exists(q):
            print('NEW', r.replace(os.sep, '/'))
        elif open(p, 'rb').read() != open(q, 'rb').read():
            print('CHG', r.replace(os.sep, '/'))
