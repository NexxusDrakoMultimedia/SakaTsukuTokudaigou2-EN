"""ar6_boxes: ink boxes of a texture's label area: ar6_boxes.py ID XMAX [thr]  -> prints (x,y,w,h) clusters left of XMAX, writes build/ar6/boxes_ID.png"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L
i, xmax = sys.argv[1], int(sys.argv[2])
t = L.load(i)
arr = t['arr'].copy()
arr[:, xmax:, 3] = 0
b = L.components(arr, thr=100, gx=6, gy=2, min_area=12)
for k, x in enumerate(b):
    print(k, x)
L.overlay(arr, b, os.path.join(L.ROOT, 'build', 'ar6', 'boxes_%s.png' % i), scale=3)
print(t['src'], t['tid'], t['info']['format'], [c[0] for c in L.dups(t['src'], t['tid'])])
