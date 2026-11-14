"""s7g_dump: extract + decode the tag / FACEMDUL originals to build/s7g/orig (pvr + png on a grey chequer, x3 preview)."""
import os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr, texinject
JOBS = {
 '34703': ('GAME/GAMEETC.ZAR', '@110/ktss03.pvr'),
 '34708': ('GAME/GAMEETC.ZAR', '@110/pk_parts1.pvr'),
 '34716': ('GAME/GAMEETC.ZAR', '@110/sakusen.pvr'),
 '34719': ('GAME/GAMEETC.ZAR', '@110/sk_parts2.pvr'),
 '34723': ('GAME/GAMEETC.ZAR', '@110/taisenhyoji.pvr'),
 '00056': ('ATFIRST/FACEMDUL.DAT', '@cb7e0/kao_g_dai.pvr'),
 '00062': ('ATFIRST/FACEMDUL.DAT', '@cb7e0/kao_r_toku.pvr'),
 '00065': ('ATFIRST/FACEMDUL.DAT', '@cb7e0/kao_y_gou.pvr'),
}
def flat(a, bg=(70, 70, 110)):
    im = Image.fromarray(a.astype(np.uint8), 'RGBA')
    b = Image.new('RGBA', im.size, bg + (255,))
    b.alpha_composite(im)
    return b.convert('RGB')
if __name__ == '__main__':
    for k, (f, t) in JOBS.items():
        d = texinject.extract_pvr(f, t)
        open(os.path.join(ROOT, 'build', 's7g', 'orig', k + '.pvr'), 'wb').write(d)
        a = np.asarray(pvr.decode(d)).copy()
        pvr.to_png(a, os.path.join(ROOT, 'build', 's7g', 'orig', k + '.png'))
        im = flat(a)
        im = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
        im.save(os.path.join(ROOT, 'build', 's7g', 'orig', k + '_x3.png'))
        print(k, a.shape)
