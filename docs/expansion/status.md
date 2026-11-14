# Expansion studies: what is done, what is open (status after stage 3, 2026-11-11)

The five studies in this folder were written as read-only feasibility studies before the stage-2 and stage-3 work.  This page says, for each recommendation they made, whether it has been
built, how far it is proven, and what is still open.  Status words: **DONE** = implemented, default or documented flag, tested offline; **DONE, UNPROVEN** = implemented and simulator /
read-back proven, never seen in the game; **OPT-IN** = implemented, default off; **NOT DONE**.  Nothing in the table has been booted in Flycast since the stage-3 trial discs
(`prop6`, `prop6r`) were built; the list of what to look at is `docs/playtest-checklist.md`.

## 1. Table

| Study | Recommendation | Status | Where / flag | What is left |
|---|---|---|---|---|
| disc-layout | geometry model and verifier (`verify_disc`) | DONE | `tools/discbuild_geom.py`, `tools/verify_disc.py`, `--verify-disc` | writer geometry still fixed; V11 / V12 (layout.json, pin list) not done |
| disc-layout | capacity guard (disc may not pass LBA 549150) | DONE | `build_patch` stops with `ERROR: disc full`; `--allow-overflow` restores the old behaviour | overflow images are emulator-only; Flycast / GDEMU behaviour past 549150 untested |
| disc-layout | duplicate files share one extent | OPT-IN, UNPROVEN | `--dedupe-files on` (15 groups, 3726 sectors) | game-side acceptance of shared extents: boot items 2 and 5 of that study s11 |
| disc-layout | add file / directory, no 64-byte directory limit | DONE | `--add-file /ISO/PATH=LOCAL` | the game's own directory cache sizes (`docs/expansion/overlay-memory.md` item 8) are not patched |
| disc-layout | ISO-only patch with a move-aware encoder, player-side raw rebuild | DONE | `tools/vcdiff.py`, `tools/release.py`, `tools/apply_patch.py` (`docs/xdelta-release.md`) | real GDI / dumps from other dumpers untested |
| disc-layout | stub the Dream Passport tree, shrink track 4 | NOT DONE | content decisions | not needed while the disc fits (6431 free sectors, 10157 with dedupe) |
| overlay-memory | append text to a no-BSS overlay | DONE, UNPROVEN | `--append-safe` (33 overlays) | loader and allocator acceptance of the raised `_end` word (T4) |
| overlay-memory | grow an overlay that has BSS (pad to the old `_end`, raise `_end`) | OPT-IN, UNPROVEN | `--grow-overlays N` (default 0, `docs/pipeline.md` 9.5) | real free memory when each overlay runs (T4 / T5), slot-count state |
| overlay-memory | raise slot counts (`desc[1]`), stub patch for GAME, on-demand pack file, directory-cache count | NOT DONE | | needs the free-slot trace and the directory-cache overflow test (items 3, 4, 6) |
| overlay-memory | 1ST_READ growth | NOT DONE (not useful) | only its tail caves are used (font 0x8c299800, money 0x8c299a00, registry in `tools/patchengine.py`) | |
| field-widths | rank 1: full municipality names in the 126-byte records | DONE, UNPROVEN | `tools/re/hnm/hnm_apply_names.py`, `translation/FLOW_PRG__HOMETOWN.BIN.jsonl` | seeing the list in game |
| field-widths | rank 2: `%s%s` -> `%s %s` in club and hometown messages | DONE | `tools/layoutpatch.py` item 3, translation records | |
| field-widths | rank 3: no 2-byte cut of the short names, plus a club-name guard | DONE, UNPROVEN | `layoutpatch` (chop patches, `--club-guard on`, `--club-dot on`); 142,670 simulator runs, 0 problems (`docs/layout-issues.md` 9.5, 9.8) | real size of the destination buffers, neighbour field intact (9.7); the 916 odd cut results (`N. . Topolino`) are FIXED on the text side, 0 odd shapes in prop7 / prop7r (`docs/layout-issues.md` 9.9) |
| field-widths | rank 4: relocate half-width pool strings | OPT-IN, UNPROVEN | `--hw-relocate on|force`, forced on by `--refit on` (`docs/hw-relocation.md`) | any screen that uses a moved string, in game |
| field-widths | refit forms (better short forms made possible by 4) | OPT-IN, UNPROVEN | `--refit on`, `translation/refit/` (75 overlay files), trial disc `prop6r` | prop6 vs prop6r comparison (`docs/playtest-checklist.md` s8) |
| field-widths | rank 5: side buffer for club and user name; rank 6: staff-name bank; rank 7: player-name bank | NOT DONE | design in `docs/expansion/save-format.md` s6 | needs the name accessor patch; see the save findings below |
| field-widths | rank 8: widen the 288 / 92-byte player records | NOT DONE, not recommended | | breaks saves |
| field-widths | V7: does the save hold name strings? | ANSWERED | `docs/expansion/save-format.md` s1 | yes for the user and club name and ~48 runtime player structs; no for the other ~5,270 players |
| patch-toolkit | one declarative patch engine (registry, overlap check, families, hook builder) | DONE (parts 1, 3, 4) | `tools/patchengine.py`, `docs/patch-engine.md` | the assembler / Lua-poke exporter parts of the design |
| patch-toolkit | #1 proportional font on after one live test | DONE | `--proportional-font on` is the standard flag; played in Flycast up to `trial_prop3` | prop6 / prop6r not booted |
| patch-toolkit | #2 pixel-aware validator and reflow | DONE | `tools/pixelwidth.py`, `tools/winwidth.py`, `translib._fmt_cells` (`%m` = 15 cells) | |
| patch-toolkit | #3 scale the advance by A/24 | OPT-IN, UNPROVEN | `--prop-scale on` (`docs/patch-engine.md` s4); 144-byte cave | the live test (`docs/playtest-checklist.md` s9) |
| patch-toolkit | #4 size class 2 for long prose, #5 condensed glyph art, #7 escape-token names, #8 raise W, #9 replace the layout function | NOT DONE | | each needs an emulator experiment first (study s9 items 2, 3) |
| save-format | read-only reverse engineering of the save | DONE (findings only) | `docs/expansion/save-format.md`, `tools/re/svfmt_*` | CSAVE / CSAVE3 / SONGSAVE not decompiled; the 12-character cut mechanism is still unknown |

## 2. Save format findings that matter to the patch (details: `save-format.md`)

* The main save (types G and A) is a raw 64 KiB RAM arena behind a 0x180-byte header; it stores the 14-byte user and club names and the names inside ~48 runtime player structs.  Names of the
  other players are not stored, so a display-time name substitution does not change a serialised struct.
* Because the stored name fields stay 14 bytes, the project **does not widen any record**: long English names are handled by the club-name guard, the 12 / 13 character limits of the style guide and
  (not built) a name bank.  The patch changes no serialised struct, so a Japanese-disc save should still load on the patched disc (its stored names stay Japanese); this has not been tested.
* Files on the VMU are `SAKATOK2.<G|A|P|C|D|L|E>NN`; the file CRC is the Sega library's, the in-RAM section CRC is CRC-16/X-25.  Nothing in the patch writes a save.
* Untested: loading a Japanese-disc save on the patched disc, and a save made on the patched disc loaded on the Japanese disc.

## 3. Why the open items stay open

Every NOT DONE row either needs an emulator experiment (the studies name it: T4 / T5 of overlay-memory, the live tests of patch-toolkit s9) or is a content decision for the project owner (stubbing the
Dream Passport tree, shrinking track 4).  Nothing here blocks a release: the standard build fits the disc, and no step depends on a row that is not DONE.
