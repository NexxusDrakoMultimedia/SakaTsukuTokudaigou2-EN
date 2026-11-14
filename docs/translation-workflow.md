# Translation workflow (shards, translator contract, validator, merge, disc rebuild)

> **Status note (docs, 2026-11-11).** The record and distinct-text counts in the diagram below (126,273 / 29,122, `en` empty) are the stage-1 numbers; the database now has 368,492 records and 35,898 distinct texts including the table records (docs/uncovered-text.md), and `python -I -X utf8 tools/transmerge.py status` gives the live figures. The workflow itself is unchanged.

Tools: `tools/transwork.py` (plan), `tools/transcheck.py` (validator), `tools/transmerge.py` (merge + status), shared code in
`tools/translib.py`, self-test `tools/test_transwork.py`.  Pure stdlib, always `python -I -X utf8 ...`, deterministic, the
whole real-database plan takes about 2 s.  Nothing here launches an emulator or touches `extracted/`.

```
translation/*.jsonl (126,273 records, en empty)
      │  transwork.py plan          group by distinct ja (29,122), classify, budget, order, cut into shards
      ▼
build/trans/shards/NNNN.json  ──►  translator agent  ──►  build/trans/results/NNNN.json
                                         ▲   │  transcheck.py RESULT.json  (repair loop until exit 0)
                                         └───┘
      │  transmerge.py merge RESULT.json…   validate again, write en to EVERY record with the same ja, backup, atomic
      ▼
translation/*.jsonl (en filled)  ──►  tools/build_patch.py  ──►  build/out/SakaTsuku2-EN.gdi
```

`en` in `translation/*.jsonl` is written only by `transmerge.py merge` (and, for the single-string fixes of docs/style-guide.md
s10, by hand).  `textdb.py extract` no longer erases translations (see "Re-extracting" below).

## 1. Planning: `transwork.py plan`

```
python -I -X utf8 tools/transwork.py plan [--tdb translation] [--out build/trans]
```
Outputs (all rewritten on every run; stale shard files are deleted): `build/trans/shards/NNNN.json`, `index.json` (one row per
shard), `plan_summary.md` (counts per category / area / shard), `skip_report.tsv` (every skip-hinted text, for auditing).
The plan ignores the `en` fields, so shard numbers and keys do not move while the translation advances; re-plan only when the
jsonl files are re-extracted (and then check `status`).

**Distinct texts.** Records are grouped by the exact Japanese text.  One *item* = one distinct text; `key` = first 12 hex digits of
`sha1(ja as utf-8)` (collisions are checked).  The English of an item is written to all its records.

**Canonical occurrence.** An item is placed where the player meets it first: the occurrence with the lowest (area, source position,
file line).  That occurrence decides category, `ctx`, `prev` / `next` (the neighbouring Japanese strings in that source file, in
source order, 60 characters each).

**Priority order (areas)**, `transwork.AREAS`: title (TITLE, OPTION) → new_game (S_SELECT, N_ENTRY, HEREWEGO, INITCON, CLUBEDIT,
CAP_SLCT, NEWUNIF, PLNUMSET, PL_EDIT, SEARCH, SPF_READ, SCDRF) → save_load → menus (GAME, OFFICE, ESTABLIS, GETREP, NENREP, INVEST,
LOCAL, HOMETOWN, SPONSOR, DRAFT, NEWCON, RECON, FIRE, YOUTH, ABROAD, ...) → meeting (MEETING) → news (NEWS_OP, NEWS, NEWS_ED) →
event (EVENT, TV_EVENT, JSCEVENT, SELNAT, GAMEOVER, ENDING) → training (TRAINING) → help (HELP) → match_ui (G_INCOME, BPMATCH,
CHALMODE, SCHE0/1, ENDOPT, ...) → players (BPINFO names) → rest (every other overlay) → dev (PWK_EDIT, FLOW1-11) → browser
(Dream Passport: MESSAGE.INI, 2_DP.BIN) → junk (debug / binary / skip-hinted).  Inside an area the order is category rank
(label, numunit, system, dialogue, meeting, news, event, training, help, tactic, dataroom, place, name, browser, debug, binary),
then source, then source order.  Table-sized name / place lists therefore come after the prose of the same screen.

**Categories** (`transwork.classify`, judged on the canonical record: source file, `ctx`, shape, length):

