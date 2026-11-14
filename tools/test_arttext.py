#!/usr/bin/env python
"""Self-test for tools/arttext.py:  python -I -X utf8 tools/test_arttext.py [--gallery OUT.png]

Builds synthetic textures (gradient plate with fake 'Japanese' blobs), runs every erase mode and every
preset, and checks that: the erased area matches the clean plate closely, text lands inside the region,
nothing outside the region/erase rect changes, auto-fit respects the region, and quantize is idempotent.
--gallery writes a contact sheet of the presets for eyeballing.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arttext  # noqa: E402

W, H = 160, 96


def plate():
    y, x = np.mgrid[0:H, 0:W]
    r = 40 + x * 0.3
    g = 80 + y * 0.8
    b = 200 - x * 0.2
    return Image.fromarray(np.stack([r, g, b, np.full_like(r, 255)], -1).clip(0, 255).astype(np.uint8), "RGBA")


def with_ink(base, rect):
    im = base.copy()
    d = ImageDraw.Draw(im)
    x, y, w, h = rect
    for i in range(5):
        d.rectangle([x + 4 + i * 12, y + 4, x + 10 + i * 12, y + h - 4], fill=(240, 250, 250, 255), outline=(0, 0, 0, 255))
    return im


fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print("FAIL:", msg)
    else:
        print("ok  :", msg)


def main():
    clean = plate()
    rect = (20, 20, 80, 40)
    dirty = with_ink(clean, rect)
    ca = np.asarray(clean).astype(int)
    for mode, extra in [("mask-diffuse", {"mode": "mask", "ink": [{"luma_gt": 200}, {"luma_lt": 20}], "dilate": 1}),
                        ("mask-hfill", {"mode": "mask", "ink": [{"luma_gt": 200}, {"luma_lt": 20}], "dilate": 1, "fill": "hfill"}),
                        ("mask-vfill", {"mode": "mask", "ink": [{"luma_gt": 200}, {"luma_lt": 20}], "dilate": 1, "fill": "vfill"}),
                        ("mask-coons", {"mode": "mask", "ink": [{"luma_gt": 200}, {"luma_lt": 20}], "dilate": 1, "fill": "coons"}),
                        ("auto", {"mode": "auto", "tol": 40}),
                        ("hgrad", {"mode": "hgrad"}), ("vgrad", {"mode": "vgrad"}), ("coons", {"mode": "coons"})]:
        spec = {"regions": [{"id": "t", "x": rect[0], "y": rect[1], "w": rect[2], "h": rect[3], "erase": extra}]}
        out, rep = arttext.render_spec(spec, dirty)
        oa = np.asarray(out).astype(int)
        err = np.abs(oa[20:60, 20:100, :3] - ca[20:60, 20:100, :3]).mean()
        outside = np.abs(oa - np.asarray(dirty).astype(int)).copy()
        outside[20:60, 20:100] = 0
        check(err < 12, "%s residual %.1f < 12" % (mode, err))
        check(outside.sum() == 0, "%s leaves outside pixels untouched" % mode)

    out, _ = arttext.render_spec({"regions": [{"x": 4, "y": 4, "w": 20, "h": 10, "erase": {"mode": "flat", "color": [1, 2, 3]}}]}, dirty)
    check(tuple(np.asarray(out)[5, 5]) == (1, 2, 3, 255), "flat colour")
    out, _ = arttext.render_spec({"regions": [{"x": 4, "y": 4, "w": 20, "h": 10, "erase": {"mode": "clear"}}]}, dirty)
    check(np.asarray(out)[5, 5, 3] == 0, "clear -> transparent")
    out, _ = arttext.render_spec({"regions": [{"x": 0, "y": 0, "w": 20, "h": 10, "erase": {"mode": "copy", "src": [100, 50]}}]}, dirty)
    check((np.asarray(out)[0:10, 0:20] == np.asarray(dirty)[50:60, 100:120]).all(), "copy patch")

    # text: auto-fit inside the region, nothing painted outside it
    for preset in sorted(arttext.PRESETS):
        spec = {"regions": [{"id": "p", "x": 30, "y": 30, "w": 100, "h": 30, "text": "Secretary Select", "style": preset, "erase": None}]}
        out, rep = arttext.render_spec(spec, clean)
        diff = np.abs(np.asarray(out).astype(int) - ca).sum(axis=2)
        ys, xs = np.nonzero(diff)
        inside = len(ys) > 0 and xs.min() >= 30 and xs.max() < 130 and ys.min() >= 30 and ys.max() < 60
        check(inside, "preset %s paints only inside its region" % preset)
        check(not rep["warnings"], "preset %s fits 'Secretary Select' in 100x30 (%s)" % (preset, rep["regions"][0].get("size")))

    # too long -> warning, no crash
    spec = {"regions": [{"id": "long", "x": 10, "y": 10, "w": 30, "h": 12, "text": "Extraordinarily Long Heading", "style": "menu_label", "erase": None}]}
    out, rep = arttext.render_spec(spec, clean)
    check(len(rep["warnings"]) > 0, "overflow reported as warning")

    # hard alpha + quantize idempotence
    spec = {"quantize": "argb4444", "regions": [{"x": 10, "y": 10, "w": 60, "h": 20, "text": "Step Up", "style": "plain_white", "aa": False, "erase": None}]}
    out, _ = arttext.render_spec(spec, clean)
    a1 = np.asarray(out)
    out2, _ = arttext.render_spec({"quantize": "argb4444", "regions": [{"x": 10, "y": 10, "w": 60, "h": 20, "erase": None}]}, out)
    check((a1 == np.asarray(out2)).all(), "quantize argb4444 idempotent")
    for fmt in ("rgb565", "argb1555"):
        o, _ = arttext.render_spec({"quantize": fmt, "regions": [{"x": 0, "y": 0, "w": 40, "h": 40, "erase": None}]}, clean)
        o2, _ = arttext.render_spec({"quantize": fmt, "regions": [{"x": 0, "y": 0, "w": 40, "h": 40, "erase": None}]}, o)
        check((np.asarray(o) == np.asarray(o2)).all(), "quantize %s idempotent" % fmt)

    # glossary
    g = arttext.load_glossary(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "translation", "glossary.tsv"))
    _, rep = arttext.render_spec({"regions": [{"id": "g", "ja": "決定", "text": "Wrong", "x": 0, "y": 0, "w": 60, "h": 20, "erase": None}]}, clean, glossary=g)
    check(any("glossary" in w for w in rep["warnings"]), "glossary mismatch warns")

    if "--gallery" in sys.argv:
        path = sys.argv[sys.argv.index("--gallery") + 1]
        names = sorted(arttext.PRESETS)
        sheet = Image.new("RGBA", (260, 40 * len(names) + 4), (70, 100, 70, 255))
        for i, n in enumerate(names):
            spec = {"regions": [{"x": 4, "y": 4 + 40 * i, "w": 252, "h": 36, "text": "Secretary Select", "style": n, "erase": None, "align": "left"}]}
            sheet, _ = arttext.render_spec(spec, sheet)
        sheet = sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST)
        sheet.convert("RGB").save(path)
        print("gallery ->", path)
    print("FAILED %d" % len(fails) if fails else "ALL OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
