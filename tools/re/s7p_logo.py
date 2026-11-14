"""s7p_logo - the two-line italic 'STARS' team logos of GAME/BINDNAME.BIN (white face, blue rim, black outline + shadow).
Used for 14029 (BINDNAME [141]) 'sakatsuku STARS' -> 'SAKATSUKU / STARS'; 's7p_logo.py --test' renders BALKAN / STARS
(BINDNAME [140]) with the same code next to the original to prove the style match.
  python -I -X utf8 tools/re/s7p_logo.py [--test] [--write]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import arttext, pvr
import s7p_plates as P

S = 4
FACE_T, FACE_B = (255, 255, 255), (226, 226, 255)
BLUE = (16, 16, 236)
SHEAR = 0.0           # the italic face carries the slant


def layer(text, alias, size, sx, x_left, x_right, base_y, stroke):
    """L mask (128*S) of the text with a `stroke` px round outline, sheared, squashed to fit [x_left, x_right] (face ink)."""
    path, _ = arttext.resolve_font(alias)
    font = ImageFont.truetype(path, int(round(size * S)))
    return font, path


def draw_line(text, alias, cap_px, x_left, x_right, base_y):
    path, _ = arttext.resolve_font(alias)
    # em size from the cap height (cap ~ 0.716 em for Arial)
    em = cap_px / 0.716
    font = ImageFont.truetype(path, int(round(em * S)))
    bb = font.getbbox(text, anchor='ls')
    wface = (bb[2] - bb[0]) / S + cap_px * SHEAR          # sheared width
    sx = (x_right - x_left) / wface              # the art is extended: stretch as well as squash
    out = {}
    for name, sw in (('face', 0.0), ('blue', 1.2), ('black', 2.2)):
        im = Image.new('L', (128 * S * 2, 128 * S), 0)
        d = ImageDraw.Draw(im)
        d.text((40 * S - bb[0], base_y * S), text, font=font, fill=255, anchor='ls', stroke_width=int(round(sw * S)), stroke_fill=255)
        # shear about the baseline
        k = SHEAR
        im = im.transform(im.size, Image.AFFINE, (1, k, -k * base_y * S, 0, 1, 0), Image.BICUBIC)
        a = np.asarray(im)
        xs = np.where(np.asarray(Image.fromarray(a)).max(0) > 8)[0]
        out[name] = a
    # squash + placement: find face ink extents
    fa = out['face']
    xs = np.where(fa.max(0) > 8)[0]
    x0, x1 = xs[0], xs[-1] + 1
    res = {}
    for name, a in out.items():
        crop = Image.fromarray(a)
        nw = int(round(crop.size[0] * sx))
        crop = crop.resize((nw, crop.size[1]), Image.LANCZOS)
        arr = np.asarray(crop)
        fx0 = int(round(x0 * sx))
        fx1 = int(round(x1 * sx))
        left = int(round((x_left + ((x_right - x_left) - (fx1 - fx0) / S) / 2) * S)) - fx0
        m = np.zeros((128 * S, 128 * S), np.uint8)
        for xd in range(max(0, left), min(128 * S, left + arr.shape[1])):
            m[:, xd] = arr[:, xd - left]
        res[name] = m
    return res


def compose(lines):
    face = np.zeros((128 * S, 128 * S)); blue = np.zeros_like(face); black = np.zeros_like(face)
    for (text, alias, cap, xl, xr, by) in lines:
        r = draw_line(text, alias, cap, xl, xr, by)
        face = np.maximum(face, r['face'] / 255.0)
        blue = np.maximum(blue, r['blue'] / 255.0)
        black = np.maximum(black, r['black'] / 255.0)
    o = 2 * S
    shadow = np.zeros_like(black)
    for d in range(1, 3):
        sh = np.zeros_like(black)
        sh[d * S:, d * S:] = black[:-d * S, :-d * S]
        shadow = np.maximum(shadow, sh)
    H = 128 * S
    yy = np.arange(H, dtype=float)[:, None] / S
    # gradient only over the logo rows
    t = np.clip((yy - 15) / 40.0, 0, 1)
    fcol = np.zeros((H, H, 3))
    for c in range(3):
        fcol[..., c] = (FACE_T[c] + (FACE_B[c] - FACE_T[c]) * t)
    rgb = np.zeros((H, H, 3)); a = np.zeros((H, H))
    def over(col, al):
        nonlocal rgb, a
        # premultiplied "over"
        rgb = col * al[..., None] + rgb * (1 - al[..., None])
        a = al + a * (1 - al)
    over(np.zeros((H, H, 3)), shadow)
    over(np.zeros((H, H, 3)), black)
    over(np.broadcast_to(np.array(BLUE, float), (H, H, 3)), blue)
    over(fcol, face)
    pm = np.concatenate([rgb, a[..., None]], -1).reshape(128, S, 128, S, 4).mean((1, 3))
    al = pm[..., 3]
    col = np.where(al[..., None] > 1e-6, pm[..., :3] / np.maximum(al[..., None], 1e-6), 0)
    return np.clip(np.rint(np.concatenate([col, al[..., None] * 255], -1)), 0, 255).astype(np.uint8)


JOBS = {
    'test': [('BALKAN', 'arial-bold-italic', 15, 7, 118, 32), ('STARS', 'arial-bold-italic', 12, 29, 112, 48)],
    'sakatsuku': [('SAKATSUKU', 'arial-bold-italic', 15, 7, 118, 32), ('STARS', 'arial-bold-italic', 12, 29, 112, 48)],
}


def main(argv):
    out = os.path.join(ROOT, 'build', 's7', 'p', 'out'); os.makedirs(out, exist_ok=True)
    for key, tid in (('test', '[140]'), ('sakatsuku', '[141]')):
        if key == 'test' and '--test' not in argv and '--all' not in argv:
            continue
        img = compose(JOBS[key])
        orig = P.load_orig(P.NAME_FILE, tid)
        enc, K, over = P.encode_fit(img, orig, P.NAME_FILE, tid)
        print(key, 'codebook', K, 'over', over)
        if over:
            raise SystemExit('does not fit')
        dec = np.asarray(pvr.decode(enc))
        ob = np.asarray(pvr.decode(orig))
        pair = Image.new('RGB', (128 * 2 + 4, 128), (30, 30, 30))
        pair.paste(P.on_blue(ob), (0, 0)); pair.paste(P.on_blue(dec), (132, 0))
        pair.resize((pair.size[0] * 3, 384), Image.NEAREST).save(os.path.join(out, 'logo_%s_ba.png' % key))
        print(key, 'alpha err', float(np.abs(dec[..., 3].astype(int) - img[..., 3].astype(int)).mean()))
        if key == 'sakatsuku':
            if '--write' in argv:
                m = P.load_manifest(); rep = []
                P.write_tex(P.NAME_FILE, tid, enc, m, rep); P.save_manifest(m); print(rep or 'written')


if __name__ == '__main__':
    main(sys.argv[1:])