| category | what | notes |
|---|---|---|
| name | person names (BPINFO, 14-byte name tables, hw-kana foreign names, PLNUMSET hiragana readings) | ladder `Given Family` → `G. Family` → `Family` |
| place | municipalities / prefectures / readings (HOMETOWN) | no City/Pref. suffix; fixed 8/12-byte slots |
| label | short UI labels and menu entries | space ladder |
| numunit | numbers with units / formats (`%d位`, `３級`) | |
| system | save / load / VM messages | |
| dialogue | other prose (secretary, scouts, managers, offices, SS_EDIT ...) | |
| meeting, news, event, training | prose of MEETING / NEWS* / EVENT, TV_EVENT, JSCEVENT / TRAINING (news headlines `#tkNN#...` count as news) | |
| tactic | TRAINING texts in fixed in-place slots (orphans) | write at slot length |
| help | HELP.BIN pages | |
| dataroom | DATAROOM / DRS* record screens | |
| browser | Dream Passport UI (MESSAGE.INI, 2_DP.BIN) | dead service, last |
| debug | developer text (ASCII identifiers, `TEAM:%d`, `ダミー`, PWK_EDIT ...) | skip hint |
| binary | binary data read as text, blank | skip hint |

**Skip hints.** `skip` is a string for blank / ASCII-only / debug / binary / single IME kana items and null otherwise.  They stay in
the plan (junk area, last shards) and in `skip_report.tsv`; a translator may leave them out, return `""`, return the Japanese
unchanged (then the record gets `"skip": true`, `en = ja`), or translate them if they are clearly player-visible.  A hint is a promise
that the player never sees the text, so the rules are narrow ("when in doubt do not skip": an unneeded translation is cheap, a missing
one ships Japanese).  A Latin word, a colon or the word "test" is NOT enough: shop "test sale" dialogue, the club-URL announcement,
`BESTPLAYERS MATCH` / `CHALLENGE MODE` descriptions, the GMSHOW02 network text and the SS_EDIT `REPEAT` / `END` help are all translated.
A text is hinted only when it is
* blank (nothing but whitespace; `%s` + a full-width space is a layout string, not blank), pure ASCII, or one IME kana cell;
* binary junk read as text (kanji-less symbol soup, the 曙 / 酔 / 糟 pointer fragments, raw `<XX>` bytes);
* developer text with no sentence content: a code identifier (`bcFunc`, `NsMessegeGetTeamScore`, `GM_AI_CHC_TYPE_DF`, `jstat[1]`,
  `PWK_...`; also with a sentence, never in HELP), a variable dump (`tm:%d`, `team = %d`), dummy / debug / dump vocabulary,
  `...フラグ` next to a `%d` value (`トレード禁止フラグ %d(%d)`), or a PWK_EDIT screen label;
* a text whose EVERY record is listed in **`tools/trans_skip_ids.txt`**: the data-driven list of known extraction false positives
  (pointer tables read as text, e.g. `FLOW_PRG/NEWS_OP.BIN#28f21` `緒喧`).  One record id per line, `#` starts a comment.  If one
  record of the text is not listed the text is NOT hidden.  `plan --skip-ids FILE|none` overrides the list and the plan prints how
  many listed ids no longer exist (after a re-extract).  Add an id only when sure; the file is the place to fix a missed junk text.
Still audit `skip_report.tsv` once: a debug-looking text that is really on screen is a hole (move it out by making the rule narrower).

**Budgets.**  A record is *fixed* when it can only be overwritten in place: orphan, no pointer, `stride-table`, `interior-ptrs`
(docs/capacity-design.md section 1), every BPINFO name (14-byte field) and every 2_DP.BIN string.  MESSAGE.INI has no limit.
* `budget_fixed` = the smallest `max_bytes` (string + NUL) over the fixed records of the text, `null` if none; `max_chars_fixed` =
  `budget_fixed - 1`.
* `budget_min` = smallest `max_bytes` over all records (guide for movable text), `null` for MESSAGE.INI.
* `soft_max_bytes` = `int(1.05 x (JP bytes + 1))` for movable text (L4 discipline: prose about 0.85 x natural English).

**Shards.**  Items of one area and category, in source order, are cut into shards of 125 items (the remainder is merged into the
previous shard when below 40 and the result stays within 150).  Long-prose shards close earlier at 12,000 Japanese characters.  A shard
file is `{shard, category, area, source, sources, guidance, n_items, items:[...]}`, one item per line:
`key, ja, ids_count, budget_fixed, budget_min, tokens, lines, ctx, prev, next, skip, kind, id0, soft_max_bytes, max_chars_fixed`
(`kind` = overlay | ini | bpinfo | ptrblob, `id0` = canonical record id, `lines` = number of lines of the Japanese, `tokens` = its
control tokens in order).  `transwork.py show N` lists a shard compactly, `transwork.py ids KEY` lists every record id of a text.

## 2. The translator contract

