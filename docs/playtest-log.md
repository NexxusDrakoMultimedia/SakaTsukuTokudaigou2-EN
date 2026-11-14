# Playtest log (user-driven Flycast sessions)

Each entry: build, screen, what was seen, status. "A/B/C/D" = tasks of workflow `playtest-findings-1` (data tables, number
formats, window widths, layout). Texture art is tracked by the image workflow.

## Session 1 - 2026-11-10, trial_plain (full English, fixed-width font), Redump disc 27370 source

| Screen | Seen | Cause / owner |
|---|---|---|
| Name Entry (letters) | Each grid cell took two letters | The picker grids in N_ENTRY are 2-byte-cell data tables; translating them to half-width broke them. FIXED: the five records restored to Japanese + skip. English names use the full-width 英数字 page. Optional later: patch cell stepping for half-width. |
| Name Entry tabs, secretary profile card, "未定", "SCHEDULE", "Today/Home/Away", 前月/翌月/終了, 収支報告, 地元団体, 年間総収入 etc. | Japanese | Baked-in texture art (image workflow). |
| Rival club intro | Club name サリーレ in Japanese | Club-name data table not covered (A). |
| Hometown list | Towns (青ヶ島村, 延岡市, ...) Japanese; "To ho ku" / "Ka ns ai" letter-pair gaps; "Izu Is." + town | A (town table), D (spacing). |
| Club name choice popup | "Aogashiミュートス" | Club-suffix table not covered (A). |
| Event list / player card | "Isao Nakagak" clipped; managers/coaches (織田 道三, ﾙﾄﾞﾅｯﾌﾟ, ﾋﾞﾗｶｽ) Japanese | D (widths), A (staff tables). |
| Speech bubbles | "any dream can com/e", "heav/y" wrapped mid-word, overflow the box | Window width is 33 cells not 39 (C). |
| Money lines | "130015000,00", "60000,00", "3200?000 man", "4 oku 0000 man", "3 oku 6200 man", "Y 26M" | Money expander prints Japanese 億/万 groups (B). |
| Finances screen | Labels/rows English; amounts as above; heading "J.League DIVISION 2" ok | B. |
| Schedule/Office | "MD 1." and "Jリーグ ディビジョン2" mix; J2 club names (パープルサンガ, アルビレックス, サガン, ベガルタ, ヴァンフォーレ, アルディージャ, 横浜FC, サリーレ) Japanese | Club names table (A). |
| Overseas camp country list | カメルーン, スペイン, スコットランド, ハンガリー, ブラジル, チリ, コロンビア, ウルグアイ Japanese | Country-name table (A). |
| Sponsor list | Names overflow their columns, "Aoashi Civic Society" overlaps the heading texture | D. |

## Session 1, part 2 (same build)

| Screen | Seen | Owner |
|---|---|---|
| Practice > Player Placement | On-pitch name labels clipped to ~4 letters ("Kenj", "Dais", "Susp", "Akir", "Ryoj") | D / field-widening |
| Practice > player card | "GK/ 9 yrs", "1cm 2kg": leading digits lost (age and height/weight clipped on the left) | D / field-widening, B (number tokens) |
| Hometown status | "Izu Is. Aogashima" (English town name exists here, so a second, translated table is used), stat labels in art (人口 地価 交通 住宅 商業 ...) | A, image workflow |
| Local Info bubble | "There's enough greenery for a fai/rly" wraps mid-word | C |
| Match intro / scoreboard / results / standings / scoring and rating rankings | Club names Japanese (ミュートス, パープルサンガ, サリーレ, フロンターレ, トリニータ, ベルマーレ, ベガルタ, ...) in lists and in dialogue lines ("ミュートス have lost"), stadium "ミュートス スタジアム"; column headers (順位, 勝点, クラブ名, 選手名, 総得点数, ...) and "第1節", "ゴール" Japanese | A (club/stadium tables), image workflow or strings (to check) |
| Match results | player names English (M. Kurobe, Bentinho, Y. Abe) work | - |

User note (2026-11-10): "We should probably look to expand the bounds of some fields, and shrink some other usages."
Plan: after tasks C and D report, a field-geometry workflow: (1) find every text field/panel/column width constant (window
constructors, label tables, column offsets), (2) widen the ones that can grow safely (code/data immediates, with SH-4
encode checks like tools/fontpatch.py), (3) for fields that cannot grow, give the translators per-field limits and shorter
forms (names: initials/family name; labels: abbreviations), (4) re-run the fit/validator with the new limits.
