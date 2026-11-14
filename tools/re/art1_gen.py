"""art1_gen - write tools/re/art1_spec/*.json for the header-bar textures (parametrised).
python -I -X utf8 tools/re/art1_gen.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'art1_spec')
FONT = ["segoe-ui-bold", "arial-bold"]
NFONT = ["arial-narrow-bold", "bahnschrift", "arial-bold"]


def sty(top, bot, outline, sh):
    s = {"font": FONT, "gradient": [[0, top], [1, bot]],
         "shadow": {"color": sh, "dx": 1.5, "dy": 1.5, "steps": 2, "alpha": 1.0}}
    if outline:
        s["outline"] = {"color": outline, "width": 1}
    return s


def spec(tid, size, qf, hdr, hdr_ink, hdr_rects, extra):
    d = {"texture": tid, "size": size, "supersample": 4, "quantize": qf,
         "styles": hdr[1], "defaults": {"style": "t", "align": "left", "valign": "middle", "min_sx": 0.8,
                                        "erase": {"mode": "mask", "ink": hdr_ink, "dilate": 1, "fill": "hfill"}}}
    d["styles"] = {"t": hdr[0]}
    for k, v in hdr[1].items():
        d["styles"][k] = v
    reg = []
    for (rid, ja, txt, r, kw) in hdr_rects:
        o = {"id": rid, "ja": ja, "text": txt, "x": r[0], "y": r[1], "w": r[2], "h": r[3]}
        o.update(kw)
        reg.append(o)
    d["regions"] = reg + extra
    return d


def bar(i, tid, qf, hdr_ink, hs, man, oku, half, man_ink, ha=None, hb=None, ya=None, hg=False, cp=None):
    """hs: style for header, man/oku/half: (style, rect-kw)"""
    r = ya or {"yr": [198, 36, 38, 30], "mo": [260, 36, 34, 30], "wk": [296, 36, 40, 30]}
    hr = [("yr", "年目", "Yr", r["yr"], {"size": 18, "align": "center"}),
          ("mo", "月", "Mo", r["mo"], {"size": 17}),
          ("wk", "週", "Wk", r["wk"], {"size": 17})]
    if hg:
        er = {"yr": [196, 34, 42, 34], "mo": [260, 34, 22, 34], "wk": [296, 34, 26, 34]}
        for h in hr:
            h[4]["erase"] = {"mode": "hgrad"}
            h[4]["erase_rect"] = er[h[0]]
    if cp:
        for h in hr:
            rr = h[3]
            h[4]["hsmooth"] = 4
            h[4]["erase_rect"] = [rr[0] - 2, rr[1], rr[2] + 4, rr[3]]
    ex = []
    if man:
        ex.append(dict({"id": "man", "ja": "万円", "text": "man", "style": "man", "size": "auto", "max_size": 18,
                        "erase": {"mode": "hgrad"},
                        "erase_rect": man[2]}, **man[1]))
    if oku:
        ex.append(dict({"id": "oku", "ja": "億", "text": "oku", "style": "oku", "size": 18,
                        "min_sx": 0.4, "font": NFONT, "align": "center", "erase": {"mode": "clear"}}, **oku[1]))
    if half:
        ex.append(dict({"id": "first", "ja": "前半", "text": "1st", "style": "half", "size": 19, "align": "center",
                        "erase": {"mode": "clear"}}, **half[0]))
        ex.append(dict({"id": "second", "ja": "後半", "text": "2nd", "style": "half", "size": 19, "align": "center",
                        "erase": {"mode": "clear"}}, **half[1]))
    st = {}
    if man: st["man"] = man[0]
    if oku: st["oku"] = oku[0]
    if half: st["half"] = half[2]
    return spec(tid, [512, 512] if i not in ("10470", "10474") else [512, 256], qf, (hs, st), hdr_ink, hr, ex)


OUTPUT = {}
HALF_A = [{"x": 466, "y": 296, "w": 46, "h": 37}, {"x": 466, "y": 335, "w": 46, "h": 38}]
OKU_A = {"x": 462, "y": 266, "w": 30, "h": 32}

# 00002 : white header, mint 万円, teal 億, white 前後半
w_hdr = sty("#ffffff", "#d8f0e0", "#000000", "#000000")
OUTPUT["00002"] = bar("00002", "00002 ATFIRST/BAR.TBD #0", "argb4444",
    [{"luma_gt": 150}, {"luma_lt": 45}], w_hdr,
    (sty("#ffffff", "#d0ecd8", "#000000", "#000000"), {"x": 66, "y": 141, "w": 49, "h": 24, "align": "right"}, [70, 141, 45, 24]),
    (sty("#e8ffff", "#2fb8a8", "#000000", "#000000"), dict(OKU_A)),
    (HALF_A[0], HALF_A[1], sty("#ffffff", "#d8d8d8", "#000000", "#000000")),
    [{"luma_gt": 150}, {"luma_lt": 20}])
OUTPUT["10475"] = bar("10475", "10475 FLOW_PRG/YOUTH.ZAR youth.tbd#5", "argb4444",
    [{"luma_gt": 150}, {"luma_lt": 45}], w_hdr,
    (sty("#ffffff", "#d0ecd8", "#000000", "#000000"), {"x": 66, "y": 141, "w": 49, "h": 24, "align": "right"}, [70, 141, 45, 24]),
    (sty("#e8ffff", "#2fb8a8", "#000000", "#000000"), dict(OKU_A)),
    (HALF_A[0], HALF_A[1], sty("#ffffff", "#d8d8d8", "#000000", "#000000")),
    [{"luma_gt": 150}, {"luma_lt": 20}])
# 07332 : olive header on blue/brown, navy 万円/億
olive = sty("#adad00", "#adad00", None, "#181800")
OUTPUT["07332"] = bar("07332", "07332 FLOW_PRG/LOADBAR.BIN @1ec#0", "argb1555",
    [{"color": [173, 173, 0], "tol": 45}, {"color": [49, 49, 0], "tol": 35}], olive,
    (sty("#292194", "#292194", None, "#000000"), {"x": 62, "y": 126, "w": 52, "h": 36}, [60, 128, 54, 34]),
    (sty("#292194", "#292194", None, "#000000"), dict(OKU_A)),
    (HALF_A[0], HALF_A[1], sty("#adad00", "#adad00", None, "#181800")),
    [{"color": [41, 33, 148], "tol": 45}, {"luma_lt": 40}], hg=True)
cream = sty("#dedec6", "#dedec6", None, "#181808")
OUTPUT["10469"] = bar("10469", "10469 FLOW_PRG/YOUTH.BIN @36114#0", "argb1555",
    [{"color": [222, 222, 198], "tol": 45}, {"luma_lt": 40}], cream,
    (sty("#c6d600", "#c6d600", None, "#000000"), {"x": 62, "y": 126, "w": 52, "h": 36}, [60, 128, 54, 34]),
    (sty("#c6d600", "#c6d600", None, "#000000"), dict(OKU_A)),
    (HALF_A[0], HALF_A[1], sty("#dedec6", "#dedec6", None, "#181808")),
    [{"color": [198, 214, 0], "tol": 45}, {"luma_lt": 40}], hg=True)
# youth.tbd #0 / #4, TRAINING : ice header, green halves
ice = sty("#eeffff", "#bfe4ee", "#102020", "#000000")
ink_ice = [{"luma_gt": 175}, {"luma_lt": 70, "sat_lt": 0.45}]
Y = {"yr": [80, 54, 42, 36], "mo": [145, 54, 34, 36], "wk": [187, 54, 40, 36]}
T = {"yr": [66, 54, 42, 36], "mo": [131, 54, 34, 36], "wk": [173, 54, 40, 36]}
green = sty("#ddffdd", "#6ab86a", "#0c300c", "#000000")
OUTPUT["10470"] = bar("10470", "10470 FLOW_PRG/YOUTH.ZAR youth.tbd#0", "argb4444", ink_ice, ice, None, None,
    ({"x": 163, "y": 198, "w": 42, "h": 34}, {"x": 211, "y": 198, "w": 42, "h": 34}, green), None, ya=Y, cp=220)
OUTPUT["10474"] = bar("10474", "10474 FLOW_PRG/YOUTH.ZAR youth.tbd#4", "argb4444", ink_ice, ice, None, None,
    None, None, ya=Y, cp=220)
OUTPUT["37285"] = bar("37285", "37285 TRAINING/TRAINING.TBD #0", "argb4444", ink_ice, ice, None, None,
    ({"x": 300, "y": 119, "w": 40, "h": 36}, {"x": 348, "y": 119, "w": 44, "h": 36}, green), None, ya=T, cp=206)
for k, v in OUTPUT.items():
    json.dump(v, open(os.path.join(OUT, k + '.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(sorted(OUTPUT))
