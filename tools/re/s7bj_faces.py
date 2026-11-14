"""s7bj_faces: the three FACEMDUL tiles (大 / 特 / 号 -> DAI / TOKU / GOU) and the ONISTA splash (package J).
PNGs only (build/s7/titles/new/):  python -I -X utf8 tools/re/s7bj_faces.py faces | onista
"""
import os
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7bj_lib as L

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'build', 's7', 'titles', 'new')
FACES = {
    '00056': ('build/tex/ATFIRST__FACEMDUL.DAT/00056_cb7e0_kao_g_dai.pvr_0.png', 'DAI'),
    '00062': ('build/tex/ATFIRST__FACEMDUL.DAT/00062_cb7e0_kao_r_toku.pvr_0.png', 'TOKU'),
    '00065': ('build/tex/ATFIRST__FACEMDUL.DAT/00065_cb7e0_kao_y_gou.pvr_0.png', 'GOU'),
}


def do_face(i):
    src, word = FACES[i]
    a = np.asarray(Image.open(os.path.join(ROOT, src)).convert('RGBA')).copy()
    g = a[..., 1].astype(int)
    m = np.zeros(g.shape, bool)
    bg = np.median(a[60:70, 4:8, :3].reshape(-1, 3), axis=0)
    dist = np.abs(a[..., :3].astype(int) - bg.astype(int)).sum(2)
    m[6:122, 8:120] = dist[6:122, 8:120] > 45
    m = L.dilate(m, 3)
    m[:, :6] = False
    m[:, 122:] = False
    a = L.inpaint(a, m, iters=250)
    img = Image.fromarray(a, 'RGBA')
    L.paste_text(img, (10, 34, 108, 62), word, font='impact', fill='#ffffff', outlines=[],
                 shadow=('#7d1111', -2, 3), min_sx=0.8, max_h=50)
    return img


def do_onista():
    a = np.asarray(Image.open(os.path.join(ROOT, 'build/tex/ETC_DATA__ONISTA.TBD/03546_ONISTA.TBD_0.png')).convert('RGBA')).copy()
    b = np.asarray(Image.open(os.path.join(ROOT, 'build/tex/ETC_DATA__ONISTA2.TBD/03547_ONISTA2.TBD_0.png')).convert('RGBA')).copy()
    full = np.concatenate([a, b], axis=1)  # 512 x 256
    r, g, bl = full[..., 0].astype(int), full[..., 1].astype(int), full[..., 2].astype(int)
    red = (r - g > 40) & (r - bl > 30) & (r > 90)
    m = L.dilate(red, 3)
    full = L.inpaint(full, m, iters=400)
    img = Image.fromarray(full, 'RGBA')
    red_g = [(0, '#ff2a4a'), (0.5, '#e0102c'), (1, '#a8081e')]
    L.paste_text(img, (120, 30, 272, 62), 'DECEMBER 2000', font='impact', gradient=red_g, outlines=[('#3a0008', 1)],
                 shadow=('#3a0008', 3, 3), shear=0.15, min_sx=0.8, max_h=52)
    L.paste_text(img, (62, 125, 392, 96), 'Onishige Returns!!', font='impact', gradient=red_g, outlines=[('#3a0008', 1)],
                 shadow=('#3a0008', 4, 4), shear=0.22, min_sx=0.8, max_h=84)
    return img


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for k in sys.argv[1:]:
        if k == 'faces':
            for i in FACES:
                do_face(i).save(os.path.join(OUT, i + '.png'))
        elif k == 'onista':
            im = do_onista()
            im.save(os.path.join(OUT, 'onista_full.png'))
            im.crop((0, 0, 256, 256)).save(os.path.join(OUT, '03546.png'))
            im.crop((256, 0, 512, 256)).save(os.path.join(OUT, '03547.png'))
        print(k, 'ok')
