"""Writes build/tex/classify/part_8.json (classification of contact sheets 8-11).
Manual visual classification; this script only holds the data. Run: python -I -X utf8 tools/classify_part8.py
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "tex", "classify", "part_8.json")

# (id, sheet, has_jp, jp_text, en, kind, prio, region, notes, extra_regions)
R = []


def add(i, sheet, jp, text="", en="", kind="other", prio=0, region=None, notes="", regions=None):
    sid = "%05d" % i
    R.append((i, sheet, jp, text, en, kind, prio, region, notes, regions))


S8, S9, S10, S11 = "sheet_0008", "sheet_0009", "sheet_0010", "sheet_0011"

# ---------------- sheet 8 ----------------
reg_main = {
    "rows_menu_labels": [0, 40, 135, 235],
    "ketteibtn_shiai_kaishi": [133, 235, 407, 267],
    "shiai_kaishi_saidoro": [433, 272, 511, 351],
    "shuuryou": [73, 400, 147, 431],
    "daihyou_AB": [193, 437, 349, 511],
    "kaigai_ABC": [353, 395, 511, 511],
}
add(165, S8, True,
    "簡易選択 / 大会形式 / 試合形式 / 参加チーム / スタジアム / 選手規定 / 決定 / 試合開始 / 試合開始 / 再ドロー / 終了 / 代表A / 代表B / 海外A / 海外B / 海外C",
    "Quick Setup / Tournament Format / Match Format / Teams / Stadium / Player Rules / OK / Start Match / Start Match / Redraw / Exit / National A / National B / Overseas A / Overseas B / Overseas C",
    "menu_button", 1, [0, 40, 511, 511],
    "Best Players Match (BPMATCH) / Exhibition setup screen atlas (BMMAIN variant). 'MATCH REGULATIONS' header, 'ENTRY CLUB' and J1/J2 are Latin (keep). Six row labels are stacked on a green panel. Row-label widths ~135px: 'Tournament Format' will need a condensed font or 'Format'. Bottom-left grid: J1/J2 Latin, 代表A/B and 海外A/B/C are kanji+Latin letter: repaint only the kanji ('Nat. A' / 'Intl A' or 'Abroad A').",
    reg_main)
add(166, S8, False, notes="Latin-only backdrop art (EXHIBITION / LEAGUE / TOURNAMENT ghost text). Already English.", kind="other")
add(167, S8, True,
    "海外クラブ / 自動選択 / Jリーグ / 手動選択 / 国代表",
    "Overseas Clubs / Auto Select / J.League / Manual Select / National Teams",
    "menu_button", 1, [0, 1, 285, 237],
    "Participating-team selection buttons (help text refers to Jリーグ, 海外クラブ, 国代表 and 自動設定/手動設定). 512x256 atlas, each button ~137x76 px. Existing help-text glossary suggests: 'J.League', 'Overseas Clubs', 'National Teams', 'Auto' / 'Manual'. Button colour frames must be kept.",
    {"kaigai_club": [0, 1, 137, 77], "jidou_sentaku": [144, 1, 285, 77], "J_league": [0, 81, 137, 155],
     "shudou_sentaku": [144, 81, 285, 155], "kokudaihyou": [0, 161, 137, 237]})
add(168, S8, False, notes="Latin 'BEST PLAYERS MATCH' title (split across strip, already English).", kind="title")
add(169, S8, True,
    "簡易選択 / 大会形式 / 試合形式 / 参加チーム / スタジアム / 選手規定 / 試合開始 / 試合開始 / 再ドロー / 終了 / 代表A / 代表B / 海外A / 海外B / 海外C",
    "Quick Setup / Tournament Format / Match Format / Teams / Stadium / Player Rules / Start Match / Start Match / Redraw / Exit / National A / National B / Overseas A / Overseas B / Overseas C",
    "menu_button", 1, [0, 40, 511, 511],
    "Blue-panel variant of #165 (BPMATCH atlas). Same labels; 'ENTERED' badge and 'MATCH REGULATIONS' are Latin (keep). Translate consistently with #165.",
    {"rows_menu_labels": [0, 40, 135, 235], "shiai_kaishi_header": [184, 240, 413, 267],
     "shiai_kaishi_saidoro": [433, 276, 511, 349], "shuuryou": [73, 399, 147, 429],
     "daihyou_AB": [193, 432, 349, 509], "kaigai_ABC": [353, 396, 511, 509]})
add(170, S8, True,
    "海外クラブ / 国代表 / 自動選択 / Jリーグ / 試合開始 / 再ドロー / 手動選択",
    "Overseas Clubs / National Teams / Auto Select / J.League / Start Match / Redraw / Manual Select",
    "menu_button", 1, [0, 0, 428, 183],
    "Highlighted/active variants of the #167 buttons (ghost Latin 'OVERSEAS', 'NATIONAL', 'AUTO', 'J.LEAGUE', 'MANUAL' bleeds in behind the kanji, so the Latin underlay can be reused). Lower part (y 270+) is Latin 'BEST PLAYERS MATCH' backdrop: keep.",
    {"kaigai_club": [0, 0, 137, 80], "kokudaihyou": [141, 0, 281, 80], "jidou_sentaku": [288, 0, 428, 80],
     "J_league": [0, 87, 137, 167], "shiai_kaishi_saidoro_box": [144, 93, 237, 183], "shudou_sentaku": [288, 87, 428, 167]})
add(171, S8, False, notes="Latin 'BEST PLAYERS MATCH' title strip. Already English.", kind="title")
add(172, S8, False, notes="Stadium backdrop texture, no text.")
add(173, S8, False, notes="Blue pipe/bracket UI frame pieces, no text.")
add(174, S8, False, notes="Group A-H letter tiles (GROUP A..H), Latin. Already English.", kind="stat_label")
for n in (175, 176, 177, 178):
    add(n, S8, False, notes="CAP_SLCT 3D room backdrop (captain-select scene art), no text.")
add(179, S8, False, notes="'Club Edit', 'Secretary Select', 'Name&Mascot Select', 'Uniform&Flag Select' are ALREADY English in the original (CE_TEX). No translation needed. (Candidate to compare against the Club Edit kanji menu atlas elsewhere.)", kind="title")
add(180, S8, False, notes="Mascot face icons and flag tiles, no text.")
for n in (185, 186, 187):
    add(n, S8, False, notes="Green blurred stadium transition art, no text.")

# ---------------- sheet 9 ----------------
for n in range(188, 198):
    add(n, S9, False, notes="CE_TEX.TBD blurred stadium / transition art or blue lozenge, no text.")
add(198, S9, False, notes="CE_VS 64x64 greyscale sky art, no text.")
for n in (203, 204, 205, 206):
    add(n, S9, False, notes="CHALDANI backdrop with player statue (gold/silver/bronze/GK). Background blur contains Latin 'SOCCER' lettering only. No Japanese.")
add(207, S9, False, notes="Latin 'CHALLENGE MODE' title strip (split). Already English.", kind="title")

# ---------------- sheet 10 ----------------
add(208, S10, True, "免許皆伝",
    "Grand Master", "caption", 2, [0, 411, 333, 511],
    "Marble/blue panel atlas: numerals 1-11 in the list box are Latin digits (keep); the gold calligraphy 免許皆伝 (menkyo kaiden = 'full transmission', top rank) sits at the bottom-left. Check FLOW_PRG/CHALDANI strings for the final English term (currently untranslated in jsonl; 'Grand Master' proposed, shorter 'Master' if width is tight).")
for n, k, e in ((209, "一", "1"), (210, "二", "2"), (211, "三", "3"), (212, "四", "4"), (213, "五", "5"), (214, "六", "6"),
                (215, "七", "7"), (216, "八", "8"), (217, "九", "9"), (218, "十", "10")):
    add(n, S10, True, k, e, "stat_label", 2, [4, 12, 124, 116],
        "Gold brush-kanji numeral used to build rank captions (kyu/dan). Composed with #219-221 by the game: English arabic numeral (digit '10' needs two glyphs in one 128x128 cell). Layout of the composite is code-driven: verify how the code places the pieces before repainting.")
add(219, S10, True, "初", "1st", "stat_label", 2, [4, 12, 124, 116],
    "'First' prefix of 初段 (1st dan). Alternative: replace by '1' and reuse the dan glyph. 128x128 gold brush glyph.")
add(220, S10, True, "級", "-kyu", "stat_label", 2, [4, 12, 124, 116],
    "Kyu suffix glyph. Style guide: '10級' -> '10-kyu'. Use 'Kyu' (no hyphen) in gold lettering; 3 letters fit 128px at ~40px height.")
add(221, S10, True, "段", "-dan", "stat_label", 2, [4, 12, 124, 116],
    "Dan suffix glyph. Style guide: '7段' -> '7-dan'. Use 'Dan'.")
add(222, S10, True, "敗退 / 完全制覇",
    "Eliminated / Total Victory", "caption", 2, [0, 4, 327, 231],
    "512x256 gold calligraphy captions: 敗退 (knocked out) at top-left, 完全制覇 (complete conquest) below. Strings 'FLOW_PRG/CHALDANI.BIN#c424' share the same term; keep wording identical ('Total Victory' / 'Clean Sweep').",
    {"haitai": [0, 4, 253, 124], "kanzen_seiha": [0, 131, 327, 231]})
add(223, S10, False, notes="Blue stadium backdrop with blurred Latin letters only. No Japanese.")
add(227, S10, True,
    "欧州オールドスターズ / 欧州スーパースターズ / 南米オールドスターズ / 南米スーパースターズ / アジア・スターズ / ジャパン・スターズ / 北欧・スターズ / バルカン・スターズ",
    "European Old Stars / European Superstars / S. American Old Stars / S. American Superstars / Asia Stars / Japan Stars / Nordic Stars / Balkan Stars",
    "menu_button", 2, [0, 0, 256, 256],
    "Eight opponent-team names for Challenge Mode, one per 32px row in gold-on-black text, 256 wide (about 21 chars at ~12px, so names must be condensed). Must match the string table at FLOW_PRG/CHALDANI.BIN#c434.. (ジャパン・スターズ, アジア・スターズ, 北欧・スターズ, バルカン・スターズ already listed there). Rows are y=0..255 step 32.")
add(228, S10, True,
    "さかつく・スターズ / ワールド・スターズ / アフリカ・スターズ / スペイン・レジェンズ / フランス・レジェンズ / U.K.・レジェンズ / ドイツ・レジェンズ / オランダ・レジェンズ",
    "Sakatsuku Stars / World Stars / Africa Stars / Spain Legends / France Legends / U.K. Legends / Germany Legends / Netherlands Legends",
    "menu_button", 2, [0, 0, 256, 256],
    "Eight rows (32px pitch), same style as #227. 'Netherlands Legends' is 19 chars: may need 'Dutch Legends'. Keep wording identical to the string table (c494 'さかつく・スターズ' etc.).")
add(229, S10, True,
    "イタリア・レジェンズ / ブラジル・レジェンズ / アルゼンチン・レジェンズ / ウィング・ファームズ / ドリーム・スターズ",
    "Italy Legends / Brazil Legends / Argentina Legends / Wing Farms / Dream Stars",
    "menu_button", 2, [0, 0, 256, 160],
    "Five rows (32px pitch). ウィング・ファームズ is the final boss club (help text: beating it = Total Victory); 'Wing Farms' proposed (UNKNOWN official reading: could be 'Wing Firms').")
add(230, S10, False, notes="'CHALLENGE-MATCH' stadium scene, banner text is Latin. Already English.", kind="title")
add(231, S10, False, notes="Blank marble plaque (128x64), no text. Backing for the rank plaques; the Japanese is drawn in other textures.")
for n in (232, 233, 234):
    add(n, S10, False, notes="Locker-room / stadium coloured backdrop, no text.")
add(235, S10, True, "初段", "1st Dan", "stat_label", 2, [19, 11, 109, 51],
    "Marble plaque with 初段 (1st dan) in dark engraved lettering (CHALMODE.ZAR). Same style as the CH_DANI plaques #238-#258; 128x64.")
add(236, S10, False, notes="Flat dark blue 64x64 tile, no text.")

# ---------------- sheet 11 ----------------
plaque_region = [14, 12, 114, 54]
names = {
    238: ("十級", "10-kyu"), 239: ("九級", "9-kyu"), 240: ("八級", "8-kyu"), 241: ("七級", "7-kyu"),
    242: ("六級", "6-kyu"), 243: ("五級", "5-kyu"), 244: ("四級", "4-kyu"), 245: ("三級", "3-kyu"),
    246: ("二級", "2-kyu"), 247: ("一級", "1-kyu"), 248: ("初段", "1st Dan"), 249: ("二段", "2-dan"),
    250: ("三段", "3-dan"), 251: ("四段", "4-dan"), 252: ("五段", "5-dan"), 253: ("六段", "6-dan"),
    254: ("七段", "7-dan"), 255: ("八段", "8-dan"), 256: ("九段", "9-dan"),
}
for n, (jp, en) in names.items():
    add(n, S11, True, jp, en, "stat_label", 2, plaque_region,
        "CH_DANI plaque (128x64, marble frame, engraved orange-gold kanji; frame is Latin-free art and stays). Rank shown after a Challenge match. English follows style guide (10-kyu, 7-dan); '初段' = '1-dan' per guide, '1st Dan' is a suggested alternative for plaque.")
add(257, S11, True, "免許皆伝", "Grand Master", "stat_label", 2, [10, 12, 118, 54],
    "Top-rank plaque; four kanji in lighter olive-gold. Keep wording identical to #208 and CHALDANI strings (c418).")
add(258, S11, True, "特別対戦", "Special Match", "stat_label", 2, [10, 12, 118, 54],
    "Plaque for the special bonus opponent match (not a rank). Four kanji in olive-gold.")

# ---------------- output ----------------
out = []
for (i, sheet, jp, text, en, kind, prio, region, notes, regions) in R:
    d = {
        "id": None,  # filled below
        "sheet": sheet,
        "has_japanese": jp,
        "japanese_text": text,
        "english_suggestion": en,
        "kind": kind,
        "priority": prio if jp else 0,
        "region": region if jp else None,
        "notes": notes,
    }
    if regions:
        d["regions"] = regions
    d["_n"] = i
    out.append(d)

# resolve ids from sheet_map.json
import json as _j
m = _j.load(open(os.path.join(ROOT, "build", "tex", "sheets", "sheet_map.json"), encoding="utf-8"))["sheets"]
idmap = {}
for s in (S8, S9, S10, S11):
    for it in m[s]["items"]:
        idmap[it["n"]] = it["id"]
final = []
seen = set()
for d in out:
    n = d.pop("_n")
    d["id"] = idmap[n]
    seen.add(n)
    final.append(d)
missing = [n for n in idmap if n not in seen]
print("missing:", missing)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=1)
print("total", len(final), "with_japanese", sum(1 for d in final if d["has_japanese"]))
