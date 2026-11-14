"""skp (skeptic): build a trial disc with the standard flags and fontpatch align_fix=True forced on (build_patch has no flag yet).

    python -I -X utf8 tools/re/skp_build_align.py OUT_DIR NAME      (OUT_DIR must be under build/trial)
"""
import os, sys, functools
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
out, name = sys.argv[1], sys.argv[2]
assert os.path.abspath(out).startswith(os.path.join(ROOT, 'build', 'trial')), 'trial dir only'
import fontpatch as FPT
_orig = FPT.make_patches
FPT.make_patches = functools.partial(_orig, align_fix=True) if False else (lambda *a, **k: _orig(*a, **dict(k, align_fix=True)))
import build_patch as B
os.chdir(ROOT)
sys.exit(B.main(['--out', out, '--name', name, '--repack', 'on', '--share', 'dup', '--append-safe', '--proportional-font', 'on', '--strict'] + sys.argv[3:]))
