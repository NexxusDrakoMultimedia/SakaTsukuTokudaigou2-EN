"""s7bj_lib: small raster helpers for the title-logo repaint (numpy + Pillow, no arttext).

  inpaint(arr, mask)             diffusion fill of the masked pixels from their surroundings
  render_text(...)               supersampled text with fill / gradient / outlines / shadow / shear -> RGBA layer
  paste_text(img, box, text, ..) fit text into a box and composite it onto an RGBA PIL image
"""
import os
import numpy as np
from PIL import Image, ImageFont, ImageDraw, ImageFilter, ImageChops

FONTS = {
    'impact': 'C:/WINDOWS/Fonts/impact.ttf',
    'arial-black': 'C:/WINDOWS/Fonts/ariblk.ttf',
    'arial-bold': 'C:/WINDOWS/Fonts/arialbd.ttf',
    'arial-narrow-bold': 'C:/WINDOWS/Fonts/ARIALNB.TTF',
    'franklin-condensed': 'C:/WINDOWS/Fonts/FRAMDCN.TTF',
    'bahnschrift': 'C:/WINDOWS/Fonts/bahnschrift.ttf',
    'segoe-black': 'C:/WINDOWS/Fonts/seguibl.ttf',
    'trebuchet-bold': 'C:/WINDOWS/Fonts/trebucbd.ttf',
}


def hexc(c, a=255):
    if isinstance(c, (tuple, list)):
        return tuple(c) + ((a,) if len(c) == 3 else ())
    c = c.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


def inpaint(arr, mask, iters=500):
    """Diffusion fill: masked pixels become the average of their 8 neighbours, known pixels stay (RGB only; alpha copied
    from the nearest ring by the same diffusion)."""
    a = arr.astype(np.float32).copy()
    m = mask.astype(bool)
    # initial guess: mean of the known pixels around
    known = ~m
    if known.any():
        a[m] = a[known].mean(axis=0)
    for it in range(iters):
        p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode='edge')
        s = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) * 2 + p[:-2, :-2] + p[:-2, 2:] + p[2:, :-2] + p[2:, 2:]
        a[m] = (s / 12.0)[m]
    return np.clip(a + 0.5, 0, 255).astype(np.uint8)


def dilate(mask, r):
    im = Image.fromarray((mask * 255).astype(np.uint8))
    if r > 0:
        im = im.filter(ImageFilter.MaxFilter(2 * r + 1))
    return np.asarray(im) > 127


def _font(name, px):
    return ImageFont.truetype(FONTS.get(name, name), px)


