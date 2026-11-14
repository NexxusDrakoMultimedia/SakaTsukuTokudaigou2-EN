# Roadmap

Where the English patch for Sakatsuku Tokudaigou 2 (Dreamcast, HDR-0183) goes after 0.1.0-beta.1.  This is a plan, not a promise: **no dates are given**, and an item moves only when it has been built and tested.  Each item says what is implemented, what is only designed, and what is untested.  Facts come from the maintainers' investigation notes in `docs/`; where nothing was checked, the text says "untested" or "not yet investigated".

## 1. Principles

1. **Stylistic choices are OPTIONAL and off by default.**  Honorifics, Japanese name order and western money style are matters of taste.  Each ships as a separate, small optional patch (a "layer") applied on top of the base patch.  None is part of the default result.
2. **Efficiency and proper use of space are always pursued, in the base patch.**  Relocating strings into spare room, scaling letter spacing to the text window, and making fields hold more are pure improvements: same words, same style, more room.  They are not layers.  They stay out of the base only while they are unproven.
3. **Japanese flavour is the default.**  The base keeps quirks such as `13 oku 1500 man` and the oku/man units rather than localising them.  A player who wants something else turns it on.
4. **Version numbers** follow `docs/RELEASING.md` section 1.  A new optional feature that is off by default is a MINOR bump (0.2.0), even if the default output is unchanged.  Anything else that changes the patch bytes (corrections, rebuilt art) is a PATCH bump.  Pre-releases use `-beta.N` and `-rc.N`.
5. **What OPTIONAL means for a player.**  You never need a layer.  The base patch is a complete, recommended translation of the whole game.  If you apply nothing extra, you get exactly the default.  Layers are for people who prefer another style, and every layer will be described as optional in the README, the release notes and `apply_patch.py --list-options`.

## 2. Plan for 0.1.0 (the regular release)

0.1.0-beta.1 is released (tag `v0.1.0-beta.1`).  The next steps are beta.2, then rc.1, then 0.1.0.

### 2.1 Testing breadth

All testing so far was in the Flycast emulator.  Still to do:

- Another emulator (not yet investigated which).
- Real Dreamcast hardware, if volunteers with a GD-ROM or a burned disc come forward.  Untested at present.  Half-width string relocation keeps strings 4-byte aligned, which should protect against alignment faults on the SH-4, but this was never seen on hardware.
- Compare the source-disc hashes with the Redump database (CHANGELOG known issue: they were taken from the dump used here and not compared).
- A full-season playthrough on the release flags: matches, training, news, save and load, ending.  The test sheets so far cover the Event, scout, club-word and hometown screens, not a long run.
- Work through the playtest sheet (`docs/playtest-checklist.md`) and record results in `docs/playtest-log.md`.

### 2.2 Known-issues triage

Copied from `CHANGELOG.md`, grouped.  Each is to be fixed, accepted or moved to a later version.

**Visible on screen**

- In-match team-instruction label (HOME / AWAY): the repaint is incomplete and a remnant of the old picture (`efend`) can show.
- Name tags: the tag icon can overlap the name.
- In-match player tags show initials only.
- Player List: the `Age 31` field pokes past its panel.
- Ordinals on the in-match rank tag read `1th`, `2th`, `3th`.
- About 5 % of commentary lines are longer than their clip and are cut off when the clip ends.  This is a timing problem, not a space problem, so string relocation does not help.
- Commentary subtitles draw 13 px glyphs in a 12 px cell (clamped to 12).

**Cosmetic**

- Practice screen, left strip: three labels overshoot by 1 to 3 px.
- The indentation of the `Screen Saver` label is off.
- The standalone OPTION screen still reads `Commentary Text` (the in-match options say `Subtitles`).

**Decisions**

- `Grampus` versus `Grampus Eight` for Nagoya Grampus Eight.
- Some staff-name readings in the credits are best guesses (`docs/credits-names.tsv`: one low confidence, 29 medium).
- Two people with the same romanised name may look identical.

**Refit caps (space limits)**

