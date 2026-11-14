"""art1_gen2 - specs for YEAR_PT, ESTABLIS strip, Yes/No and mon.tbd.  python -I -X utf8 tools/re/art1_gen2.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'art1_spec')
NF = ["arial-narrow-bold", "bahnschrift", "arial-bold"]
BF = ["segoe-ui-bold", "arial-bold"]


def w(name, d):
    json.dump(d, open(os.path.join(OUT, name + '.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)


YEL = {"font": NF, "fill": "#efff42", "shadow": {"color": "#000000", "dx": 1.5, "dy": 1.5, "steps": 2, "alpha": 1.0}}
YELB = dict(YEL, font=BF)
CHROME = {"font": BF, "gradient": [[0, "#f7f7f7"], [0.5, "#cfcfcf"], [0.52, "#9c9c9c"], [1, "#bdbdbd"]],
          "outline": {"color": "#101042", "width": 1}, "shadow": {"color": "#101042", "dx": 1.5, "dy": 1.5, "steps": 2, "alpha": 1.0}}
CLEAR = {"mode": "clear"}
YINK = [{"color": [239, 255, 66], "tol": 70}, {"luma_lt": 30}]

# 04112 YEAR_PT : chrome Yr on the purple marble plate
w("04112", {"texture": "04112 ETC_DATA/YEAR_PT.TBD #0", "size": [256, 256], "supersample": 4, "quantize": "argb4444",
  "styles": {"chrome": {"font": ["arial-black", "impact"], "gradient": [[0, "#ffffff"], [0.46, "#e6e6e6"], [0.5, "#8e8e8e"], [1, "#d4d4d4"]],
             "outline": {"color": "#2a2a2a", "width": 1.2}, "shadow": {"color": "#1c1c1c", "dx": 2, "dy": 2, "steps": 2, "alpha": 1.0}}},
  "regions": [{"id": "yr", "ja": "年目", "text": "Yr", "style": "chrome", "x": 143, "y": 207, "w": 88, "h": 40, "size": "auto", "max_size": 42,
     "align": "center", "erase": {"mode": "mask", "ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "diffuse"}},
   {"id": "tick", "ja": "年", "x": 143, "y": 203, "w": 88, "h": 4, "erase": {"mode": "mask", "ink": [{"sat_lt": 0.2, "luma_gt": 40}], "dilate": 1, "fill": "hfill"}}]})

# 07308 ESTABLIS strip
w("07308", {"texture": "07308 FLOW_PRG/ESTABLIS.BIN @1ee08#0", "size": [256, 64], "supersample": 4, "quantize": "argb4444",
  "styles": {"y": YEL},
  "regions": [
   {"id": "oku", "ja": "億", "text": "oku", "style": "y", "x": 0, "y": 0, "w": 32, "h": 30, "size": 18, "min_sx": 0.4, "align": "center", "erase": CLEAR},
   {"id": "man", "ja": "万円", "text": "man", "style": "y", "font": BF, "x": 168, "y": 0, "w": 70, "h": 29, "size": "auto", "max_size": 20, "align": "right",
    "erase": {"mode": "mask", "ink": [{"color": [238, 255, 68], "tol": 70}, {"luma_lt": 105, "sat_gt": 0.3}], "dilate": 1, "fill": "hfill"}}]})

# Yes / No
VIO = {"font": ["segoe-ui-bold", "arial-bold"], "gradient": [[0, "#ffffff"], [1, "#d6d6ee"]],
       "outline": {"color": "#8a5ae0", "width": 1.6}, "shadow": {"color": "#2a0a5a", "dx": 1.5, "dy": 1.5, "blur": 1, "alpha": 0.7}}
w("00091", {"texture": "00091 yesno.tbd#1", "size": [128, 128], "supersample": 4, "quantize": "argb4444", "styles": {"v": VIO},
  "regions": [
   {"id": "yes", "ja": "はい", "text": "Yes", "style": "v", "x": 0, "y": 16, "w": 128, "h": 44, "size": 36, "align": "center", "erase": CLEAR},
   {"id": "no", "ja": "いいえ", "text": "No", "style": "v", "x": 0, "y": 62, "w": 128, "h": 52, "size": 36, "align": "center", "erase": CLEAR}]})
GREY = {"font": ["segoe-ui-bold", "arial-bold"], "fill": "#c4c4cc"}
w("03634", {"texture": "03634 ETC_DATA/SHTEX.ZAR frame.tbd#3", "size": [64, 64], "supersample": 4, "quantize": "argb4444", "styles": {"g": GREY},
  "regions": [
   {"id": "yes", "ja": "はい", "text": "Yes", "style": "g", "x": 0, "y": 0, "w": 64, "h": 26, "size": 22, "align": "center", "erase": CLEAR},
   {"id": "no", "ja": "いいえ", "text": "No", "style": "g", "x": 0, "y": 38, "w": 64, "h": 26, "size": 22, "align": "center", "erase": CLEAR}]})


# mon.tbd (ARGB1555)
def mon(tid, third):
    dk = {"luma_lt": 30}
    regs = [
     {"id": "contract", "ja": "契約年数", "text": "Contract Yrs", "style": "silveri", "x": 4, "y": 8, "w": 63, "h": 19, "size": "auto", "max_size": 13, "min_sx": 0.7, "align": "left", "erase_rect": [3, 6, 64, 24],
      "erase": {"mode": "mask", "ink": [{"sat_lt": 0.18, "luma_gt": 90}, {"luma_lt": 50}], "dilate": 1, "fill": "hfill"}},
     {"id": "yr", "ja": "年", "text": "Yr", "style": "y", "font": BF, "x": 40, "y": 38, "w": 38, "h": 28, "size": "auto", "max_size": 22, "align": "right", "erase_rect": [40, 38, 38, 32],
      "erase": {"mode": "mask", "ink": [{"color": [239, 255, 66], "tol": 80}, {"luma_lt": 14}], "dilate": 2, "fill": "hfill"}},
     {"id": "salary", "ja": "年俸", "text": "Salary", "style": "silver", "x": 88, "y": 3, "w": 64, "h": 30, "size": "auto", "max_size": 24, "align": "left", "erase": CLEAR},
     {"id": "funds", "ja": "現在の所持金", "text": "Funds", "style": "silveri", "x": 155, "y": 5, "w": 98, "h": 28, "size": "auto", "max_size": 24, "align": "left", "erase": CLEAR},
     {"id": "cell", "ja": "万円", "text": "man", "style": "y", "font": BF, "x": 1, "y": 174, "w": 46, "h": 30, "size": "auto", "max_size": 18, "align": "center",
      "erase": {"mode": "flat", "color": [0, 82, 82]}, "erase_rect": [0, 174, 48, 31]},
     {"id": "stripend", "ja": "万", "x": 234, "y": 118, "w": 22, "h": 32, "erase": {"mode": "mask", "ink": YINK, "dilate": 1, "fill": "hfill"}}]
    if third:
        regs.append({"id": "oku", "ja": "億", "text": "oku", "style": "y", "x": 104, "y": 118, "w": 38, "h": 32, "size": 20, "min_sx": 0.4, "align": "center",
                     "erase": {"mode": "mask", "ink": YINK, "dilate": 1, "fill": "hfill"}})
    else:
        regs += [
         {"id": "oku", "ja": "億", "text": "oku", "style": "y", "x": 90, "y": 34, "w": 36, "h": 28, "size": 18, "min_sx": 0.4, "align": "center",
          "erase": {"mode": "mask", "ink": YINK, "dilate": 1, "fill": "hfill"}},
         {"id": "search", "ja": "捜索費用", "text": "Search Cost", "style": "silveri", "x": 155, "y": 34, "w": 98, "h": 28, "size": "auto", "max_size": 22, "align": "left", "erase": CLEAR},
         {"id": "income", "ja": "収入", "text": "Income", "style": "silver", "x": 88, "y": 163, "w": 62, "h": 28, "size": "auto", "max_size": 20, "align": "left", "erase": CLEAR},
         {"id": "total", "ja": "合計金額", "text": "Total", "style": "silver", "x": 158, "y": 163, "w": 100, "h": 28, "size": "auto", "max_size": 24, "align": "left", "erase": CLEAR},
         {"id": "cost", "ja": "費用", "text": "Expenses", "style": "silver", "x": 90, "y": 195, "w": 100, "h": 30, "size": "auto", "max_size": 20, "align": "left", "erase": CLEAR}]
    return {"texture": tid, "size": [256, 256], "supersample": 4, "quantize": "argb1555",
            "styles": {"y": YEL, "silver": CHROME, "silveri": dict(CHROME, shear=0.2, font=NF)}, "regions": regs}


w("00088", mon("00088 ATFIRST/SHTEX0.ZAR mon.tbd#0", False))
w("03642", mon("03642 ETC_DATA/SHTEX.ZAR mon.tbd#0", True))
print('ok')
