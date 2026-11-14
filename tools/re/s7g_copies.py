"""s7g_copies: every place the same art lives (texinject.find_copies on build/texindex.tsv, byte-compared) for the s7g textures."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.dirname(__file__))
import texinject as T
from s7g_dump import JOBS
for k, (f, t) in JOBS.items():
    try:
        cp = T.find_copies(os.path.join(ROOT, 'build', 'texindex.tsv'), f, t)
    except Exception as e:
        print(k, 'ERR', e); continue
    print(k, [(r[0], r[1]) for r in cp])
