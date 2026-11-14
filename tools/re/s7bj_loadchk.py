"""s7bj_loadchk: does texinject.load_textures_dir pick up my files (incl. the @cb7e0 run members)?"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import texinject
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
g = texinject.load_textures_dir(os.path.join(ROOT, 'translation', 'textures'), os.path.join(ROOT, 'extracted'))
for k in sorted(g):
    if any(w in k for w in ('TITLE', 'FACEMDUL', 'KSPAPET', 'ONISTA')):
        print(k, sorted(g[k]))
