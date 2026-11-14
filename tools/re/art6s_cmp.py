import sys, glob, os
sys.path.insert(0, 'tools')
import numpy as np
from PIL import Image
import pvr
M = [('00165','ETC_DATA/BMMAIN.TBD/#0'),('00167','ETC_DATA/BMMAIN.TBD/#2'),('00169','ETC_DATA/BPMATCH.TBD/#0'),
('00170','ETC_DATA/BPMATCH.TBD/#1'),('03266','ETC_DATA/MEETING.ZAR/pvr.tbd#0'),('36800','GAME2/GM_SHORT.TBD/#0'),
('36802','GAME2/SS_EDIT.TBD/#0'),('36805','GAME2/SS_EDIT.TBD/#3'),('37277','TRAINING/PLSEL.TBD/#5'),
('37281','TRAINING/PLSEL.TBD/#9'),('37289','TRAINING/TRAINING.TBD/#4'),('37292','TRAINING/TRAINING.TBD/#7'),
('37293','TRAINING/TRAINING.TBD/#8'),('37300','TRAINING/TUTO_BF.TBD/#0')]
def chk(im, c=8):
    h, w = im.shape[:2]
    y, x = np.mgrid[0:h, 0:w]
    g = np.where(((x//c)+(y//c)) % 2 == 0, 70, 110).astype(np.float32)
    bg = np.stack([g, g*1.1, g], -1)
    a = im[..., 3:4].astype(np.float32)/255
    return (im[..., :3]*a + bg*(1-a)).clip(0, 255).astype(np.uint8)
for tid, p in M:
    new = pvr.decode(open('translation/textures/%s.pvr' % p, 'rb').read())
    orig = np.array(Image.open(glob.glob('build/tex/*/%s_*.png' % tid)[0]).convert('RGBA'))
    print(tid, new.shape, orig.shape, 'changed px', int((new != orig).any(-1).sum()),
          'alpha changed', int((new[...,3] != orig[...,3]).sum()))
    Image.fromarray(np.concatenate([chk(orig), np.full((orig.shape[0], 4, 3), 255, np.uint8), chk(new)], 1)).save('build/art6s/%s.png' % tid)