`python -I -X utf8 tools/transwork.py prompt N` prints the complete prompt for shard N (instructions + category guidance + the shard
JSON).  What an agent receives and must return:

* **Receives**: the shard file `build/trans/shards/NNNN.json` (and `docs/style-guide.md`, `translation/glossary.tsv`).
* **Returns**: `build/trans/results/NNNN.json` = `{"shard": N, "results": [{"key": "...", "en": "..."}, ...]}` with one entry for every
  item that has no `skip` hint (`key` copied exactly; extra fields such as `note` are ignored; `{key: en}` maps are also accepted).
* **Runs** `python -I -X utf8 tools/transcheck.py build/trans/results/NNNN.json` and repairs every ERROR before finishing.
* **Rules** (the validator enforces them): ASCII 0x20-0x7E plus `\n`; no `\` `~`; never type `@ = #` or a lone `%`; keep the control
  tokens of the Japanese (same multiset, printf formats in the same order, colour / window spans open-close); at most 39 cells per line
  (token widths below); no more lines than the Japanese; `len(en) + 1 <= budget_fixed` for fixed slots; no stray leading / trailing
  spaces.  Style: British English, football / match / pitch / kit, Owner, honorifics dropped, staff polite and warm, players keep
  their voice, prose at about 0.85 x natural length (`soft_max_bytes`), consistent terms across shards (glossary wins).
* Same Japanese means same English: the item is one text however many records use it.

## 3. The validator: `transcheck.py`

```
python -I -X utf8 tools/transcheck.py RESULT.json [--shards DIR | --shard-file PATH] [--json] [--rejects PATH]
                                      [--extra-lines N] [--allow-missing] [--quiet]
```
Exit 0 = no errors (warnings allowed), 1 = validation errors in a well-formed file, 2 = malformed or unreadable input (not JSON /
not UTF-8, top level not an object, `results` missing / null / not a list or map, `shard` not a number, shard file missing or
broken) or usage.  A UTF-8 BOM is accepted.  Entries that are not objects with a string `key` (also a list-typed key) are `BAD_ENTRY`
errors (exit 1), a lone surrogate in `en` is a `NON_ASCII` error; neither crashes the report.  `--json` prints the structured
report (for malformed input `{"ok": false, "malformed": ...}`), `--rejects PATH` writes a
repair work order `{shard, repair:[{key, ja, en, errors:[{code, msg, hint, ...detail}], item}]}` for a repair agent.
Every error has `code`, `msg`, `hint` and detail fields (`over`, `width`, `line`, `missing` / `extra` tokens, ...).

| code | rule |
|---|---|
| EMPTY | empty en (only skip-hinted items may be empty) or whitespace-only en (invalid for EVERY item; the one exception: a skip-hinted blank Japanese kept identical) |
| NON_ASCII | a character outside 0x20-0x7E other than `\n` (suggests the ASCII replacement for quotes, dashes, accents) |
| FORBIDDEN_CHAR | `\` (draws as yen) or `~` (overline) |
| STRAY_CHAR | `@ = #` or lone `%` outside the control tokens of the Japanese (browser text: only `%`) |
| TOKEN_MISMATCH | control-token multiset differs from the Japanese (missing / extra; an extra `@` `=` means you typed one) |
| TOKEN_ORDER | `%s %d %D %m` ... reordered (they are filled positionally), or colour `@X/..@` / window `=X/..=` spans no longer open-close |
| LINE_TOO_WIDE | a line over 39 cells; widths: ASCII 1, `#sname#` / `#tkNN#` 10, other `#x#` 8, `$N` 6, `%s` 8, `%d` 3, `%D` 6, `%m` 15 (jp money style; `%Nd` at least N), colour / window tokens and `<XX>` 0 |
| PUNCT_AT_EDGE | a 39-cell line ending in `. , ! ?` |
| TOO_MANY_LINES | more lines than the Japanese (`--extra-lines N` allows N more for movable items; fixed slots never) |
| OVER_BUDGET | `len(en) + 1 > budget_fixed` |
| LEADING_SPACE / TRAILING_SPACE / EMPTY_LINE | layout whitespace the Japanese does not have (indent / alignment spaces are allowed when the Japanese has them) |
| NEWLINE_IN_INI | newline in a one-line MESSAGE.INI value |
| MISSING / UNKNOWN_KEY / DUPLICATE_KEY / BAD_ENTRY | result-file level problems (MISSING only for non-skip items) |

Warnings (never fail): `WARN_LONG` (movable text above 1.05 x the Japanese bytes), `HONORIFIC`, `STACKED_PUNCT`, `ELLIPSIS`,
`DOUBLE_SPACE`, `US_SPELLING`, `EMPTY_SPAN`.  Browser text (MESSAGE.INI, 2_DP.BIN) uses HTML tags / entities as tokens and has no width rule.

