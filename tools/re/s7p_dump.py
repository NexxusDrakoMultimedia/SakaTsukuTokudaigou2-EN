"""s7p_dump - decode original club-name plate textures to PNG (RGBA on mid-grey/checker next to alpha) for viewing.
python -I -X utf8 tools/re/s7p_dump.py OUTDIR file tid [file tid ...]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import numpy as np
from PIL import Image
import texinject, pvr


def load(file_rel, tid):
    path = os.path.join(texinject.EXTRACTED, *file_rel.split('/'))
    with open(path, 'rb') as f:
        d = f.read()
    return texinject.extract_pvr(d, tid)


def to_img(blob):
    return pvr.decode(blob)


def on_bg(img, bg=(70, 90, 140)):
    a = img[..., 3:4].astype(float) / 255
    rgb = img[..., :3] * a + np.array(bg) * (1 - a)
    return Image.fromarray(rgb.astype('uint8'))


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    args = sys.argv[2:]
    for i in range(0, len(args), 2):
        f, t = args[i], args[i + 1]
        img = to_img(load(f, t))
        name = f.replace('/', '_') + '_' + t.strip('[]')
        Image.fromarray(img).save(os.path.join(out, name + '.png'))
        on_bg(img).resize((384, 384), Image.NEAREST).save(os.path.join(out, name + '_bg.png'))
        print(name, img.shape)