def render_text(text, size_wh, font='impact', ss=4, fill='#ffffff', gradient=None, outlines=(), shadow=None,
                shear=0.0, bold=0, align='center', valign='middle', max_h=None, min_sx=0.6, margin=0, letter_spacing=0):
    """Fit `text` into a (w, h) box (the box includes outlines and shadow) -> RGBA PIL image of size (w, h).
    outlines = [(colour, width_px), ...] drawn widest first.  shadow = (colour, dx, dy) hard extrusion copy.
    The glyph size is the largest that fits; if the width does not fit, the glyphs are squashed down to min_sx."""
    w, h = size_wh
    import math
    ow = int(math.ceil(max([o[1] for o in outlines] + [0])))
    sdx, sdy = (shadow[1], shadow[2]) if shadow else (0, 0)
    padx = ow + abs(sdx) + margin
    pady = ow + abs(sdy) + margin
    gw, gh = (w - 2 * padx) * ss, (h - 2 * pady) * ss
    # find largest font px whose glyph height fits
    def mask_for(px):
        f = _font(font, px)
        if letter_spacing:
            bbs = []
            x = 0
            m = Image.new('L', (int(px * len(text) * 1.5) + 40, int(px * 2) + 40), 0)
            d = ImageDraw.Draw(m)
            for ch in text:
                d.text((20 + x, 20), ch, font=f, fill=255)
                x += d.textlength(ch, font=f) + letter_spacing * ss
        else:
            m = Image.new('L', (int(f.getlength(text)) + 80, int(px * 2) + 40), 0)
            d = ImageDraw.Draw(m)
            d.text((20, 20), text, font=f, fill=255)
        if bold:
            m = m.filter(ImageFilter.MaxFilter(2 * bold * ss // 2 * 2 + 1)) if bold * ss >= 1 else m
        bb = m.getbbox()
        return m.crop(bb)
    lo, hi = 8, 1200
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        m = mask_for(mid)
        if m.height <= gh and (max_h is None or m.height <= max_h * ss):
            best = m
            lo = mid + 1
        else:
            hi = mid - 1
    m = best if best is not None else mask_for(8)
    # shear
    if shear:
        sh = int(m.height * shear)
        m2 = Image.new('L', (m.width + sh, m.height), 0)
        m2 = m.transform(m2.size, Image.AFFINE, (1, shear, -sh, 0, 1, 0), resample=Image.BICUBIC)
        m = m2
    # squash to fit width
    if m.width > gw:
        sx = max(gw / m.width, min_sx)
        m = m.resize((max(1, int(m.width * sx)), m.height), Image.LANCZOS)
        if m.width > gw:  # still too wide: scale uniformly
            s = gw / m.width
            m = m.resize((int(m.width * s), max(1, int(m.height * s))), Image.LANCZOS)
    W, H = w * ss, h * ss
    ox = padx * ss + {'left': 0, 'center': (gw - m.width) // 2, 'right': gw - m.width}[align]
    oy = pady * ss + {'top': 0, 'middle': (gh - m.height) // 2, 'bottom': gh - m.height}[valign]
    glyph = Image.new('L', (W, H), 0)
    glyph.paste(m, (ox, oy))
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if shadow:
        sm = ImageChops.offset(glyph, sdx * ss, sdy * ss)
        # extrusion: stack
        steps = max(abs(sdx), abs(sdy)) * ss
        acc = Image.new('L', (W, H), 0)
        for k in range(steps + 1):
            acc = ImageChops.lighter(acc, ImageChops.offset(glyph, int(sdx * ss * k / max(steps, 1)), int(sdy * ss * k / max(steps, 1))))
        if ow:
            acc = acc.filter(ImageFilter.MaxFilter(2 * ow * ss + 1))
        layer.paste(Image.new('RGBA', (W, H), hexc(shadow[0])), (0, 0), acc)
    for col, wd in sorted(outlines, key=lambda o: -o[1]):
        om = glyph.filter(ImageFilter.MaxFilter(2 * int(wd * ss) + 1)) if wd > 0 else glyph
        layer.paste(Image.new('RGBA', (W, H), hexc(col)), (0, 0), om)
    if gradient:
        bb = glyph.getbbox() or (0, 0, W, H)
        ys = np.arange(H)
        t = np.clip((ys - bb[1]) / max(1, bb[3] - bb[1]), 0, 1)
        ts = [g[0] for g in gradient]
        cs = np.array([hexc(g[1])[:3] for g in gradient], float)
        col = np.stack([np.interp(t, ts, cs[:, k]) for k in range(3)], axis=1)
        fillimg = np.zeros((H, W, 4), np.uint8)
        fillimg[..., :3] = col[:, None, :].astype(np.uint8)
        fillimg[..., 3] = 255
        layer.paste(Image.fromarray(fillimg), (0, 0), glyph)
    else:
        layer.paste(Image.new('RGBA', (W, H), hexc(fill)), (0, 0), glyph)
    # premultiplied box downsample
    a = np.asarray(layer).astype(np.float32)
    pm = a[..., :3] * (a[..., 3:4] / 255.0)
    pm = pm.reshape(h, ss, w, ss, 3).mean(axis=(1, 3))
    al = a[..., 3].reshape(h, ss, w, ss).mean(axis=(1, 3))
    rgb = np.where(al[..., None] > 0, pm / np.maximum(al[..., None], 1e-6) * 255.0, 0)
    out = np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def paste_text(img, box, text, **kw):
    x, y, w, h = box
    lay = render_text(text, (w, h), **kw)
    img.alpha_composite(lay, (x, y))
    return lay
