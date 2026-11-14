"""tex_zoom - composite decoded texture PNGs over grey and write them (optionally upscaled) for viewing.

    python -I -X utf8 tools/tex_zoom.py OUT.png [scale] ID_OR_PNG_PATH ...

Ids are the 5-digit serial prefix (e.g. 3541) resolved via build/tex/index.tsv. Output goes under build/tex/classify/.
"""
import os
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'build', 'tex')


def find(sid):
    with open(os.path.join(TEX, 'index.tsv'), encoding='utf8') as f:
        for ln in f:
            c = ln.split('\t')
            if c[0].startswith('%05d_' % int(sid)):
                return os.path.join(TEX, c[1].replace('/', '__'), c[0] + '.png')
    raise SystemExit('no id %s' % sid)


def main():
    out = os.path.join(TEX, 'classify', sys.argv[1])
    scale = float(sys.argv[2])
    ims = []
    for a in sys.argv[3:]:
        p = a if os.path.exists(a) else find(a)
        im = Image.open(p).convert('RGBA')
        bg = Image.new('RGBA', im.size, (128, 128, 128, 255))
        bg.alpha_composite(im)
        if scale != 1:
            bg = bg.resize((int(bg.width * scale), int(bg.height * scale)), Image.LANCZOS)
        ims.append(bg)
    W = sum(i.width for i in ims) + 8 * (len(ims) - 1)
    H = max(i.height for i in ims)
    sheet = Image.new('RGBA', (W, H), (60, 60, 60, 255))
    x = 0
    for i in ims:
        sheet.paste(i, (x, 0))
        x += i.width + 8
    sheet.convert('RGB').save(out)
    print(out, sheet.size)


main()
