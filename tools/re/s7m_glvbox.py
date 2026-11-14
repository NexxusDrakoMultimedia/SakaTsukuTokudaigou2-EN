import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7m_lib as L, art7_lib
t = L.load('FLOW_PRG/TWND1.ZAR', 'glv.tbd#5'); a = t['arr']
sub = a.copy(); sub[:, 56:, 3] = 0; sub[:16] = 0
for b in art7_lib.components(sub, gx=6, gy=2): print('text', b)
sub = a.copy(); sub[:, :94, 3] = 0; sub[40:] = 0
for b in art7_lib.components(sub, gx=2, gy=2): print('tag', b)
print([int((a[y,:56,3]>0).sum()) for y in range(128)])
