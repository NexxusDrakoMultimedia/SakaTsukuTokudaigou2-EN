# Half-width pointer string relocation (`--hw-relocate`)

Scope: expansion rank 4 of `docs/expansion/field-widths.md`.  The pointer-referenced half-width katakana pool strings
(`fmt: "hwptr"` records of `tools/textfmt_hwkana.py`: club-name words, nations, leagues, foreign name parts, sponsors; 112,982
records, 76 overlays, slots of 4 / 8 / 12 / 16 bytes) used to be written in place only, so an English form had to fit the 4 / 8 /
12-byte slot.  They can now be moved: the limit becomes the free space of the overlay's pool.  Status: PROVEN offline (unit tests,
read-back of every pointer in a full build), UNPROVEN in the game.  The flag is OFF by default.

## 1. Usage

```
python -I -X utf8 tools/build_patch.py --hw-relocate on  ...      # relocate what does not fit, everything else stays in place
python -I -X utf8 tools/build_patch.py --hw-relocate force ...    # test hook: relocate every string (round trip of the whole pool)
python -I -X utf8 tools/build_patch.py --hw-relocate off  ...     # default: in place only (as before)
```

With every English form short enough for its slot the build is byte-identical for `off`, `on` (digest checked: 0 bytes
different) - a string that fits is written exactly where `apply()` wrote it.  `--share dup` also lets identical relocated strings
share one copy (same unproven "strings are read-only" assumption as for the text pools).

## 2. How it works (`textfmt_hwkana.apply_relocate`)

* **Slot, budget.**  `slot` = physical bytes of the original string + NUL + zero padding up to the next non-zero byte or pointed
  offset (extracted by `textfmt_hwkana.extract`).  `max_bytes` of a relocatable record is the per-record **budget** (default 40
  bytes incl. NUL, written by `tools/re/hwr_raise_budget.py`); the real slot is then kept in the new field `slot` (right behind
  `max_bytes`).  `textfmt_hwkana.slot_of(rec)` = `rec.get('slot') or rec['max_bytes']`; the in-place writer and the flag-off build
  use it, so raising the budget never widens an in-place write.  Records without `slot` (hwpool, not raised) behave as before.
* **Relocatable** = `is_relocatable(rec)`: `fmt == hwptr`, `refs > 0`, no `hwpool` in ctx (`hwpool` = 1,092 records addressed by
  index / computed offset, e.g. the NENREP.BIN 8-byte club-name slots: they can never move and keep the in-place limit).
* **Arena (per overlay).**  The slots of all translated relocatable records of the overlay.  A string that fits its slot stays;
  the others are packed best-fit-decreasing into the free bytes (tails of the staying slots plus the whole slots of the moving
  ones; adjacent slots merge into runs).  Two plans are tried and the one with fewer failures wins (minimal movement on a tie):
  **min** (only strings that do not fit move) and **compact** (every movable string is repacked, which also reclaims the many
  small tails; this is what makes the whole pool slack usable, because a long string needs one contiguous run).
* **Pointers.**  Every aligned 32-bit word equal to `base + old` is rewritten to `base + new`; the count must equal the record's
  `refs`, else the string is refused.  Read-back: after writing, every pointer word of every moved string is resolved and compared
  (an internal error is raised on mismatch).
* **Fail, never corrupt.**  A string that finds no room FAILS and keeps its Japanese bytes (its slot leaves the arena, the pass is
  repeated until stable).  Also failing / frozen: stale `ja` (SKIPPED), English above the budget, padding not zero, overlapping
  slots, `refs` != pointer words found, a pointer word that lies inside a slot being rewritten or inside any other record (record
  arrays and ordinary text records are passed as `protect` ranges by `build_patch`: cp932 bytes such as `00 00 93 8c` read as a
  pointer word - 8 such false references exist in ENDOPT, CHALMODE, FREELOAD, NEWS_ED, SONGSAVE), and **suffix pointers**: when
  another pointer target lies inside the slot (29 records in 9 overlays, e.g. a pointer to the second half of the string) the
  string can only be written in place (as before) and its slot is not lent to other strings.
* Bytes outside the slots of translated relocatable records and outside the rewritten pointer words are never touched
  (proved per overlay over all 76 overlays by `tools/test_hwreloc.py`).
* Everything is deterministic (sorted, no hash order); the library default alignment of relocated strings is 1 byte, `build_patch` places
  them 4-byte aligned (`HW_ALIGN`, section 6).  UNKNOWN: whether any game code reads hw strings with word accesses (strings are read with
  byte copies in all code seen so far).  **Section 6 (s8gf) supersedes the statement that every pointer-referenced hwptr record may move:
  table bases are denied.**

## 3. Budget tool (documented max_bytes step)

