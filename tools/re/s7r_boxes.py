"""s7r_boxes ID [gx gy] : component boxes of the ORIGINAL texture (alpha) -> prints boxes"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L
t = L.load(sys.argv[1])
gx = int(sys.argv[2]) if len(sys.argv) > 2 else 3
gy = int(sys.argv[3]) if len(sys.argv) > 3 else 1
for i, b in enumerate(L.components(t['arr'], gx=gx, gy=gy)):
    print(i, b)
