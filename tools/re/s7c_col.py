import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7c_dump as D
a = D.load('t_staff')[1]
c = collections.Counter(map(tuple, a[a[..., 3] > 0].reshape(-1, 4)))
for k, v in c.most_common(14): print(k, v)
# per-row colour of the brightest ink, and glyph rows
for y in range(8, 34, 2):
    r = a[y]; m = r[:, 3] > 200
    print(y, m.sum(), r[m][:, :3].max(0) if m.any() else '')
