# Proportional font: skeptic review outcomes

Two skeptics re-derived the patch (hook bytes, registers, cave, table, addresses). Hook encodings, register safety,
wrap equivalence for A = 24 and the cave/table location (0x8c299800-0x8c2999ff, zero in all five RAM dumps) were
reproduced. Typography: proportional strips read clearly better than fixed 12 px; paper texels are transparent.

## Fixed after review
- D1 (space width): `SPACE_ADV` was 6, so pad spaces in numeric fields (`%2d`, `%4d`, ...) shrank by 6 px and
  columns misaligned. Now 12, table[0x00] = table[0x20] = 12 (`tools/fontpatch.py`). `tools/test_pipeline.py` updated
  (135 checks pass). Cost: English word gaps stay at the original width.
- fonttest.lua `fixed` mode: was `[6]+[12]*255` (not a control); now all 12 so it is identical to the unpatched game.
- fonttest.lua `restore`: only rewrites a range if RAM still holds exactly what the script wrote; ranges whose overlay
  has changed are skipped and logged (previously it could overwrite another overlay's code).

## Still open (needs the emulator, nothing proven in game)
- D2: centring / right-align by character count, cursor positions, name entry: each screen needs a live check.
- D3: windows with advance != 24 (32, 16, 10, 48) keep fixed 12-px-style steps; the cave does not scale yet.
- D4: odd advance values (A = 1 or 5) wrap by pixels instead of units (probably never carries text).
- Uncovered drawers: linear-text users (DMCLBEDT, ENDING, GAME), GAME.BIN's own engine at 0x8c3202b0,
  OFFICE/WEEKLY/BPMWEEK/FACEMDUL/TITLE/LOGO.
- Whether `flycast.memory.write8` invalidates the dynarec, whether fonttest.lua loads (no Lua interpreter here to
  syntax-check: it uses Lua 5.3 bitwise operators), hook writes while the PC is inside the hooked span.
- 23 of 205 sampled labels/names/places are wider than at fixed 12 px (13 px glyphs): only matters where a column is
  sized per character.
