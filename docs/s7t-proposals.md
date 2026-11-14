# s7t proposals (text / layout leftovers of the 2026-11-12 playtest)

Owner: s7t.  Status of each item, the code patches the integrator has to wire (tools/layoutpatch.py, fontpatch.py,
patchengine.py are owned by the align owner and were NOT touched), and what turned out to be art.

## 1. Stadium line `Mythos` + katakana (FIXED, data side)

`%sｽﾀｼﾞｱﾑ` (half-width katakana, 8 bytes + NUL + 3 zero bytes = a 12-byte slot) sits at `0x39574` of **SCHE0.BIN and SCHE1.BIN**
(pointer word `0x8c509574` at `0x39e0` in SCHE0 but at `0x39d8` in SCHE1, checked by the skeptic; a second copy at `0x38e54` in both; the match-preview / schedule overlays).  `textdb`, `textfmt_hwkana` and `textfmt_gap` all missed it
(the string starts with `%s`, so it is neither pure half-width kana nor pointer-table text).
Fix: two curated entries in `tools/textfmt_gap.py` (`GAPS`, new optional fourth element `slot` = the all-zero bytes the record may use)
and two records `FLOW_PRG/SCHE0.BIN#39574` / `SCHE1.BIN#39574` (`fmt gap`, `max_bytes 12`) with `en = "%s Stadium"` (10 bytes + NUL,
the same text as `GAME.BIN#1940bc`, `BCAST` `X Stadium`).  `tools/test_gap.py` counts 25 entries now.
The other `ｽﾀｼﾞｱﾑ...` strings (PWK_EDIT `ｽﾀｼﾞｱﾑ改築/施設/屋根`, 12-byte slots, `en` empty) belong to the stadium editor menu and were not part
of this task.

## 2. Practice > Player Placement name tags `Taiy`, `Keij`, `H.` (ROOT CAUSE FOUND, code patch proposed)

Root cause (PROVEN by disassembly, `tools/re/aln_dis.py TRAINING 0x15318 0x153b0`): the tag text is built by a shared routine
`short_name(dest, name)` (TRAINING.BIN file `0x15318`, va `0x8c2e5318`):

```
i = 0
while (i < 4 && name[i] != ' ' && name[i] != 0) buf[i] = name[i], i++     /* mov #4,r3 ; cmp/ge r3,r1 at file 0x1533c */
buf[i] = 0
sprintf(dest, (i == 1 || i == 2) ? " %s " : "%s", buf)                     /* FMT1 ' %s ' , FMT2 '%s' */
```

So it takes the FIRST blank-separated word of the 14-byte BPINFO name and keeps at most **4 bytes** (Japanese `surname given`: the
first word is the surname, two kanji = 4 bytes).  English names are `Given Family` (style guide 7.1), so the tag shows the first 4
letters of the given name (`Taiy`, `Keij`, `Seig`) or the initial (`H.` from `H. Nakata`).  It is a fixed constant of the code:
nothing in the translation data can change it.  The routine has a stack protocol of its own (variadic arguments of the sprintf
are pushed: `[sp] = fmt`, `[sp+4] = buf`).  The routine is byte-identical in **11 overlays** (`tools/re/s7t_sigscan.py`
signature `04e3f25133310a89f352f2502c000e602088`): CAP_SLCT `0x118b8`, ENDOPT `0x2e558`, EVENT `0x4ba14`, GAME `0x6f428`, G_RESULT
`0xc41c`, NEWCON `0x209ec`, NEWS `0x21d4c`, OFFICE `0x283b4`, TOWN `0x26d30`, TRAINING `0x15318`, YOUTH `0x14014` (entry offsets).
(The name labels of the other overlays use it too; all callers get the same new behaviour.)

### Proposed patch (verified, not applied)

Replace the 152-byte routine in place (entry `= site - 0x24` above) with a routine that takes the LAST blank-separated word (the family
name: `Nakata`, `Kawamoto`) and keeps up to `LIMIT = 7` bytes (the local buffer is 8 bytes; 7 letters + NUL), same pad rule for 1-2
letters, same pool words, no callee-saved register touched, 112 of the 152 bytes used (the rest `nop`).  Source and test:
`tools/re/s7t_shortname.py` (assembled with `tools/sh4asm2.py`, executed in `tools/sh4sim.py` against a Python reference for 12 names,
callee-saved registers and stack checked).  `python -I -X utf8 tools/re/s7t_shortname.py --emit` writes
**`build/s7/shortname_patch.json`**: per overlay `{offset, va, old (152 bytes), new (152 bytes)}`, after checking that the old bytes are
the known routine (the three pool words are read from the overlay).  Integration: in the patch engine add one "overwrite 152 bytes at
offset if the old bytes match" step per overlay (the same shape as the other `old -> new` hooks; refuse if `old` differs).

Open points the integrator / a Flycast check must settle (NOT verifiable here; nothing was launched):
* The **tag window width**.  The label is drawn by `PlnameTask` (TRAINING `0x3391c..`, "ytMes PlnameTask") through `zlString`;
  whether the window is clipped to 4 cells or auto-sizes is not decoded.  If it is clipped, set `LIMIT` to 5 or 6 (one constant in the
  script) and re-emit; `Nakata`/`Kawamoto` read well in 6-7 letters, `Yamada` needs 6.
