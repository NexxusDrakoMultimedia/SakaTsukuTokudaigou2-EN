"""tdl: debug helper for tools/texdelta.py (find the first texture whose delta does not round-trip)."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texdelta as T   # noqa: E402
import vcdiff as V     # noqa: E402

rel = sys.argv[1]
cont, tid = T.split_container(rel.split('/'), T.DEF_EXTRACTED)
src = T.Originals(T.DEF_EXTRACTED).texture(cont, tid[:-4])
tgt = open(os.path.join(T.DEF_TEXTURES, *rel.split('/')), 'rb').read()
print(len(src), len(tgt), src[:16].hex(), tgt[:16].hex())
d = T.encode_delta(src, tgt)
print(len(d))
pcs = T.delta_pieces(d)
tot = 0
for k, v in pcs[:40]:
    n = len(v) if k == 'add' else v
    tot += n
    print(k, n)
print(len(pcs), sum((len(v) if k == 'add' else v) for k, v in pcs))
