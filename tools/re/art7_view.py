"""art7_view: montage of decoded textures by 5-digit id. usage: art7_view.py OUT.png SCALE COLS id [id ...]
ids resolve through build/tex/index.tsv; images from build/tex/<source with / -> __>/<member?>/<id>*.png (searched by glob).
Optional env ART7_DIR to read repainted PNGs instead (build/art7/out/<id>.png) when id has a trailing 'o'."""
import sys, os, glob
from PIL import Image, ImageDraw
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
def find(i):
    if i.endswith('o'):
        return os.path.join(ROOT, 'build', 'art7', 'out', i[:-1] + '.png')
    if i.endswith('n'):
        return os.path.join(ROOT, 'build', 'art7', 'new', i[:-1] + '.png')
    g = glob.glob(os.path.join(ROOT, 'build', 'tex', '*', i + '_*.png')) + glob.glob(os.path.join(ROOT, 'build', 'tex', i + '_*.png'))
    return g[0]
def main():
    out, scale, cols = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    ids = sys.argv[4:]
    ims = []
    for i in ids:
        im = Image.open(find(i)).convert('RGBA')
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.NEAREST)
        ims.append((i, im))
    cw = max(im.width for _, im in ims) + 6
    ch = max(im.height for _, im in ims) + 18
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGBA', (cw * cols, ch * rows), (70, 90, 70, 255))
    d = ImageDraw.Draw(sheet)
    for k, (i, im) in enumerate(ims):
        x, y = (k % cols) * cw, (k // cols) * ch
        d.text((x + 2, y + 2), i, fill=(255, 255, 0, 255))
        # checker-less: gray bg to show alpha
        bg = Image.new('RGBA', im.size, (110, 110, 130, 255))
        bg.alpha_composite(im)
        sheet.paste(bg, (x + 2, y + 16))
    sheet.convert('RGB').save(out)
main()
