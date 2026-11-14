"""Smoke test: decode a sample of textures to PNGs under build/textures/smoke/ and time everything."""
import os
import sys
import time
import hashlib
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import pvr  # noqa: E402
import pvr_scan  # noqa: E402


def main():
    out = os.path.join('build', 'textures', 'smoke')
    os.makedirs(out, exist_ok=True)
    seen = set()
    samples = collections.defaultdict(list)
    stats = collections.Counter()
    fails = []
    t0 = time.time()

    def on(t):
        if t.kind == 'PVP' or t.payload is None:
            return
        key = hashlib.md5(bytes([t.pix, t.dat]) + t.w.to_bytes(2, 'little') + t.h.to_bytes(2, 'little') + t.payload).digest()
        if key in seen:
            stats['dup'] += 1
            return
        seen.add(key)
        stats['unique'] += 1
        try:
            img = pvr.decode(t.payload, t.pix, t.dat, t.w, t.h)
            assert img.shape == (t.h, t.w, 4)
            stats['ok'] += 1
        except Exception as e:  # noqa
            fails.append((t.path, t.index, t.pix, t.dat, t.w, t.h, repr(e)))
            return
        k = (t.pix, t.dat)
        if len(samples[k]) < 6:
            samples[k].append((t, img))

    pvr_scan.scan_all('extracted', on_texture=on, keep_rows=False)
    print('decode time %.1fs' % (time.time() - t0), dict(stats))
    for f in fails[:20]:
        print('FAIL', f)
    print('fails', len(fails))
    from PIL import Image
    for (pix, dat), lst in sorted(samples.items()):
        tiles = []
        for t, img in lst:
            im = Image.fromarray(img, 'RGBA')
            bg = Image.new('RGBA', im.size, (255, 0, 255, 255))
            bg.alpha_composite(im)
            im = bg.convert('RGB')
            s = 128 / max(im.size)
            if s < 1:
                im = im.resize((max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))), Image.NEAREST)
            tiles.append(im)
        W = sum(i.size[0] + 4 for i in tiles)
        H = max(i.size[1] for i in tiles)
        sheet = Image.new('RGB', (W, H), (40, 40, 40))
        x = 0
        for i in tiles:
            sheet.paste(i, (x, 0))
            x += i.size[0] + 4
        sheet.save(os.path.join(out, 'pix%d_dat%02x.png' % (pix, dat)))
    print('wrote', len(samples), 'sheets')


main()
