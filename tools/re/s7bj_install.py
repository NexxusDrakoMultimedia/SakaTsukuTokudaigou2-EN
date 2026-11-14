"""s7bj_install [--write] ID ... : encode build/s7/titles/new/ID.png into the texture's own format, check that every
identical copy fits its slot (texinject policy 'exact'), and with --write install the file for every copy under
translation/textures (existing files are backed up to build/s7/bak/ first).  Also writes the preview of the
re-decoded texture to build/s7/titles/dec/ID.png."""
import os
import sys
import shutil
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L  # noqa: E402
import pvr  # noqa: E402
import texinject  # noqa: E402

ROOT = L.ROOT
NEW = os.path.join(ROOT, 'build', 's7', 'titles', 'new')
DEC = os.path.join(ROOT, 'build', 's7', 'titles', 'dec')
BAK = os.path.join(ROOT, 'build', 's7', 'bak')


SPECIAL = {'00056': ('ATFIRST/FACEMDUL.DAT', '@cb7e0/kao_g_dai.pvr'), '00062': ('ATFIRST/FACEMDUL.DAT', '@cb7e0/kao_r_toku.pvr'),
           '00065': ('ATFIRST/FACEMDUL.DAT', '@cb7e0/kao_y_gou.pvr')}


def load(i):
    if i in SPECIAL:
        src, tid = SPECIAL[i]
        pv = texinject.extract_pvr(os.path.join(ROOT, 'extracted', *src.split('/')), tid)
        return dict(src=src, tid=tid, pvr=pv)
    return L.load(i)


def main():
    args = sys.argv[1:]
    write = '--write' in args
    ids = [a for a in args if not a.startswith('--')]
    os.makedirs(DEC, exist_ok=True)
    for i in ids:
        t = load(i)
        arr = np.asarray(Image.open(os.path.join(NEW, i + '.png')).convert('RGBA'))
        new = pvr.encode(arr, original=t['pvr'])
        dec = pvr.decode(new)
        Image.fromarray(np.asarray(dec)).save(os.path.join(DEC, i + '.png'))
        copies = L.dups(t['src'], t['tid'])
        rep = L.fit_report(new, t)
        print(i, t['src'], t['tid'], 'copies:', copies)
        for r in rep:
            print('   fit', r)
        if not all(r[2] for r in rep):
            print('   NOT WRITTEN (does not fit)')
            continue
        if write:
            for src, tid in copies:
                p = L.tex_path(src, tid)
                if os.path.exists(p):
                    b = os.path.join(BAK, 's7bj', *src.split('/'))
                    os.makedirs(b, exist_ok=True)
                    shutil.copy2(p, os.path.join(b, tid + '.pvr'))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'wb') as f:
                    f.write(new)
                print('   wrote', p)


if __name__ == '__main__':
    main()