* The **black empty name boxes** and the **`CF` icon overlapping a name** are separate: the box and the position icon are
  fixed-size sprites placed by the placement table; longer names make the text run into the icon.  If the icon overlaps after the patch,
  lower `LIMIT` to the icon-free width or move the name x position (placement table `+0x4a/+0x4c` of the window, docs/font-hook-notes.md).
* Double-byte names (a name still in kanji) would be cut mid-character at 7 bytes; every English name is single-byte, so this only
  matters for an untranslated record.

## 3. Meeting `Complain.` and the strength meter labels (ART, not text)

`Complain.` is not a string (no `Complain` record exists in the database): it is the texture **03266** (Meeting screen meter:
`Weakness`, `Selling Point`, `Complaint`, `Club Feedback`) installed by the stage-6 art owner (spec `tools/re/art6_gen_misc.py`, row
`R('comp', '不満', 'Complaint', 8, 169, 62, 24)`: the box is 62 px wide, the painted word got shortened to `Complain.`).  The two
strength-meter end caps (弱 / 強, `Weak` / `Strong`, x195-222 and x225-252, y140-165) are still Japanese (art sweep v3 package F).
Both are art owner items (03266); the text side (`MEETING.BIN` `Flaw/Plus/Gripe`, `Player: Picked: ...`) is unchanged.

## 4. Black rectangle above `4-4-2` (draft / manager panel) (NOT FOUND)

Findings: the formation `4-4-2` is not a string of SCDRF/SEARCH/DRAFT (the only `4-4-2` strings of the disc are in GAME.BIN `0x19be44`,
HELP, ABROAD), the row text above it in the panel is the fixed table `SCDRF.BIN tbl@1cd14` (tactic words `Post Play` ... `Guts` `C B A S`) and
`tbl@7880` (`%4d/%d yrs`, `Wants %2d yrs`, `Age %2d`) - all of them non-empty, so no empty string draws a window.  The only empty
record next to them is `SCDRF.BIN#32c80` (`　` ideographic blank, `en` empty, unchanged, 4 bytes, `ptr@65a0`), which draws exactly what
the Japanese build draws.  `tools/re/ar5_blackscan.py` finds no new opaque black texture area (docs/art-translation.md section 10).
Remaining candidates (need a screenshot or a Flycast frame dump of that panel; neither is possible without launching the emulator):
(a) a text window whose width follows the string length, drawn black behind the longer English `Manager` / `Scout` labels
(`SCDRF#32cd4`, `#32cdc`, slots 8 / 12 bytes, original 4 / 8 bytes); (b) a texture that failed to load.  Cheap test for (a): build with
`en = ""` for `#32cd4` / `#32cdc` and see whether the rectangle disappears.

## 5. Attract demo: HOME / AWAY `静観` and the Japanese commentary box

* `静観` is **not text**: the only cp932 hit on the disc is the IME dictionary of `2_DP.BIN` (false hit).  It is the second line of the
  in-match team-instruction sprite **`GAME/GAMEETC.ZAR` `@110/sakusen.pvr` (id 34716, 128x128 ARGB4444/VQ, four lines
  `攻めろ守れ / 静観攻守 / 全員守備 / 全員攻撃`)**, `injectable false` in `build/art/groups_v3.json` (the sweep could not inject it).
  Art owner item: needs an injector path for the VQ member before it can be repainted (`Attack/Defend`, `Hold`, `All Defend`, `All Attack`).
* The commentary box is the `BCAST/BCAST.BIN` clip text (not a string or texture): 20,914 of 30,083 segments are English; the rest
  (kk 2,814 of 3,518, mm 2,518 of 3,267, mt 2,512 of 3,320, yh 1,325 of 7,498; `tools/re/s7t_bcast_stat.py`) still show Japanese.
  That is a translation volume job (about 9,170 lines), not a bug of the subtitle control.

## 6. Money units `Y 10000k` / `%d k`

* The unit tables `万円 / 円 / 0円` ARE cleared (`en ""`, `skip`) on purpose (the money cave prints the amounts); LOCAL.BIN
  `tbl@9620` is one of them.  A `Y 10000k` / `k` text can only come from the **old western pieces**, i.e. a build without
  `--money-format on` or the `0k` records below.
* Western-style units still in the database (`tools/re/s7t_kfmt.py`): `G_INCOME.BIN#26490` `万 -> 0k` (income screen, **visible**,
  money owner: should be `man` / handled by the cave), `GETREP.BIN#26c28`, `SPT_CLUB.BIN#c50c`, `MEETING.BIN#9c954`, `RECON.BIN#21260`,
  `SCHE0/1.BIN#396c8` (debug/schedule cost lines; set by s7t to lower-case ` man`), `NENREP.BIN#24ef8` (`333?@R/Y%s/%s@`),
  and the list line `%3d %-13s Y%d %d yr` (HELP / TITLE / LOCAL / SCDRF / SPF_READ / WEEKLY / TITLE: a debug list, 20-byte slot, no room
  for `Yen`).  Sites for the money owner: only `G_INCOME#26490` and `NENREP#24ef8` are plausible player-visible rows.
