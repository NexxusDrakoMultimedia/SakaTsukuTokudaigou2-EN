"""s7m_probe SRC TID : print size, alpha stats and the colour histogram of a texture (for spec writing)."""
import sys, collections
sys.path.insert(0, __file__.rsplit('s7m_probe', 1)[0])
import s7m_lib as L
t = L.load(sys.argv[1], sys.argv[2])
a = t['arr']
print(a.shape, 'alpha<255 px', int((a[..., 3] < 255).sum()))
c = collections.Counter(map(tuple, a.reshape(-1, 4).tolist()))
for k, v in c.most_common(14):
    print(k, v)
if len(sys.argv) > 3:
    x0, y0, x1, y1 = map(int, sys.argv[3:7])
    for y in range(y0, y1):
        print(y, ' '.join('%02x%02x%02x' % tuple(a[y, x, :3]) for x in range(x0, x1)))