The token widths are the assumptions of docs/capacity-ratio.md section 7, not measured values; if a width test (docs/capacity-ratio.md
section 9, test 2) changes them, edit `translib.WIDTH_SUBST` / `_fmt_cells` and re-run the checks.

## 4. Merging: `transmerge.py merge`

```
python -I -X utf8 tools/transmerge.py merge build/trans/results/*.json [--overwrite] [--require-complete] [--all-or-nothing] [--dry-run]
```
* Each result is re-validated against its shard; **failing items are refused** (not written) and listed with their errors in
  `build/trans/rejects/NNNN.json` (repair work order); the valid items of the same file are merged.  `--all-or-nothing`: one failure
  (refused item, BAD_ENTRY or malformed file) refuses the run.  `--require-complete`: items without a result count as failures.
* **Malformed files are reported separately, never fatal for the batch**: a result file that cannot be used at all (missing,
  not JSON / UTF-8, top level not an object, `results` missing / null / not a list or map, bad `shard`, shard file missing) is listed
  under `MALFORMED result files`, and every other file of the call is still merged.  Entries that are not objects with a string
  `key` are counted as `BAD_ENTRY` (not merged, listed).  A UTF-8 BOM is accepted.  Whitespace-only `en` is refused for every item.
* **Lock**: a real (non dry-run) merge creates `build/trans/merge.lock` (`O_EXCL`; `--lock-file`, `--lock-timeout`, default 60 s)
  around "load database -> write files" and re-reads the database inside the lock, so two concurrent merges serialise and no update
  is lost (backup counters stay distinct).  The lock is removed on exit, also after an error.  A crashed run can leave the file
  behind; a pid check is not portable, so a waiting merge gives up after the timeout with a message naming the file: delete it if
  no merge is running.  Under the lock stale `*.jsonl.tmp` files (and `*.json.tmp` in the rejects dir) of a crashed run are removed.
* **Paths**: every path argument (result files, `--tdb`, `--shards`, `--shard-file`, `--backup-dir`, `--rejects-dir`, `--lock-file`;
  the same rule in `transcheck.py` and `status`) is used as is when absolute; a relative path is looked for in the **current
  directory first, then under the repository root**; one that exists in neither place (an output to be created) is relative to the
  current directory (`translib.resolve_path`).
* The fixed-slot budget is re-derived from the **current** database (a stale shard cannot slip an overlong string in).
* The English goes to **every record whose `ja` equals the item's `ja`**.  A record that already has a different non-empty `en` is
  a *conflict* and keeps it unless `--overwrite`; an empty result never blanks a record, so coverage can only grow (the run aborts if
  it would not).
* Atomic and minimal: changed files are written to `<name>.tmp` then `os.replace`d; only the changed lines are re-serialised in the
  file's own JSON style; other files are not touched.  Files with blank lines / CRLF are refused.
* Backup: before writing, the previous version of every changed file is copied to `build/trans/backup/NNNN/` (running counter,
  with `manifest.json`).  Idempotent: merging the same results again changes nothing and makes no backup.
* Afterwards it prints coverage: records with `en`, distinct texts translated, per category (done / to do).
* Exit 0 = all merged, 1 = some items refused or BAD_ENTRY entries (the valid ones are merged), 2 = a malformed / unreadable result
  file (the valid files of the batch ARE merged and reported), the lock timed out, or usage / IO.

To undo a merge, copy the files of `build/trans/backup/NNNN/` back over `translation/`.

## 5. Status: `transmerge.py status`

```
python -I -X utf8 tools/transmerge.py status [--all] [--json] [--pending]
```
Overall records / distinct texts, per category (texts, done, skip-hinted, records with en), per source file (files with some English;
`--all` lists all), shards complete / started / untouched.  `--pending` prints the numbers of the shards that still have non-skip work
(one per line; with `--json` one JSON object per line) to drive a fleet.

Fleet loop (coordinator): `transmerge.py status --pending` → hand each shard to a translator (`transwork.py prompt N`) → on return
`transcheck.py` (the agent already ran it) → `transmerge.py merge build/trans/results/NNNN.json` → if `build/trans/rejects/NNNN.json`
exists, hand it to a repair agent (it carries `ja`, the rejected `en`, the error codes with hints and the limits) and merge the
repaired result.  Merging many result files in one call is fine.

## 6. Re-extracting without losing translations

