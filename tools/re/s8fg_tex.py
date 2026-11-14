"""s8fg: list textures of an overlay in several disc copies and render PNGs side by side.
usage: s8fg_tex.py FILE(like FLOW_PRG/SCDRF.BIN) [TID ...]  (uses build/s8fg/<disc>/FILE from s8fg_extract.py)
Writes build/s8fg/png/<file>_<tid>.png : orig | hsk_full1 | s8e_nofix with 4px magenta separators. With no TID: lists textures and exits.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T  # noqa: E402
import pvr as P  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

DISCS = ['orig', 'hsk_full1', 's8e_nofix']


def main(argv):
    rel = argv[1]
    data = {}
    for d in DISCS:
        with open(os.path.join(ROOT, 'build', 's8fg', d, rel), 'rb') as f:
            data[d] = f.read()
    tl = T.list_textures(data['orig'])
    if len(argv) == 2:
        for t in tl:
            print(t)
        return
    out = os.path.join(ROOT, 'build', 's8fg', 'png')
    os.makedirs(out, exist_ok=True)
    for tid in argv[2:]:
        imgs = []
        for d in DISCS:
            try:
                imgs.append(P.decode(T.extract_pvr(data[d], tid)))
            except Exception as e:
                print('fail', d, tid, e)
                imgs.append(np.zeros((8, 8, 4), np.uint8))
        h = max(i.shape[0] for i in imgs)
        w = sum(i.shape[1] for i in imgs) + 4 * (len(imgs) - 1)
        cv = np.zeros((h, w, 4), np.uint8)
        cv[:, :, 0] = 255
        cv[:, :, 2] = 255
        cv[:, :, 3] = 255
        x = 0
        for i in imgs:
            cv[:i.shape[0], x:x + i.shape[1]] = i
            x += i.shape[1] + 4
        fn = os.path.join(out, '%s_%s.png' % (rel.replace('/', '_'), tid.replace('#', '_').replace('@', 'at')))
        Image.fromarray(cv, 'RGBA').save(fn)
        print(tid, [i.shape for i in imgs], '->', fn)


main(sys.argv)