- Three refit forms are longer than their field and fall back to the short form: `FLOW_PRG/CHALMODE.BIN#3d804` (`Domasnes`, 9 bytes, cap 8), `FLOW_PRG/EVENT.BIN#e06a8` (`Purple Sanga`, 13 bytes, cap 12), `FLOW_PRG/NEWCON.BIN#2e11c` (`Slovenia`, 9 bytes, cap 8).  These sit in table bases that the relocation guard deliberately never moves (they are on `translation/hw_inplace.tsv`), so relocation cannot help.  Fixing them needs code work (patching the table indexing) and is not yet investigated beyond that.  A text fallback (`Domsnes`) already ships.
- Many composed club names show an abbreviated town because of the 13-character field.  Relocation moves the individual club words, not the composed field.  A second short town form would be a text change; not done.
- About 23,800 of the 38,386 refit forms in the database (the changelog's 38,390 counts the forms of the standard build) fall back to the short in-place form in the standard build because of the 4-byte alignment rule and the guard's denylist.  Nine long club words do print in full.

### 2.3 Release hygiene

- VQ textures: 236 of 637 ship as-is with a re-quantised codebook.  Redrawing them as raw textures (`docs/texture-delta.md` section 6, option b) is to be looked at before the non-beta release.
- Run the REUSE lint and fix what it reports.
- Merge `doc/` and `docs/` into one folder.
- Update `docs/hw-relocation.md` and the playtest checklist section 7: both still call half-width relocation off and unproven, although the standard build turns it on through `--refit on` and it was played on prop10e to prop10j.  Counts in that document are also out of date (it says 76 overlays; the current test reports 70).  Add one line to Known issues about the alignment rule.
- Finish the playtest sheet so testers have one place to report.

### 2.4 Exit criteria

- 0.1.0-beta.2 gathers fixes from testing.
- 0.1.0-rc.1 is cut when the full-season playthrough and the extra-emulator check turn up nothing new.
- After rc.1 only blockers change.  If one does, another rc is cut.
- 0.1.0 is the same bytes as the last rc, with the version and changelog updated.

## 3. Plan for the 0.2.0 betas

0.2.0 adds the optional layers.  The default result for the same translation is to stay byte-identical to 0.1.0, or the release notes say why not.

### 3.1 The optional-layer design

**Status: designed only.**  No layer mechanism exists yet in `tools/release.py` or `tools/apply_patch.py`, and nothing has been built or measured.

- **Base plus small variant patches.**  The base patch is built exactly as today.  Each layer is a VCDIFF delta from the base-patched disc to the base plus that option.
- **Source-hash checking.**  A layer must refuse the wrong base.  Because the whole-file hash changes when a layer is added, the check is made on the byte ranges the layer touches (hash before and after), and the whole-file result hash is checked for every combination that the release lists.
- **Tested order of application.**  The manifest records one fixed order.  `apply_patch.py` applies layers in that order only.
- **`apply_patch.py` flags (planned):** `--with NAME` (repeatable; default none), `--list-options` (prints each option, marked "OPTIONAL, off by default", with a summary), and `--verify` naming the combination it recognises.
- **Combination testing.**  For three options that is 8 discs (base, each alone, each pair, all three).  Every combination is built directly from flags and compared with "base plus layers"; they must be byte-equal.  Beyond four options the plan is each single, pairs and all-on.
- **Overlap is the main risk.**  Text edits can ripple through repacked string pools, and a raw disc sector has one checksum, so two layers touching the same sector conflict.  If a combination does not compose, an exact delta for that combination ships instead.  Real layer sizes are unmeasured; measuring them is the first task.
- **Manual xdelta users** can apply a single layer or a shipped exact combination to the base result, not several layers in turn.  The README will say so.
- **Save data:** no save data is on the disc, and the layers are expected not to alter save format, but toggling a layer on an existing save is untested.  Name fields (14 bytes) may be stored in saves; unknown.

### 3.2 The optional layers

All three are OPTIONAL and off by default.

**Honorifics** (`-san`, `-kun`, `-sama`, `-senshu`).  Not implemented.  No build flag exists, and the translation records have no per-style alternative field yet.  Needs a way to carry variants per record, a width check of name fields, and layer measurement.  Placement: 0.2.0.

**Japanese name order** (Family name, then Given name).  Not implemented, same state as honorifics.  The 12 identical MEETING records (`1000 man bonus ... #tk00#`) contain a name token and would collide with any layer editing the same record (name order and honorifics both touch that token, and western money edits the amount in the same text).  Placement: 0.2.0.

**Western money style** (full yen with thousands separators, for example `Y1,315,000,000` instead of `1 oku 3150 man`).

- **Implemented, but not usable.**  A `--money-style western` build flag exists, covering only the main money routine and the TV station card.  It is **not** compatible with the current text database: the library and numeric wrappers are switched off for western, so the finance screens, income rows, abroad/fire/name-set screens and the INVEST screen would print garbled amounts.  It must not be offered to players.  Never built or run with the release flags.
- **What a proper version needs** (designed, not written): wrappers that work with either style, a single "compact" convention for tight fields, stable entry points so a style swap touches only the disc's code tail, the TV card and about 34 text records, and a new tail routine (estimated at 420 to 480 bytes of 512; an estimate only).  Amounts stored in units of 10,000 yen need only four zeros appended, so the conversion is exact.
- **Tight fields** (12-byte scout panel, 12-character slots, the 18-character INVEST field, the TV plate) need an abbreviated form such as `Y1.315bn`.  Widths were measured on paper only; nothing was seen on screen.
- **Art limit:** about 35 textures show oku, man or Yen as sprites, and the header bar composes numbers from sprites whose drawing code was never found.  Those screens cannot be regrouped into yen.  They could be relabelled or left in oku/man as a documented exception.  This is an open question, and it means the layer will never be fully consistent unless that code is found.
- **Crowd line** (`1man 827ppl`) is a separate function, not the money routine.  A western `18,270 ppl` would need that function rewritten; designed, not simulated.
- **Open questions:** which western form is primary (`Y` prefix, ` yen` suffix, abbreviated, or stored man with grouping), whether income rows show exact yen, and whether the crowd line belongs in this layer.
- Placement: 0.2.0 betas, after the base work below.  Because it is the cheapest and most independent layer, it may be the first one used to prove the layer pipeline.

### 3.3 Efficiency and space work that belongs in the base

These are not layers.

**Half-width pointer relocation (`--hw-relocate`).**  Implemented and already in 0.1.0-beta.1: the standard flags include `--refit on`, which forces it on.  Played in Flycast on prop10e to prop10j; the offline tests (`tools/test_hwguard.py`, `tools/test_hwreloc.py`) pass.  A guard with a 417-record denylist stops table bases from moving (an earlier unguarded version broke the Event and scout screens).  Open: real hardware, a full-season run, and whether 2-byte alignment (which would win back 3,424 forms) is safe.  The three over-cap forms and 13-character club names are out of its reach.  Placement: stays in 0.1.0; alignment 2 and guard improvements are 0.2.0 or later, behind a boot test and a scan for word-sized reads.

**Proportional scaling of other windows (`--prop-scale`).**  Implemented and proven only in the SH-4 simulator at routine level.  Never booted, off in the standard build.  It makes windows other than the 24 px class use the proportional width table scaled to their size, giving more characters per line (estimated, not measured: about 70 glyphs per message line against 59).  Not a style choice, so it belongs in the base once proven.  Not ready as written: it also touches two window classes (EVENT and WEEKLY) next to an unresolved Event-screen hang seen on an early build.  Plan: narrow it so those stay unchanged, add a test against the real overlay, boot one trial disc, play the checklist screens, and promote only if nothing regresses.  The narrower `--small-prop` (option and training windows) is already in the release, itself not yet seen in a long play.  Placement: 0.1.0 only if it passes before rc.1, otherwise 0.2.0.

**Money and number fixes that are not style.**  The annual report (NENREP) is not covered by the money formatter (`docs/number-formats.md` marks it open), so positive amounts there may still print Japanese kanji and the red form reads `Y%s/%s`.  **The 0.1.0-beta.1 changelog overstates this** by listing the annual report among the screens that show oku and man; it is to be corrected in beta.2 and listed under Known issues.  NENREP coverage is a base fix (it is a gap, not a taste choice).  The crowd line uses `man` for people while the population graph header says `10k`: this is a consistency decision, and if it turns out to be a matter of taste it becomes optional (with the western crowd line) instead of a base change.  Neither has been looked at beyond the investigation.  Placement: 0.1.0 or 0.2.0 depending on triage.

**Money wrapper refactor (prerequisite of the western money layer).**  Make the library and numeric money wrappers style-agnostic, define one "compact" convention for tight fields, keep stable entry points for the money routine across styles, and guarantee a maximum text length for the scout panel.  This changes no default output, so it is an efficiency/robustness change that belongs in the base, not in the layer.  Not started.  Placement: 0.2.0, before the western money layer.

## 4. Work items

| Item | Kind | Target | Status | Depends on |
|---|---|---|---|---|
| Other-emulator test | base | 0.1.0 | not started | a tester |
| Real-hardware test | base | 0.1.0 if volunteers, else later | untested | a tester with hardware |
| Redump hash comparison | base | 0.1.0 | not done | a Redump entry or dump |
| Full-season playthrough | base | 0.1.0 | not done | final flags |
| Known-issues triage | base | 0.1.0 | list copied, not triaged | testing |
| VQ texture decision (redraw as raw) | base | before 0.1.0 | shipped as-is in beta | texture-delta doc |
| REUSE lint, `doc/` and `docs/` merge, playtest sheet | base | 0.1.0 | not done | none |
| hw-relocation docs update | base (docs) | 0.1.0 | not done | none |
| Half-width relocation | base | 0.1.0 | implemented, played in Flycast | already in release |
| Alignment 2 for relocation | base | 0.2.0 | measured offline, untested | boot test, word-read scan |
| Three over-cap refit forms | base | later | not designed beyond code route | table-base patching |
| Second short town form for club names | base | later | not done | text work |
| Commentary clip timing | base | later | known, not investigated further | timing work |
| `--prop-scale` (narrowed) | base | 0.1.0 or 0.2.0 | implemented in simulator only | trial disc, overlay test |
| NENREP money coverage | base | 0.1.0 or 0.2.0 | identified, not fixed | none |
| Crowd-line unit (`man` versus `10k`) | base, or optional if taste | 0.2.0 | open decision | none |
| Money wrapper refactor (style-agnostic wrappers, stable entry points) | base | 0.2.0 | not started | none |
| Correct the changelog's annual-report line, add it to Known issues | base (docs) | 0.1.0-beta.2 | not done | none |
| Layer mechanism in `release.py` and `apply_patch.py` | tooling | 0.2.0 | designed, not built | layer-size measurement |
| Layer-size measurement | tooling | 0.2.0 | not done | a build per option |
| Per-record variant field in `l10n` | tooling | 0.2.0 | not designed in detail | layer design |
| Honorifics layer | optional layer | 0.2.0 | not implemented | layer mechanism, variant field |
| Japanese name-order layer | optional layer | 0.2.0 | not implemented | same |
| Western money layer | optional layer | 0.2.0 betas | half-built flag, unusable now | money wrapper refactor, art decision |
| Western crowd line | optional layer | with western money, or later | designed only | western money |

## 5. How to help

- **Test.**  Apply the patch to your own dump and play.  Tell us the patch version, the dump form (BIN/CUE, GDI or ISO), the emulator or hardware, and what you saw.  Full seasons and unusual screens are the most useful, because they are what has had the least testing.  Hardware reports are especially welcome.
- **Report.**  Open an issue at https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN/issues with a screenshot when you can, or talk to us in the Community Discord: https://discord.gg/7DNrGye9TZ .
- **Translate and review.**  Read `doc/TRANSLATORS_NOTES.md` and `docs/style-guide.md`.  Style questions (honorifics, name order, money) are decided as optional layers, not as arguments about the default.
- **Credit.**  The patch is by Nexxus Drako, with thanks to the Community Discord.  Please keep that credit when you share or build on it.  The licences are in `README.md` and `REUSE.toml`.