`python -I -X utf8 tools/textdb.py extract [--only NAME ...]` now merges existing `en` / `skip` back by id (only when the `ja` is
unchanged).  Translated records whose id vanished or whose Japanese changed are **orphaned**: printed as `ORPHANED ...` and saved
under `build/trans/orphaned_en/` (first set `NAME.jsonl`, later sets `NAME.2.jsonl`, `NAME.3.jsonl` ...: an earlier orphan set is
never overwritten).  `textdb.write_jsonl` is atomic (temp file + `os.replace`).  The `textfmt_*.py --write` tools already merged,
and `textfmt_common.write_jsonl` / `merge_existing` keep the `skip` flag and any other extra key of a record.  After a re-extract run `transwork.py plan` and
`transmerge.py status`.

## 7. Building a patched disc with translations

```
python -I -X utf8 tools/build_patch.py --dry-run        # patches + summary only, seconds; read FAILED / SKIPPED lines
python -I -X utf8 tools/build_patch.py --strict         # full build -> build/out/SakaTsuku2-EN.{cue,gdi} + 5 track files; exit 2 on any failure
```
`build_patch.py` reads only `id`, `ja`, `en` of `translation/*.jsonl`: empty `en` keeps the Japanese, a record that cannot fit
(fixed slot too small, no pool room) is FAILED and stays Japanese, a stale `ja` is SKIPPED.  The merge tools already guarantee that
fixed-slot strings fit their budget and that identical Japanese has identical English (`--share dup` becomes usable).  Boot the
`.gdi` (docs/pipeline.md section 1; the emulator test plan is docs/capacity-design.md section 7).  `tools/test_pipeline.py` only
needs re-running if `build_patch.py` itself changes.  Disc-level limits (no proportional-font hook yet, texture text, `%m` money
text) are in docs/pipeline.md section 6 and docs/text-engine.md.

## 8. Self-test and known limits

`python -I -X utf8 tools/test_transwork.py [--quick]` (about 12 s): plan determinism and independence from `en`; a pass and a fail
fixture for every validator rule; merge (all ids filled, only changed lines rewritten, file style kept, atomic, backup counter,
idempotency, conflicts / `--overwrite`, empty results, refusal and repair order, stale-shard budget, dry run, all-or-nothing); status;
`textdb.preserve_en` and an end-to-end re-extract of CHALDANI.BIN; the real database (byte-identical re-serialisation of every
jsonl, plan under a minute, every distinct text in exactly one shard, a 2-item merge into a temporary copy, no player-visible text
skip-hinted, the listed pointer junk hinted).  Regression blocks for the review defects: skip hints and `trans_skip_ids.txt`,
malformed result files (top-level list, `results` null, list-typed / missing key, lone surrogate, BOM) for `transcheck` and `transmerge`,
whitespace-only `en`, BAD_ENTRY counting, the merge lock (held lock, release after failure, a waiting subprocess that must not lose
another merge's write, two concurrent merges), stale temp files, path resolution, atomic `textdb.write_jsonl`, numbered orphan
files, `textfmt_common` extra keys.  Together with `tools/test_textdb.py --quick` and `tools/test_pipeline.py`.

Limits: classification is heuristic (check `skip_report.tsv` and `plan_summary.md`); the 39-cell width rule is the default window
only (narrower windows are covered by `budget_fixed` for the fixed table cells, not for every movable label); token widths are
assumed; the checker cannot judge translation quality, glossary consistency across shards or the name / place ladders beyond the
byte budget.

## 9. Per-window line width (added with docs/window-widths.md)

Shard items carry `max_cells`, `max_rows`, `wclass` (tools/winwidth.py).  `transcheck.py` enforces `max_cells` (39 only for the
20-cell message window, 33 for a speech bubble or when bubble and message window cannot be told apart, null for browser text) and
caps `--extra-lines` at `max_rows`.  Items of an older shard file without these fields keep the 39-cell default.  After a merge, list
the texts that exceed their window with `python -I -X utf8 tools/winwidth.py violations` (`build/trans/width_violations.tsv`).

## 10. Table records (added with docs/uncovered-text.md)

After `textdb.py extract` the database holds 242,015 more records (`fmt` = `hwptr` / `recarr`: half-width pools, staff / player / municipality
record fields; all `en` empty, fixed in-place slots, `ctx` contains `stride-table(in-place only)`).  The shard plan has to be rebuilt to
include them (`transwork.py plan`: 35,898 distinct texts, 320 shards; the numbers of existing shards move, the item keys do not - plan into a
scratch directory with `--out` while shards are in flight).  4,307 of their 10,881 distinct texts already have English in older records: merge
propagation writes it to the new records of the same `ja`.  Name ladders and slot widths: docs/style-guide.md section 12.
