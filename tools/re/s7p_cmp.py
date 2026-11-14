"""s7p_cmp - compare ALLLOGOS [k] with BINDLOGO [k+14]: byte positions that differ."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import s7p_dump as D
for k in (0, 30, 59, 65):
    a = D.load('GAME/ALLLOGOS.BIN', '[%d]' % k); b = D.load('GAME/BINDLOGO.BIN', '[%d]' % (k + 14))
    diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    print(k, len(a), len(b), len(diff), diff[:10], a[:32].hex(), b[:32].hex())