`tools/re/hwr_raise_budget.py [--budget 40] [--dry-run] [--revert] [FILE.jsonl...]`: for every record with `fmt == hwptr`,
`refs > 0`, no `hwpool` and `max_bytes < budget` set `slot = old max_bytes`, `max_bytes = budget`.  Idempotent, atomic per file,
ids / order / all other fields unchanged; `--revert` restores `max_bytes` from `slot` and drops `slot`.  It was run on the real
database after all tests passed: **112,982 records in 76 files** (all slot-4/8/12/16/20/32 relocatable records now say 40).
A fresh `textdb extract` + `preserve_en` would reset `max_bytes` to the slot and drop `slot`; run the tool again afterwards.

## 4. What the budget means for translators

* 40 is a policy ceiling of the DB, not a promise: the real limit of an overlay is its pool slack (`build_patch` prints a
  `note: hw pool: N strings (a in place, b relocated), arena X bytes, used Y, slack Z` line per overlay with hw records when the
  flag is on) and a string that does not fit FAILS with `no room in the pool`.  Measured on the current database (every record
  translated, in-place sizes): the arena of an overlay is used to about 90 percent, the slack is 0 to 4,867 bytes per overlay
  (e.g. 610 of 5,891 bytes, 4,458 of 43,705); a few dozen 20-30 byte strings per overlay fit, hundreds do not.  Compaction
  recovers the small slot tails, so the usable amount is the printed slack, not the largest single tail.
* The game-side limits are unchanged and are NOT enforced by this tool: club names are `town short + club word` in the 14-byte
  `sname` (13 characters, `docs/expansion/field-widths.md` 2.3), person names 14 bytes.  Relocation only removes the 4 / 8 / 12-byte
  slot ceiling; the club-word and name policy (style guide, checks) must still cap the length.
* Transwork / translib treat hwptr as fixed because the ctx still says `stride-table(in-place only)`; with `slot` present the
  record is now relocatable under the flag.  The ctx text is not rewritten by this change (see docs notes).

## 5. Proof set

* `python -I -X utf8 tools/test_hwreloc.py`: synthetic pool (fit == `apply()`, long string moves, no room fails and keeps
  Japanese, only slot and pointer-table bytes change, determinism, share, align, forced identity, stale / index / refs mismatch /
  overlap / suffix pointer / protected range), forced identity round trip over all 76 real overlays (112,953 strings, 29 refused
  for suffix pointers, every pointer reads back the Japanese string, only slot / pointer bytes changed), `build_patch` with a
  scratch DB (off fails with a hint, on relocates, flag on == flag off when everything fits), the budget tool.
* `tools/re/hwr_verify.py DUMPDIR [TDB]`: independent read-back of a `--dump` build: for every hwptr record with English every
  original pointer word reads the English (or the Japanese for a refused string).  Forced real build: 114,155 pointers read English
  through a moved pointer, 14 kept Japanese, 0 BAD; default build: 0 BAD.
* Trial builds (`--share dup --append-safe --proportional-font on --repack on`): default and `--hw-relocate on` both 0 failed, 0
  skipped, patch digest identical to each other and (before the DB was raised) to the digest of the tree before this change.

## 6. The table-base bug and the guard (stage s8gf, 2026-11-13)

**Symptom (prop10c playtests).**  Event screen with an empty message window, then wrong scout data (salary `35 oku 8500m`, no Age, a garbage
picture box, foreign-only candidates, a freeze mid message).  The disc built with `--refit off --hw-relocate off` (`s8g_norefit`) plays
the same screens correctly: the relocation was the cause.

**Cause.**  `--refit on` forces `--hw-relocate on`.  `apply_relocate` treated every pointer-referenced hwptr record as a string.  Some of
them are not strings but the FIRST ELEMENT OF A TABLE whose base the code addresses with `base + idx * stride`: `Damui` is record 0 of the
56 byte player table of SCDRF.BIN at 0x37df0 (11 literal sites, e.g. `mov #56,rX; muls.w; add`), `Nuchitos` is a byte table (about 38
overlays), `O. Kawamoto` a 30 byte record array, `Credit Svc` / `Dream Mach.` / `World Telco` / `Inter Jewel` company arrays (`@(r0,Rn)`
accesses).  prop10c moved them (and the `compact` plan then wrote OTHER strings into the freed table bytes: the real slot began
`Purple Sanga`).  The extraction cannot tell the cases apart: the ctx `stride-table(in-place only)` is on ALL 112,982 hwptr records, so it is
not a discriminator (only `hwpool` was ever honoured, and the head rule `hw_array_heads` sat behind the env variable `S8FT_HEADFIX`).
The new strings were also placed at 1-byte alignment (bases landed on odd addresses).

**Fix (three layers, all fail safe: a string that cannot be shown to be a text pointer stays where it is).**

