"""art3_boxes.py - list connected ink components (alpha > 0) of a decoded texture PNG within a window.
usage: python -I -X utf8 tools/re/art3_boxes.py IN.png x0 y0 x1 y1 [dx dy]
dx,dy = merge gap in pixels (default 5 2).  Prints x y w h and mean colour."""
import sys
import numpy as np
from PIL import Image


def main():
    p = sys.argv[1]
    x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]
    dx = int(sys.argv[6]) if len(sys.argv) > 6 else 5
    dy = int(sys.argv[7]) if len(sys.argv) > 7 else 2
    a = np.asarray(Image.open(p).convert('RGBA'))[y0:y1, x0:x1]
    m = a[:, :, 3] > 8
    H, W = m.shape
    # dilate
    d = m.copy()
    for k in range(1, dx + 1):
        d[:, k:] |= m[:, :-k]
        d[:, :-k] |= m[:, k:]
    e = d.copy()
    for k in range(1, dy + 1):
        e[k:, :] |= d[:-k, :]
        e[:-k, :] |= d[k:, :]
    lab = np.zeros((H, W), np.int32)
    n = 0
    boxes = []
    for sy in range(H):
        for sx in range(W):
            if e[sy, sx] and not lab[sy, sx]:
                n += 1
                st = [(sy, sx)]
                lab[sy, sx] = n
                xs, ys = [], []
                while st:
                    y, x = st.pop()
                    xs.append(x)
                    ys.append(y)
                    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= ny < H and 0 <= nx < W and e[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = n
                            st.append((ny, nx))
                xs = np.array(xs)
                ys = np.array(ys)
                mm = m[ys, xs]
                bx0, bx1, by0, by1 = xs[mm].min(), xs[mm].max(), ys[mm].min(), ys[mm].max()
                boxes.append((by0, bx0, bx1 - bx0 + 1, by1 - by0 + 1, int(mm.sum())))
    boxes.sort()
    for by, bx, w, h, c in boxes:
        print('x=%d y=%d w=%d h=%d  px=%d' % (bx + x0, by + y0, w, h, c))


main()
