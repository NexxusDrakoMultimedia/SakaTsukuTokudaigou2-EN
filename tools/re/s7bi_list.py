"""s7bi_list: print package I members (id, member) from groups_v3.json; montage the originals to build/s7bi/orig_NN.png."""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7c_dump as D
ROOT = D.ROOT
d = json.load(open(os.path.join(ROOT, 'build/art/groups_v3.json'), encoding='utf8'))
pk = [p for p in d['packages'] if p['key'] == 'I'][0]
items = [(i['id'], i['member'][:-4]) for i in pk['items']]
if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'build/s7bi'), exist_ok=True)
    for k in range(0, len(items), 6):
        chunk = items[k:k + 6]
        W = 3
        c = Image.new('RGB', (W * 260, 2 * 262), (40, 0, 40))
        for j, (tid, m) in enumerate(chunk):
            pv, a = D.load(m)
            ys, xs = np.nonzero(a[..., 3] > 40)
            print(tid, m, a.shape, 'ink', xs.min(), ys.min(), xs.max(), ys.max())
            im = Image.fromarray(a.astype(np.uint8), 'RGBA')
            bg = Image.new('RGBA', im.size, (90, 90, 110, 255)); bg.alpha_composite(im)
            t = bg.convert('RGB').resize((256, 256), Image.NEAREST)
            ImageDraw.Draw(t).text((2, 2), tid + ' ' + m, fill=(255, 255, 0))
            c.paste(t, ((j % W) * 260, (j // W) * 262))
        c.save(os.path.join(ROOT, 'build/s7bi/orig_%02d.png' % (k // 6)))
