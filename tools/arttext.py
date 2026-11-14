#!/usr/bin/env python
"""arttext.py - repaint Japanese baked into game textures with English.

Pure image side of the "image translation" workflow (see docs/art-translation.md).
It works on a decoded RGBA PNG and knows nothing about PVR/ZSARC: decode the texture
first (tools/pvr.py, once it exists), run this, then re-encode and inject.

    python -I -X utf8 tools/arttext.py SPEC.json IN.png OUT.png [--sheet before_after.png]
    python -I -X utf8 tools/arttext.py --list-fonts

Pipeline per region (in spec order):
  1. ERASE  the old art inside the region (or `erase_rect`) by inpainting from the
            surrounding pixels (modes: flat, hgrad, vgrad, coons, mask, auto, copy,
            plate, clear).
  2. DRAW   the English text: font + auto-fit, colour or gradient fill, outline,
            drop shadow / extrusion, italic shear, horizontal squash, alignment.
            Rendered at `supersample` x (default 4) and box-filtered down, so edges
            are antialiased; `"aa": false` gives hard 1-bit alpha for cut-out textures.
  3. QUANTIZE (optional, `quantize` key) the touched rectangles to the target pixel
            format (argb4444 / rgb565 / argb1555) so the PNG already looks like what
            the Dreamcast will show.

Fonts are looked up by alias among the fonts installed on the machine (Windows
Fonts directory first).  Nothing is copied into the repository; text is rendered at
build time.  `--list-fonts` shows which aliases resolve here.

SPEC (JSON)
{
  "texture": "free text id, informational",
  "size": [W, H],                    # optional; verified against the input image
  "supersample": 4,                  # 1..8
  "quantize": "argb4444",            # optional preview/snap of touched rects
  "styles":   { "name": {...style...} },   # extra/overriding named styles
  "defaults": { ...region keys applied to every region... },
  "regions": [
    { "id": "kanji_tab", "ja": "漢字", "text": "Kanji",      # ja is only for the glossary check
      "x": 66, "y": 6, "w": 150, "h": 52,                    # paint rectangle (clips drawing)
      "erase": {...} | [{...},{...}] | "auto" | null,        # see below
      "erase_rect": [x, y, w, h], "erase_grow": n | [l,t,r,b],  # default: the region rectangle
      "style": "menu_label" | {...inline style...},          # plus any style key inline
      "font": "arial-black" | ["a","b"] | "C:/x.ttf",
      "size": 30 | "auto", "max_size": 40, "min_size": 8,    # px, auto = fit to region
      "min_sx": 0.8,         # auto-fit may squash horizontally down to this before shrinking
      "wrap": false, "line_spacing": 1.0,
      "align": "center|left|right", "valign": "middle|top|bottom",
      "pad": 1, "dx": 0, "dy": 0 }
  ]
}

STYLE keys (all optional; colours are "#rrggbb[aa]" or [r,g,b(,a)])
  fill        colour                       | "gradient": [[t, colour], ...]  (t 0 = top of ink, 1 = bottom;
                                              equal t values make a hard split)
  outline     {"color": c, "width": px}    (rounded, drawn outside the glyph)
  shadow      {"color": c, "dx": px, "dy": px, "blur": px, "alpha": 0..1, "steps": n}
              steps > 1 stacks copies between 0 and (dx,dy): the solid extruded look of the game headings
  highlight   {"color": c, "alpha": 0..1, "height": 0..1}  light band over the top part of the fill
  shear       0.0-0.5  italic slant        | "bold": px  fattens the glyphs | "letter_spacing": px
  opacity     0..1                         | "aa": true/false

ERASE ops  (an "erase" object/list; every op has "mode")
  flat    {"color": [r,g,b(,a)]}      fill with a colour (default: median of a 2px ring around the rect)
  hgrad   linear ramp left->right between the pixels just outside the rect, row by row
  vgrad   linear ramp top->bottom between the pixels just outside the rect, column by column
  coons   all four edges blended (bilinear Coons patch); best for smooth plates
  mask    build a mask of the old ink inside the rect and inpaint only those pixels:
            "ink": {cond...} | [{cond...}, ...]   a dict is AND, a list is OR
               conds: luma_gt, luma_lt, alpha_gt, alpha_lt, sat_gt, sat_lt,
                      color [r,g,b] + tol, bg [r,g,b]|null + bg_dist_gt (null = ring median),
                      rects [[x,y,w,h]..] (texture coords), mask_png "file.png" (white = ink,
                      texture-sized or rect-sized, relative to the spec file)
            "dilate": n (grow the mask n px, catches antialiased fringes), "exclude": [[x,y,w,h]..]
            "fill": diffuse (default, harmonic) | hfill | vfill | hvfill | flat | coons
            "relax": iterations of smoothing for diffuse (default 80)
  auto    mask op shortcut for a plain background: ink = differs from the ring median by more
          than "tol" (default 40), dilate 2, diffuse fill
  copy    {"src": [x, y]} copy a same-sized rect from elsewhere in the texture (a clean patch)
  plate   {"path": "clean.png", "replace": false} paste a hand-made clean plate at the rect origin
  clear   set the rect to fully transparent
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --------------------------------------------------------------------------- fonts

# alias -> candidate file names (first one that exists wins).  Generic fall-backs at the end
# of the bold ones keep the tool usable on non-Windows machines.
_GENERIC_BOLD = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf", "Helvetica.ttc"]
FONT_ALIASES = {
    "arial-black": ["ariblk.ttf"] + _GENERIC_BOLD,
    "impact": ["impact.ttf"] + _GENERIC_BOLD,
    "verdana-bold": ["verdanab.ttf"] + _GENERIC_BOLD,
    "verdana-bold-italic": ["verdanaz.ttf"] + _GENERIC_BOLD,
    "segoe-ui": ["segoeui.ttf", "DejaVuSans.ttf"],
    "segoe-ui-semibold": ["seguisb.ttf", "segoeuib.ttf"] + _GENERIC_BOLD,
    "segoe-ui-bold": ["segoeuib.ttf"] + _GENERIC_BOLD,
    "segoe-ui-bold-italic": ["segoeuiz.ttf"] + _GENERIC_BOLD,
    "segoe-ui-black": ["seguibl.ttf", "segoeuib.ttf"] + _GENERIC_BOLD,
    "arial": ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
    "arial-bold": ["arialbd.ttf"] + _GENERIC_BOLD,
    "arial-bold-italic": ["arialbi.ttf"] + _GENERIC_BOLD,
    "arial-narrow-bold": ["ARIALNB.TTF", "arialbd.ttf"] + _GENERIC_BOLD,
    "tahoma-bold": ["tahomabd.ttf"] + _GENERIC_BOLD,
    "trebuchet-bold": ["trebucbd.ttf"] + _GENERIC_BOLD,
    "franklin-gothic": ["framd.ttf"] + _GENERIC_BOLD,
    "franklin-gothic-condensed": ["FRAMDCN.TTF", "framd.ttf"] + _GENERIC_BOLD,
    "gothic-bold": ["GOTHICB.TTF"] + _GENERIC_BOLD,
    "bahnschrift": ["bahnschrift.ttf"] + _GENERIC_BOLD,
    "calibri-bold": ["calibrib.ttf"] + _GENERIC_BOLD,
    "comic-sans-bold": ["comicbd.ttf"] + _GENERIC_BOLD,
    "georgia-bold": ["georgiab.ttf"] + _GENERIC_BOLD,
    "sans-bold": ["arialbd.ttf"] + _GENERIC_BOLD,
}

_font_index = None
_font_cache = {}


def _font_dirs():
    dirs = []
    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if windir:
        dirs.append(os.path.join(windir, "Fonts"))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))
    dirs += ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
             os.path.expanduser("~/.local/share/fonts"), "/Library/Fonts", "/System/Library/Fonts",
             os.path.expanduser("~/Library/Fonts")]
    return [d for d in dirs if os.path.isdir(d)]


def _index_fonts():
    global _font_index
    if _font_index is None:
        _font_index = {}
        for d in _font_dirs():
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower().endswith((".ttf", ".otf", ".ttc")):
                        _font_index.setdefault(f.lower(), os.path.join(root, f))
    return _font_index


def resolve_font(spec):
    """spec: alias | file name | path | list of those.  Returns (path, label)."""
    cands = spec if isinstance(spec, (list, tuple)) else [spec]
    idx = _index_fonts()
    for c in cands:
        c = str(c)
        if c.startswith("path:"):
            c = c[5:]
        if os.path.isfile(c):
            return c, c
        names = FONT_ALIASES.get(c.lower(), [c])
        for n in names:
            p = idx.get(n.lower())
            if p:
                return p, c
    return None, None


def load_font(spec, px, warnings):
    path, label = resolve_font(spec)
    if path is None:
        warnings.append("font %r not found, using Pillow default (check --list-fonts)" % (spec,))
        return ImageFont.load_default(px), "pillow-default"
    key = (path, px)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, px)
    return _font_cache[key], os.path.basename(path)


def list_fonts():
    print("font search dirs: %s" % ", ".join(_font_dirs()))
    for alias in sorted(FONT_ALIASES):
        path, _ = resolve_font(alias)
        first = FONT_ALIASES[alias][0].lower()
        exact = path is not None and os.path.basename(path).lower() == first
        print("  %-24s %-6s %s" % (alias, "ok" if exact else ("FALLBACK" if path else "MISSING"), path or ""))


# --------------------------------------------------------------------------- colours

def parse_color(c, default=(255, 255, 255, 255)):
    if c is None:
        return default
    if isinstance(c, str):
        s = c.lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) == 6:
            s += "ff"
        if len(s) != 8:
            raise ValueError("bad colour %r" % c)
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4, 6))
    c = list(c)
    if len(c) == 3:
        c.append(255)
    return tuple(int(v) for v in c)


# --------------------------------------------------------------------------- style presets

# Looks measured from build/emu/live1.png..live3.png (Club Edit screens).
PRESETS = {
    # pale cyan italic labels with black outline and black block shadow on the blue tabs
    "menu_label": {
        "font": ["segoe-ui-bold", "verdana-bold", "arial-bold"], "shear": 0.22,
        "gradient": [[0, "#c8ffff"], [1, "#98e0ec"]],
        "outline": {"color": "#000000", "width": 1.2},
        "shadow": {"color": "#000000", "dx": 2, "dy": 2, "steps": 2, "alpha": 1.0},
    },
    # "Name Entry": pale yellow with an extruded dark-purple shadow
    "heading_yellow": {
        "font": ["bahnschrift", "arial-narrow-bold", "arial-bold"], "bold": 0.4,
        "gradient": [[0, "#f4f4b8"], [0.5, "#e2e2a4"], [0.52, "#d2d28c"], [1, "#c8c884"]],
        "outline": {"color": "#201030", "width": 1},
        "shadow": {"color": "#200030", "dx": 3, "dy": 3, "steps": 3, "alpha": 1.0},
    },
    # "Club Edit": soft blue glass lettering with a deep blue rim
    "heading_blue": {
        "font": ["arial-black", "impact"],
        "gradient": [[0, "#b0b8f4"], [1, "#6c78e0"]],
        "outline": {"color": "#0000a0", "width": 2},
        "shadow": {"color": "#0000a0", "dx": 2, "dy": 3, "blur": 1.5, "alpha": 0.8},
    },
    # "Name" caption: lavender with a dark green drop shadow
    "caption_lavender": {
        "font": ["arial-black", "arial-bold"],
        "fill": "#b4c0e4",
        "outline": {"color": "#202050", "width": 1},
        "shadow": {"color": "#103010", "dx": 1.5, "dy": 1.5, "alpha": 0.9},
    },
    # status-screen stat captions (blood type, birthday ...): white, thin dark outline
    "caption_white": {
        "font": ["segoe-ui-bold", "arial-bold"],
        "fill": "#ffffff", "outline": {"color": "#101840", "width": 1},
        "shadow": {"color": "#000000", "dx": 1, "dy": 1, "alpha": 0.8},
    },
    # "LEVEL UP" style gold/orange pop-ups
    "level_up": {
        "font": ["impact", "arial-black"], "shear": 0.12,
        "gradient": [[0, "#fff6a0"], [0.5, "#ffc830"], [0.52, "#ff9a10"], [1, "#e86800"]],
        "outline": {"color": "#601800", "width": 1.5},
        "shadow": {"color": "#300800", "dx": 2, "dy": 2, "steps": 2, "alpha": 1.0},
    },
    "plain_white": {
        "font": ["arial-bold"], "fill": "#ffffff", "outline": {"color": "#000000", "width": 1},
    },
}


def _merge(a, b):
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


STYLE_KEYS = ("font", "fill", "gradient", "outline", "shadow", "highlight", "shear", "bold",
              "letter_spacing", "opacity", "aa")
REGION_STYLE_KEYS = STYLE_KEYS


def resolve_style(region, spec):
    styles = dict(PRESETS)
    for k, v in (spec.get("styles") or {}).items():
        styles[k] = _merge(styles.get(k, {}), v)
    out = {}
    d = spec.get("defaults") or {}
    for layer in (d, region):
        s = layer.get("style")
        if isinstance(s, str):
            if s not in styles:
                raise ValueError("unknown style %r (known: %s)" % (s, ", ".join(sorted(styles))))
            out = _merge(out, styles[s])
        elif isinstance(s, dict):
            out = _merge(out, s)
        inline = {k: layer[k] for k in STYLE_KEYS if k in layer}
        # an inline plain fill replaces a preset gradient and vice versa
        if "fill" in inline and "gradient" not in inline:
            out.pop("gradient", None)
        if "gradient" in inline and "fill" not in inline:
            out.pop("fill", None)
        out = _merge(out, inline)
    return out


# --------------------------------------------------------------------------- text block

def _text_w(s, font, ls):
    if not s:
        return 0.0
    if ls:
        return sum(font.getlength(ch) for ch in s) + ls * (len(s) - 1)
    return font.getlength(s)


def _wrap(text, font, maxw, ls):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            t = word if not cur else cur + " " + word
            if cur and _text_w(t, font, ls) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = t
        lines.append(cur)
    return lines


def _draw_line(draw, xy, s, font, ls, fill, stroke):
    if not ls:
        draw.text(xy, s, font=font, fill=fill, anchor="la", stroke_width=stroke, stroke_fill=fill)
        return
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=font, fill=fill, anchor="la", stroke_width=stroke, stroke_fill=fill)
        x += font.getlength(ch) + ls


def build_block(text, style, size_px, sx, S, avail_w, wrap, line_spacing, align, warnings):
    """Render the text block at S x scale.  Returns dict with equally sized layers."""
    font, font_name = load_font(style.get("font", "arial-bold"), max(1, int(round(size_px * S))), warnings)
    ls = float(style.get("letter_spacing", 0)) * S
    bold = int(round(float(style.get("bold", 0)) * S))
    ow = int(round(float((style.get("outline") or {}).get("width", 0)) * S))
    lines = _wrap(text, font, (avail_w * S) / max(sx, 0.01), ls) if wrap else text.split("\n")
    asc, desc = font.getmetrics()
    lh = (asc + desc) * line_spacing
    widths = [_text_w(l, font, ls) for l in lines]
    bw = max(widths) if widths else 0
    pad = bold + ow + int(size_px * S * 0.15) + 4
    W = int(math.ceil(bw)) + 2 * pad
    H = int(math.ceil(lh * len(lines) + (asc + desc - lh))) + 2 * pad
    fill_m = Image.new("L", (W, H), 0)
    out_m = Image.new("L", (W, H), 0)
    df, do = ImageDraw.Draw(fill_m), ImageDraw.Draw(out_m)
    for i, l in enumerate(lines):
        w = widths[i]
        x = pad + {"left": 0, "center": (bw - w) / 2, "right": bw - w}[align]
        y = pad + i * lh
        _draw_line(df, (x, y), l, font, ls, 255, bold)
        _draw_line(do, (x, y), l, font, ls, 255, bold + ow)

    shear = float(style.get("shear", 0))
    if shear:
        ext = int(math.ceil(shear * H))
        for_name = []
        for m in (fill_m, out_m):
            for_name.append(m.transform((W + ext, H), Image.AFFINE, (1, shear, -shear * H, 0, 1, 0),
                                        resample=Image.BICUBIC))
        fill_m, out_m = for_name
        W += ext
    if abs(sx - 1.0) > 1e-3:
        nw = max(1, int(round(W * sx)))
        fill_m = fill_m.resize((nw, H), Image.LANCZOS)
        out_m = out_m.resize((nw, H), Image.LANCZOS)
        W = nw

    sil = out_m if ow else fill_m
    box = sil.getbbox()
    if box is None:
        return None
    fill_m, out_m = fill_m.crop(box), out_m.crop(box)
    iw, ih = fill_m.size

    # shadow silhouette placed in a canvas that holds glyph + shadow
    sh = style.get("shadow")
    ox = oy = 0
    cw, ch = iw, ih
    shadow_m = None
    if sh:
        dx, dy = float(sh.get("dx", 2)) * S, float(sh.get("dy", 2)) * S
        blur = float(sh.get("blur", 0)) * S
        steps = max(1, int(sh.get("steps", 1)))
        m = Image.fromarray(np.asarray(out_m if ow else fill_m))
        bpad = int(math.ceil(blur * 2)) + 1
        offs = [(dx * k / steps, dy * k / steps) for k in range(1, steps + 1)]
        minx = min(0, min(o[0] for o in offs)) - bpad
        miny = min(0, min(o[1] for o in offs)) - bpad
        maxx = max(0, max(o[0] for o in offs)) + bpad
        maxy = max(0, max(o[1] for o in offs)) + bpad
        ox, oy = int(math.ceil(-minx)), int(math.ceil(-miny))
        cw = int(math.ceil(iw + maxx)) + ox
        ch = int(math.ceil(ih + maxy)) + oy
        shadow_m = Image.new("L", (cw, ch), 0)
        for (ddx, ddy) in offs:
            tmp = Image.new("L", (cw, ch), 0)
            tmp.paste(m, (int(round(ox + ddx)), int(round(oy + ddy))))
            shadow_m = Image.fromarray(np.maximum(np.asarray(shadow_m), np.asarray(tmp)))
        if blur > 0:
            shadow_m = shadow_m.filter(ImageFilter.GaussianBlur(blur))
    fill_c = Image.new("L", (cw, ch), 0)
    fill_c.paste(fill_m, (ox, oy))
    out_c = Image.new("L", (cw, ch), 0)
    out_c.paste(out_m, (ox, oy))
    return {"fill": fill_c, "outline": out_c if ow else None, "shadow": shadow_m, "ink": (ox, oy, iw, ih),
            "size": (cw, ch), "font": font_name, "lines": lines}


def _gradient_rgba(size, ink, style):
    cw, ch = size
    ox, oy, iw, ih = ink
    stops = style.get("gradient")
    if not stops:
        c = parse_color(style.get("fill"), (255, 255, 255, 255))
        img = Image.new("RGBA", size, c)
        return img
    ts = np.array([s[0] for s in stops], dtype=np.float64)
    cs = np.array([parse_color(s[1]) for s in stops], dtype=np.float64)
    y = (np.arange(ch) - oy + 0.5) / max(ih, 1)
    col = np.stack([np.interp(y, ts, cs[:, k]) for k in range(4)], axis=1)
    arr = np.repeat(col[:, None, :], cw, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def compose_block(blk, style):
    """Return an RGBA image (S scale) of shadow + outline + fill [+ highlight]."""
    size = blk["size"]
    op = float(style.get("opacity", 1.0))
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    sh = style.get("shadow")
    if sh and blk["shadow"] is not None:
        c = parse_color(sh.get("color", "#000000"))
        a = float(sh.get("alpha", 1.0)) * (c[3] / 255.0)
        layer = Image.new("RGBA", size, c[:3] + (255,))
        layer.putalpha(blk["shadow"].point(lambda v: int(v * a)))
        canvas = Image.alpha_composite(canvas, layer)
    if blk["outline"] is not None:
        c = parse_color((style.get("outline") or {}).get("color", "#000000"))
        layer = Image.new("RGBA", size, c)
        layer.putalpha(blk["outline"].point(lambda v: int(v * c[3] / 255.0)))
        canvas = Image.alpha_composite(canvas, layer)
    layer = _gradient_rgba(size, blk["ink"], style)
    a = np.asarray(blk["fill"]).astype(np.float64) / 255.0 * (np.asarray(layer)[..., 3] / 255.0)
    layer.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    canvas = Image.alpha_composite(canvas, layer)
    hl = style.get("highlight")
    if hl:
        c = parse_color(hl.get("color", "#ffffff"))
        ox, oy, iw, ih = blk["ink"]
        h = float(hl.get("height", 0.45))
        ya = (np.arange(size[1]) - oy) / max(ih, 1)
        band = ((ya >= 0) & (ya < h)).astype(np.float64)[:, None]
        a = np.asarray(blk["fill"]).astype(np.float64) / 255.0 * band * float(hl.get("alpha", 0.35))
        hlayer = Image.new("RGBA", size, c[:3] + (255,))
        hlayer.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
        canvas = Image.alpha_composite(canvas, hlayer)
    if op < 1.0:
        al = canvas.getchannel("A").point(lambda v: int(v * op))
        canvas.putalpha(al)
    return canvas


def _paste_clip(dst, src, x, y):
    x, y = int(round(x)), int(round(y))
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(src.width, dst.width - x), min(src.height, dst.height - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    piece = src.crop((sx0, sy0, sx1, sy1))
    region = dst.crop((x + sx0, y + sy0, x + sx1, y + sy1))
    dst.paste(Image.alpha_composite(region, piece), (x + sx0, y + sy0))


def render_text(region, style, S, warnings, report):
    w, h = int(region["w"]), int(region["h"])
    text = region["text"]
    pad = float(region.get("pad", 1))
    align = region.get("align", "center")
    valign = region.get("valign", "middle")
    wrap = bool(region.get("wrap", False))
    lsp = float(region.get("line_spacing", 1.0))
    availw, availh = w - 2 * pad, h - 2 * pad
    size = region.get("size", "auto")
    min_sx = float(region.get("min_sx", 0.8))
    blk = None
    sx = 1.0
    chosen = None
    if size == "auto":
        smax = float(region.get("max_size", h))
        smin = float(region.get("min_size", 6))
        s = smax
        while s >= smin - 1e-9:
            b = build_block(text, style, s, 1.0, S, availw, wrap, lsp, align, warnings)
            if b is not None:
                bw, bh = b["size"][0] / S, b["size"][1] / S
                if bh <= availh + 1e-6:
                    if bw <= availw + 1e-6:
                        blk, chosen, sx = b, s, 1.0
                        break
                    need = availw / bw
                    if need >= min_sx:
                        b2 = build_block(text, style, s, need, S, availw, wrap, lsp, align, warnings)
                        if b2 is not None and b2["size"][0] / S <= availw + 0.6:
                            blk, chosen, sx = b2, s, need
                            break
            s -= 0.5
        if blk is None:
            chosen, sx = smin, 1.0
            blk = build_block(text, style, smin, 1.0, S, availw, wrap, lsp, align, warnings)
            if blk is not None:
                bw = blk["size"][0] / S
                if bw > availw:
                    sx = max(availw / bw, 0.4)
                    blk = build_block(text, style, smin, sx, S, availw, wrap, lsp, align, warnings)
            warnings.append("%s: text does not fit at min_size %.1f (squash %.2f); enlarge the region or shorten the text"
                            % (region.get("id", "?"), smin, sx))
    else:
        chosen = float(size)
        blk = build_block(text, style, chosen, 1.0, S, availw, wrap, lsp, align, warnings)
        if blk is not None:
            bw = blk["size"][0] / S
            if bw > availw + 0.5 and region.get("squash", True):
                sx = max(availw / bw, min_sx)
                blk = build_block(text, style, chosen, sx, S, availw, wrap, lsp, align, warnings)
    if blk is None:
        warnings.append("%s: empty text" % region.get("id", "?"))
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))

    img = compose_block(blk, style)
    cw, ch = img.size
    cwx, chx = cw / S, ch / S
    if cwx > w + 0.5 or chx > h + 0.5:
        warnings.append("%s: rendered %.1fx%.1f overflows region %dx%d (clipped)" % (region.get("id", "?"), cwx, chx, w, h))
    fx = {"left": 0.0, "center": 0.5, "right": 1.0}[align]
    fy = {"top": 0.0, "middle": 0.5, "bottom": 1.0}[valign]
    x = (pad + (availw - cwx) * fx + float(region.get("dx", 0))) * S
    y = (pad + (availh - chx) * fy + float(region.get("dy", 0))) * S
    canvas = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    _paste_clip(canvas, img, x, y)
    small = canvas.convert("RGBa").resize((w, h), Image.BOX).convert("RGBA")
    if style.get("aa", True) is False:
        a = np.asarray(small).copy()
        a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
        small = Image.fromarray(a, "RGBA")
    report.update({"font": blk["font"], "size": chosen, "squash": round(sx, 3),
                   "block": [round(cwx, 1), round(chx, 1)], "lines": blk["lines"]})
    return small


# --------------------------------------------------------------------------- erase

def _clip_rect(r, W, H):
    x, y, w, h = [int(v) for v in r]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    return x0, y0, max(0, x1 - x0), max(0, y1 - y0)


def _ring(arr, rect, depth=2):
    H, W = arr.shape[:2]
    x, y, w, h = rect
    parts = []
    if y - depth >= 0:
        parts.append(arr[y - depth:y, max(0, x - depth):min(W, x + w + depth)].reshape(-1, arr.shape[2]))
    if y + h + depth <= H:
        parts.append(arr[y + h:y + h + depth, max(0, x - depth):min(W, x + w + depth)].reshape(-1, arr.shape[2]))
    if x - depth >= 0:
        parts.append(arr[y:y + h, x - depth:x].reshape(-1, arr.shape[2]))
    if x + w + depth <= W:
        parts.append(arr[y:y + h, x + w:x + w + depth].reshape(-1, arr.shape[2]))
    if not parts:
        return np.zeros((1, arr.shape[2]))
    return np.concatenate(parts, axis=0)


def _edge(arr, rect, side, d=1):
    """mean colour line just outside one side; shape (n, C)."""
    H, W = arr.shape[:2]
    x, y, w, h = rect
    if side == "l":
        xs = slice(max(0, x - d), x) if x > 0 else slice(x + w, min(W, x + w + d))
        return arr[y:y + h, xs].mean(axis=1)
    if side == "r":
        xs = slice(x + w, min(W, x + w + d)) if x + w < W else slice(max(0, x - d), x)
        return arr[y:y + h, xs].mean(axis=1)
    if side == "t":
        ys = slice(max(0, y - d), y) if y > 0 else slice(y + h, min(H, y + h + d))
        return arr[ys, x:x + w].mean(axis=0)
    ys = slice(y + h, min(H, y + h + d)) if y + h < H else slice(max(0, y - d), y)
    return arr[ys, x:x + w].mean(axis=0)


def _hgrad(arr, rect, d=1):
    x, y, w, h = rect
    L, R = _edge(arr, rect, "l", d), _edge(arr, rect, "r", d)
    t = ((np.arange(w) + 0.5) / w)[None, :, None]
    return L[:, None, :] * (1 - t) + R[:, None, :] * t


def _vgrad(arr, rect, d=1):
    x, y, w, h = rect
    T, B = _edge(arr, rect, "t", d), _edge(arr, rect, "b", d)
    t = ((np.arange(h) + 0.5) / h)[:, None, None]
    return T[None, :, :] * (1 - t) + B[None, :, :] * t


def _coons(arr, rect, d=1):
    x, y, w, h = rect
    L, R = _edge(arr, rect, "l", d), _edge(arr, rect, "r", d)
    T, B = _edge(arr, rect, "t", d), _edge(arr, rect, "b", d)
    u = ((np.arange(w) + 0.5) / w)[None, :, None]
    v = ((np.arange(h) + 0.5) / h)[:, None, None]
    lin = (1 - u) * L[:, None, :] + u * R[:, None, :] + (1 - v) * T[None, :, :] + v * B[None, :, :]
    c00, c10, c01, c11 = L[0], R[0], L[-1], R[-1]
    bil = ((1 - u) * (1 - v) * c00 + u * (1 - v) * c10 + (1 - u) * v * c01 + u * v * c11)
    return lin - bil


def _run_fill(arr, mask, axis):
    """Linear interpolation across masked runs along an axis (0 = vertical, 1 = horizontal).
    Pixels in runs that touch no known pixel on either side stay unchanged (return filled mask)."""
    out = arr.copy()
    done = ~mask
    a = out if axis == 1 else out.transpose(1, 0, 2)
    m = mask if axis == 1 else mask.T
    dn = done if axis == 1 else done.T
    n = a.shape[1]
    for r in range(a.shape[0]):
        row = m[r]
        if not row.any():
            continue
        i = 0
        while i < n:
            if not row[i]:
                i += 1
                continue
            j = i
            while j < n and row[j]:
                j += 1
            left = a[r, i - 1] if i > 0 else None
            right = a[r, j] if j < n else None
            if left is None and right is None:
                i = j
                continue
            if left is None:
                a[r, i:j] = right
            elif right is None:
                a[r, i:j] = left
            else:
                t = ((np.arange(j - i) + 1.0) / (j - i + 1))[:, None]
                a[r, i:j] = left * (1 - t) + right * t
            dn[r, i:j] = True
            i = j
    return out, done


def _diffuse(arr, mask, relax=80):
    """Harmonic inpainting: onion-peel initialisation + Jacobi relaxation on the masked pixels."""
    out = arr.copy()
    known = ~mask
    if not known.any():
        return out
    H, W = mask.shape
    k = known.copy()
    guard = 0
    while not k.all() and guard < H + W:
        guard += 1
        wgt = k.astype(np.float64)
        num = np.zeros_like(out)
        cnt = np.zeros((H, W))
        vp = np.pad(out * wgt[..., None], ((1, 1), (1, 1), (0, 0)))
        wp = np.pad(wgt, 1)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                num += vp[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
                cnt += wp[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
        new = (~k) & (cnt > 0)
        if not new.any():
            break
        out[new] = num[new] / cnt[new][:, None]
        k |= new
    for _ in range(relax):
        p = np.pad(out, ((1, 1), (1, 1), (0, 0)), mode="edge")
        avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4.0
        out[mask] = avg[mask]
    return out


def _dilate(mask, n, shape="square"):
    for i in range(int(n)):
        p = np.pad(mask, 1)
        m = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        if shape == "square" or (shape == "octagon" and i % 2 == 0):
            m = m | p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:]
        mask = m
    return mask


def _cond_mask(cond, arr, rect, base_dir, W, H):
    """arr: full image float; returns bool mask for the rect."""
    x, y, w, h = rect
    sub = arr[y:y + h, x:x + w]
    rgb, a = sub[..., :3], sub[..., 3]
    m = np.ones((h, w), bool)
    luma = rgb @ np.array([0.299, 0.587, 0.114])
    if "luma_gt" in cond:
        m &= luma > cond["luma_gt"]
    if "luma_lt" in cond:
        m &= luma < cond["luma_lt"]
    if "alpha_gt" in cond:
        m &= a > cond["alpha_gt"]
    if "alpha_lt" in cond:
        m &= a < cond["alpha_lt"]
    if "sat_gt" in cond or "sat_lt" in cond:
        mx, mn = rgb.max(axis=2), rgb.min(axis=2)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
        if "sat_gt" in cond:
            m &= sat > cond["sat_gt"]
        if "sat_lt" in cond:
            m &= sat < cond["sat_lt"]
    if "color" in cond:
        c = np.array(cond["color"][:3], dtype=np.float64)
        m &= np.sqrt(((rgb - c) ** 2).sum(axis=2)) <= float(cond.get("tol", 40))
    if "bg_dist_gt" in cond:
        bg = cond.get("bg")
        bgc = np.array(bg[:3], dtype=np.float64) if bg else np.median(_ring(arr, rect, 2)[:, :3], axis=0)
        m &= np.sqrt(((rgb - bgc) ** 2).sum(axis=2)) > float(cond["bg_dist_gt"])
    if "rects" in cond:
        rm = np.zeros((h, w), bool)
        for rx, ry, rw, rh in cond["rects"]:
            x0, y0 = max(rx, x), max(ry, y)
            x1, y1 = min(rx + rw, x + w), min(ry + rh, y + h)
            if x1 > x0 and y1 > y0:
                rm[y0 - y:y1 - y, x0 - x:x1 - x] = True
        m &= rm
    if "mask_png" in cond:
        mi = Image.open(os.path.join(base_dir, cond["mask_png"])).convert("L")
        ma = np.asarray(mi) > 127
        if ma.shape == (H, W):
            ma = ma[y:y + h, x:x + w]
        elif ma.shape != (h, w):
            raise ValueError("mask_png %s is %s, expected texture or rect size" % (cond["mask_png"], ma.shape[::-1]))
        m &= ma
    return m


def erase_region(arr, rect, ops, base_dir, ctx, label):
    H, W = arr.shape[:2]
    rect = _clip_rect(rect, W, H)
    x, y, w, h = rect
    if w == 0 or h == 0:
        return
    if ops is None:
        return
    if isinstance(ops, (str, dict)):
        ops = [ops]
    for op in ops:
        if isinstance(op, str):
            op = {"mode": op}
        mode = op.get("mode", "auto")
        d = int(op.get("depth", 1))
        if mode == "flat":
            c = op.get("color")
            col = np.array(parse_color(c), float) if c is not None else np.median(_ring(arr, rect, 2), axis=0)
            arr[y:y + h, x:x + w] = col
        elif mode == "hgrad":
            arr[y:y + h, x:x + w] = _hgrad(arr, rect, d)
        elif mode == "vgrad":
            arr[y:y + h, x:x + w] = _vgrad(arr, rect, d)
        elif mode in ("coons", "grad"):
            arr[y:y + h, x:x + w] = _coons(arr, rect, d)
        elif mode == "clear":
            arr[y:y + h, x:x + w] = 0
        elif mode == "copy":
            sx, sy = op["src"]
            if sx < 0 or sy < 0 or sx + w > W or sy + h > H:
                raise ValueError("%s: copy source outside the texture" % label)
            arr[y:y + h, x:x + w] = arr[sy:sy + h, sx:sx + w].copy()
        elif mode == "plate":
            pim = Image.open(os.path.join(base_dir, op["path"])).convert("RGBA")
            pa = np.asarray(pim).astype(np.float64)
            ph, pw = min(h, pa.shape[0]), min(w, pa.shape[1])
            if op.get("replace"):
                arr[y:y + ph, x:x + pw] = pa[:ph, :pw]
            else:
                al = pa[:ph, :pw, 3:4] / 255.0
                arr[y:y + ph, x:x + pw, :3] = pa[:ph, :pw, :3] * al + arr[y:y + ph, x:x + pw, :3] * (1 - al)
                arr[y:y + ph, x:x + pw, 3] = np.maximum(arr[y:y + ph, x:x + pw, 3], pa[:ph, :pw, 3])
        elif mode in ("mask", "auto"):
            if mode == "auto":
                ink = [{"bg_dist_gt": float(op.get("tol", 40)), "bg": op.get("bg")}]
                dil = int(op.get("dilate", 2))
            else:
                ink = op.get("ink") or [{"luma_gt": 200}]
                dil = int(op.get("dilate", 0))
            if isinstance(ink, dict):
                ink = [ink]
            m = np.zeros((h, w), bool)
            for cond in ink:
                m |= _cond_mask(cond, arr, rect, base_dir, W, H)
            if dil:
                m = _dilate(m, dil, op.get("dilate_shape", "square"))
            for rx, ry, rw, rh in op.get("exclude", []):
                x0, y0 = max(rx, x), max(ry, y)
                x1, y1 = min(rx + rw, x + w), min(ry + rh, y + h)
                if x1 > x0 and y1 > y0:
                    m[y0 - y:y1 - y, x0 - x:x1 - x] = False
            ctx.setdefault("masks", {})[label] = (rect, m.copy())
            ctx["notes"].append("%s: erase mask covers %d of %d px" % (label, int(m.sum()), w * h))
            if not m.any():
                ctx["warnings"].append("%s: erase mask is empty (adjust ink conditions)" % label)
                continue
            fill = op.get("fill", "diffuse")
            mg = 4
            cx0, cy0 = max(0, x - mg), max(0, y - mg)
            cx1, cy1 = min(W, x + w + mg), min(H, y + h + mg)
            crop = arr[cy0:cy1, cx0:cx1].copy()
            cm = np.zeros(crop.shape[:2], bool)
            cm[y - cy0:y - cy0 + h, x - cx0:x - cx0 + w] = m
            if fill == "diffuse":
                res = _diffuse(crop, cm, int(op.get("relax", 80)))
            elif fill in ("hfill", "vfill", "hvfill"):
                res = crop
                if fill in ("hfill", "hvfill"):
                    rh_, dh = _run_fill(crop, cm, 1)
                if fill in ("vfill", "hvfill"):
                    rv_, dv = _run_fill(crop, cm, 0)
                if fill == "hfill":
                    res = rh_
                elif fill == "vfill":
                    res = rv_
                else:
                    res = (rh_ + rv_) / 2.0
                left = cm & ~(dh if fill != "vfill" else dv)
                if left.any():
                    res = _diffuse(res, left, 40)
            elif fill == "flat":
                col = np.median(_ring(arr, rect, 2), axis=0)
                res = crop.copy()
                res[cm] = col
            elif fill in ("coons", "grad"):
                res = crop.copy()
                patch = _coons(arr, rect, d)
                sub = res[y - cy0:y - cy0 + h, x - cx0:x - cx0 + w]
                sub[m] = patch[m]
            else:
                raise ValueError("%s: unknown fill %r" % (label, fill))
            arr[cy0:cy1, cx0:cx1][cm] = res[cm]
        else:
            raise ValueError("%s: unknown erase mode %r" % (label, mode))
    np.clip(arr[y:y + h, x:x + w], 0, 255, out=arr[y:y + h, x:x + w])


# --------------------------------------------------------------------------- quantize

def quantize(arr, fmt, rect):
    x, y, w, h = rect
    sub = np.clip(np.rint(arr[y:y + h, x:x + w]), 0, 255).astype(np.int32)

    def snap(v, bits):
        q = v >> (8 - bits)
        # bit replication like the DC hardware expansion
        out = (q << (8 - bits)) | (q >> (2 * bits - 8))
        return out

    r, g, b, a = (sub[..., i] for i in range(4))
    if fmt == "argb4444":
        res = [snap(r, 4), snap(g, 4), snap(b, 4), snap(a, 4)]
    elif fmt == "rgb565":
        res = [snap(r, 5), snap(g, 6), snap(b, 5), np.full_like(a, 255)]
    elif fmt == "argb1555":
        res = [snap(r, 5), snap(g, 5), snap(b, 5), np.where(a >= 128, 255, 0)]
    else:
        raise ValueError("unknown quantize format %r" % fmt)
    arr[y:y + h, x:x + w] = np.stack(res, axis=-1)


# --------------------------------------------------------------------------- glossary

def load_glossary(path):
    g = {}
    if not path or not os.path.isfile(path):
        return g
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0 or not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 2:
                continue
            ja_parts = [p.strip() for p in cols[0].split(" / ")]
            en_parts = [p.strip() for p in cols[1].split(" / ")]
            short = cols[2].strip() if len(cols) > 2 else ""
            for k, jp in enumerate(ja_parts):
                en = en_parts[k] if len(en_parts) == len(ja_parts) else cols[1].strip()
                g[jp] = (en, short, cols[1].strip())
    return g


def glossary_check(region, glossary, notes, warnings):
    ja = region.get("ja")
    if not ja or not glossary or region.get("text") is None:
        return
    ent = glossary.get(ja)
    if ent is None:
        notes.append("%s: %r not in glossary (add it to translation/glossary.tsv)" % (region.get("id", "?"), ja))
        return
    en, short, full = ent
    ok = {en.lower(), short.lower(), full.lower()} - {""}
    if region["text"].replace("\n", " ").strip().lower() not in ok:
        warnings.append("%s: art text %r differs from glossary %r%s" %
                        (region.get("id", "?"), region["text"], en, " (short %r)" % short if short else ""))


# --------------------------------------------------------------------------- driver

def render_spec(spec, img, base_dir=".", glossary=None, debug_dir=None):
    """spec: dict, img: PIL RGBA.  Returns (new_img, report dict)."""
    img = img.convert("RGBA")
    W, H = img.size
    warnings, notes = [], []
    if spec.get("size") and tuple(spec["size"]) != (W, H):
        raise ValueError("spec size %s does not match input image %dx%d" % (spec["size"], W, H))
    S = int(spec.get("supersample", 4))
    if not 1 <= S <= 8:
        raise ValueError("supersample must be 1..8")
    arr = np.asarray(img).astype(np.float64).copy()
    qfmt = spec.get("quantize")
    ctx = {"warnings": warnings, "notes": notes}
    regions_report = []
    defaults = spec.get("defaults") or {}
    for i, raw in enumerate(spec.get("regions", [])):
        region = _merge(defaults, raw)
        # style keys of defaults/region must not be merged twice; resolve separately below
        rid = region.get("id") or "r%d" % i
        region["id"] = rid
        rect = _clip_rect((region["x"], region["y"], region["w"], region["h"]), W, H)
        if rect[2] != int(region["w"]) or rect[3] != int(region["h"]):
            warnings.append("%s: region clipped to the texture (%d,%d %dx%d)" % (rid, *rect))
        region["x"], region["y"], region["w"], region["h"] = rect
        glossary_check(region, glossary, notes, warnings)
        rep = {"id": rid, "rect": list(rect), "text": region.get("text")}
        erase = region.get("erase", "auto")
        er = region.get("erase_rect")
        if not er:
            g = region.get("erase_grow", 0)
            gl, gt, gr, gb = ([g] * 4) if isinstance(g, (int, float)) else g
            er = [rect[0] - gl, rect[1] - gt, rect[2] + gl + gr, rect[3] + gt + gb]
        erase_region(arr, er, erase, base_dir, ctx, rid)
        if region.get("text"):
            style = resolve_style(raw, spec)
            tile = render_text(region, style, S, warnings, rep)
            x, y, w, h = rect
            base = Image.fromarray(np.clip(np.rint(arr[y:y + h, x:x + w]), 0, 255).astype(np.uint8), "RGBA")
            out = Image.alpha_composite(base, tile)
            arr[y:y + h, x:x + w] = np.asarray(out).astype(np.float64)
        if qfmt:
            quantize(arr, qfmt, rect)
            if er is not None and list(_clip_rect(er, W, H)) != list(rect):
                quantize(arr, qfmt, _clip_rect(er, W, H))
        regions_report.append(rep)
    result = Image.fromarray(np.clip(np.rint(arr), 0, 255).astype(np.uint8), "RGBA")
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        for rid, (rect, m) in (ctx.get("masks") or {}).items():
            Image.fromarray((m * 255).astype(np.uint8), "L").save(os.path.join(debug_dir, "mask_%s.png" % rid))
    return result, {"regions": regions_report, "warnings": warnings, "notes": notes}


def before_after(before, after, path, scale=3):
    w, h = before.size
    sheet = Image.new("RGBA", (w * scale * 2 + 12, h * scale), (40, 40, 40, 255))
    sheet.paste(before.resize((w * scale, h * scale), Image.NEAREST), (0, 0))
    sheet.paste(after.resize((w * scale, h * scale), Image.NEAREST), (w * scale + 12, 0))
    sheet.convert("RGB").save(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Repaint Japanese art text with English (see docs/art-translation.md)")
    ap.add_argument("spec", nargs="?")
    ap.add_argument("src", nargs="?")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--list-fonts", action="store_true", help="show which font aliases resolve on this machine")
    ap.add_argument("--glossary", default=None, help="glossary TSV (default: translation/glossary.tsv next to the repo)")
    ap.add_argument("--sheet", help="also write a before|after comparison PNG (3x nearest)")
    ap.add_argument("--debug-masks", help="directory for per-region erase masks")
    ap.add_argument("--strict", action="store_true", help="exit 1 when there are warnings")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    if a.list_fonts:
        list_fonts()
        return 0
    if not (a.spec and a.src and a.dst):
        ap.error("usage: arttext.py spec.json in.png out.png")
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    gpath = a.glossary
    if gpath is None:
        here = os.path.dirname(os.path.abspath(__file__))
        gpath = os.path.join(here, "..", "translation", "glossary.tsv")
    img = Image.open(a.src).convert("RGBA")
    out, rep = render_spec(spec, img, os.path.dirname(os.path.abspath(a.spec)), load_glossary(gpath), a.debug_masks)
    d = os.path.dirname(os.path.abspath(a.dst))
    os.makedirs(d, exist_ok=True)
    out.save(a.dst)
    if a.sheet:
        before_after(img, out, a.sheet)
    if not a.quiet:
        for r in rep["regions"]:
            if r.get("font"):
                print("  %-14s %-18r font=%s size=%s squash=%s block=%s" %
                      (r["id"], r["text"], r["font"], r["size"], r["squash"], r["block"]))
        for n in rep["notes"]:
            print("  note: " + n)
    for w in rep["warnings"]:
        print("  WARNING: " + w, file=sys.stderr)
    print("wrote %s (%d regions, %d warnings)" % (a.dst, len(rep["regions"]), len(rep["warnings"])))
    return 1 if (a.strict and rep["warnings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