1. `tools/hwguard.py` classifies every pointer word ("site") of a record from the ORIGINAL overlay bytes: `ptrtab` (a table of string
   pointers: neighbouring in-image pointer, indexed by 4), `lit` (the literal of a `mov.l @(d,pc),Rn`; the use of Rn is followed: index
   arithmetic `add` / `mul` / `@(r0,Rn)` / `@(d,Rn)` / shifts = BASE; only passed to `jsr` in r4..r7 = text; stored / read bytewise = unknown),
   `litx` (an index use outside the recognised code windows is still believed), `field` (a lone pointer field of a record: unknown).  A record
   is TEXT only when all sites are `ptrtab` or call-only literals.  Also BASE: the head of a record array (Rule A / B, now always on; Rule A ignores entries of a pointer table `tbl@`: s8gkc found BACKUP's club words
   `Panthera` / `Mythos` denied by a spurious recarray 240 bytes behind them).
2. `translation/hw_inplace.tsv` (id, class, reason) is the data-driven denylist, generated by `tools/re/s8gf_scan.py --deny`:
   417 records in 71 overlays (85 base, 63 head, 269 unknown; 112,563 records are text, 112,562 of them plain pointer tables).
   `textfmt_hwkana.is_relocatable` honours it (so do `refit.hard_cap` / `check_hard`: a refit form that would need relocation of a denied record
   is skipped), lines of class `manual` survive a regeneration.  `build/s8gf_classify.tsv` is the per-record evidence (id, overlay, old
   address, sites, use tags, class, English, slot, reason).
3. `apply_relocate(guard=True)` (what `build_patch` passes) re-checks the sites of every relocatable record in the image at build time with
   layer 1, so a record that is missing from the file is still refused.  Records that cannot move (denied, `hwpool`, refused) are written
   in place and their slot is NEVER lent to other strings (they may be fields of a record).  A refit form that cannot be written for such a
   reason goes back to the in-place short form of the DB (`build_patch.hw_relocate_fit`, step 1 below).

**Alignment and room.**  `build_patch.HW_ALIGN = 4`: every relocated string starts 4-byte aligned.  Why 4 (s8gkc, `build/s8gkc_align.py`): 112,966 of the
112,982 original pointer-referenced half-width strings start 4-byte aligned (15 at 2 mod 4, 1 odd), whereas ordinary text strings sit at every
alignment (12 percent odd), so the half-width readers may use word accesses; the prop10c playtests at 1 byte only prove the screens seen.  A string takes `ceil((len+1)/4)` words, so
the small pools (55 / 85 club words, J.League names, nations, cities) and the 5,600 string name pools have not room for all 38,386 refit
forms.  `hw_relocate_fit` gives forms back, in this order: (1) a form that cannot be written for a reason of its own; (2) on `no room`: the
forms of the lowest classes first (`REFIT_DROP_ORDER` person, other, sponsor, town, city, nation, jclub; longest first; the smallest prefix
that fits, by bisection); the nine club words are never given up for alignment; (3) when even that is not enough the overlay is placed at
alignment 2, then 1 (only `FLOW_PRG/HOMETOWN.BIN` needs 2).  Result in `prop10d`: 23,792 of 38,386 refit forms are back at the in-place short
form (person 20,458, city 2,200, nation 993, jclub 124, other 17); all club words print in full.  The cost of alignment 2 would be 3,424
forms, of alignment 1 none (measured with `build/s8gf_measure.py`): changing `HW_ALIGN` is a one-line decision.  `HW_COMPACT = True` keeps
the repacking plan (the min plan alone finds no contiguous run and would give up every club word).

**Fail safe.**  `apply_relocate(guard=True)` calls `hwguard.require_deny()`: a missing or empty `translation/hw_inplace.tsv` stops the build (it used to
read as an empty list and silently lift every head / unknown / manual denial).  Reviewed on prop10d disc bytes by s8gkc (`build/s8gkc_*.py`): of the
112,469 relocated strings only 2 are loaded by code at all (`Carlos` GAME, `Blaze` ENDOPT: both passed on to a call) plus the position names
`Goalkeeper` / `Defender` / `Midfielder` (EVENT 0x1b6c, pushed as a stack argument); all others are words of pointer tables, 151 of 471 tables
have a code reader whose element pointer is only passed on / read bytewise, the other 320 are reached by no literal (index or another table).

**Checks.**  `tools/test_hwguard.py` (synthetic code and tables, the guard in `apply_relocate`, denylist format and effect, every list line names
an existing record, the known Damui / Nuchitos bases are on it, no club-word table record is, the list equals the scan, real overlays:
no relocated string is denied or non-text and all start 4-byte aligned).  `build/s8gf_probe.py` proves it on the built disc bytes (`docs/pipeline.md` 9.4).  Residual risk: the use analysis is a heuristic over straight-line code (36 instructions); a base literal whose
indexing happens later and far from the load would look like text if its pointer word also has a neighbouring pointer.  Not seen on screen.
