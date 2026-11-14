# Texture deltas: shipping the repainted textures without shipping Sega's pixels (tools/texdelta.py)

The public repository holds English and identifiers only. A repainted texture (translation/textures/**/*.pvr, the working
form every tool reads) is a whole PVR image whose pixels are mostly Sega's, so it is NOT committed. What is committed is
`l10n/textures/<same relative path>.vcdiff`, a VCDIFF delta of the repaint against the ORIGINAL texture, plus one manifest.
The player's own disc supplies the original; the delta supplies only what we changed.

Self-test: `python -I -X utf8 tools/test_texdelta.py` (81 checks, ~6 s; `--full` also round-trips all repaints, ~40 s).
Sections 3 to 5 and 8 were measured on the tree of 2026-11-12 (237 repainted textures); the delivered set of 0.1.0-beta.1 is all 637 repainted textures (section 10).
Decision (owner, 2026-11-15): textures ship as deltas only ("Deltas, VQ as-is"); `translation/textures/` is git-ignored, `l10n/textures/` is committed.

## 1. Commands

```
python -I -X utf8 tools/texdelta.py make      [--textures-dir translation/textures] [--extracted extracted] [--out l10n/textures] [--plain]
python -I -X utf8 tools/texdelta.py apply-all [--delta-dir l10n/textures] [--extracted extracted] --out <dir>
python -I -X utf8 tools/texdelta.py apply     DELTA.vcdiff ORIGINAL.pvr OUT.pvr
python -I -X utf8 tools/texdelta.py verify    [--work build/l10n_tex]        # make + apply_all + byte compare, writes only below --work
python -I -X utf8 tools/texdelta.py stats     [--delta-dir l10n/textures]
python -I -X utf8 tools/texdelta.py analyze   [--delta-dir l10n/textures]    # original-equal bytes inside the deltas (section 5)
```

* `make` (maintainer, needs the working .pvr files): for every `<iso path>/<texture id>.pvr` it finds the original texture in
  `extracted/` with the same locator the injector uses (tools/texinject.py: `load_textures_dir` rule for the container,
  `extract_pvr` for the texture; a TBD record gets its synthesised GBIX + PVRT header, exactly as the injector expects), encodes
  the delta, decodes it again and refuses to write anything that does not reproduce the repaint. Output: one
  `.vcdiff` per texture below `l10n/textures/` (same relative path, `.pvr` replaced by `.vcdiff`) and `MANIFEST.tsv`.
* `apply-all` (player or maintainer): rebuild every .pvr working file from the deltas and the extracted disc. Every texture that
  fails is printed as `MISMATCH <path>: <reason>` and the exit code is 1; nothing is skipped silently and the textures that are
  fine are still written.
* `tools/build_patch.py --textures-delta l10n/textures` does the `apply-all` into a temporary directory under build/ (removed at
  exit) and uses it as `--textures-dir`. Default off (the flag is absent: nothing changes); it excludes `--textures-dir`; any
  problem stops the build with exit 1 and names the texture.

## 2. File format

`l10n/textures/<iso path>/<texture id>.vcdiff` mirrors translation/textures one to one. Example:
`ETC_DATA/SHTEX8.ZAR/yesno.tbd#1.pvr` -> `l10n/textures/ETC_DATA/SHTEX8.ZAR/yesno.tbd#1.vcdiff`.

Each file is a standard VCDIFF (RFC 3284) with ONE window:

* source segment = the whole ORIGINAL texture as a PVR file (the original's bytes: `GBIX` + `PVRT` + payload, 16 + payload bytes
  with a 16 byte header for TBD records), target = the whole repainted PVR file;
* default code table, VCD_SELF addressing, no checksum, no application header;
* instructions: `COPY` (address in the original + length) for every stretch that equals the original (same offset, any length >= 6;
  other offset, length >= 10), `RUN` for a byte repeated 32+ times, `ADD` (literal bytes) for the rest;
* the ADD / instruction / address sections are xz-compressed as xdelta3's `-S lzma` does it (header flag VCD_DECOMPRESS, secondary
  id 2, stream cut before the xz index so it is a flushed stream like xdelta3 writes). `make --plain` writes uncompressed
  deltas (3x larger; any RFC 3284 decoder reads them). Both flavours are applied successfully by xdelta3 (checked by the test and
  by `tools/re/tdl_size.py`), so a player can also use `xdelta3 -d -s original.pvr x.vcdiff out.pvr` by hand.

`MANIFEST.tsv` (UTF-8, LF, `#` lines are comments), tab separated, one line per texture, sorted:

| column | content |
|---|---|
| path | the working file below translation/textures/ (`ETC_DATA/SHTEX8.ZAR/yesno.tbd#1.pvr`); the delta is the same path with `.vcdiff` |
| repaint sha256 | SHA-256 of the repainted PVR (the file `apply` must reproduce byte for byte) |
| original sha256 | SHA-256 of the ORIGINAL texture bytes as `texinject.extract_pvr` gives them: proves the player's disc holds the same texture (other revisions or a damaged dump differ here) |
| delta bytes | size of the .vcdiff file |

`apply` order of checks: original sha256 (message: "original texture differs from the one the patch was made for (other disc
revision or damaged dump)"), delta decoding (a source that is too short is reported as such), repaint sha256 ("result differs
from the shipped repaint"). The disc itself is verified earlier by tools/verify_source_disc.py (Redump hashes in tools/release.toml);
the per-texture original hash is the second line of defence and the one that names the texture.

## 3. Numbers (237 textures)

| | |
|---|---|
| deltas | 237 files, 1,760,953 bytes in total (4,701,367 with `--plain`) |
| per file | smallest 269 bytes, median 4,225, largest 71,100 (TRAINING/TRAINING.TBD#4, 512x512) |
| size classes | 138 deltas under 5 kB, 55 over 10 kB, 21 over 20 kB |
| the repaints themselves | 237 PVR files, 34.6 MB of payload (4,554,752 B fmt 0 dt 1; 24,616,960 B fmt 2 dt 1; ...): the deltas are 5.1 % of that |

The "a few kB" expectation holds for the typical texture (median 4 kB) and not for the big full-sheet repaints
(512x512 ARGB4444 menu sheets and the VQ textures, 20 to 71 kB). Identical repaints used on several containers
(for example `ATFIRST/BAR.TBD#0` and `ETC_DATA/BAR.TBD#0`) are stored once per container; a content-addressed store would save
perhaps 15 %, not done (it would break the one-to-one mirror of translation/textures).

## 4. Why this is legal enough, in plain words

A COPY instruction contains no picture data: it says "bytes 1,000 to 1,400 of the file you already have". Everything the
delta carries as data (ADD / RUN) is bytes of OUR repaint that are not an equal run of the original at the same place or at
any other place of the original. A person who does not own the game cannot get a single Sega texture out of the delta.

What the delta does contain, honestly, by kind of texture (section 5 has the measurements):

* Raw textures (ARGB4444 / RGB565 / ARGB1555 twiddled or rectangular, 223 of 237): the ADD data is the changed rectangle of the
  repaint, our lettering plus the background we painted over the old Japanese (flat fills and gradients synthesised from the
  neighbouring pixels). These are new pixels. They sit exactly where the old text was, so they are "derived from" the original
  only in the weak sense that a fill matches its surroundings.
* VQ textures (fmt 1/2 dt 3; 14 of the 237 measured on 2026-11-12, **236 of the 637 delivered**, section 10): the repaint was re-encoded, which rewrites the 256-entry codebook and the index table.
  The new codebook entries are re-quantised versions of what the whole picture contains, so the ADD data of these deltas
  (14 textures: about 105 kB of ADD, 73 kB compressed; 236 textures: 941,005 ADD bytes, 665,364 delta bytes) is DERIVED from the whole original image, not only from our lettering,
  even though few bytes are equal to the original ones. This is the one honest weak spot of the delta route (section 6).
  Owner decision (2026-11-15, taken knowing the count is 236): **ship as is** for 0.1.0-beta.1; revisit before a non-beta release (section 6, option b).

Delta, hashes and the extracted original never leave the player's machine in a form that can be redistributed: the release
bundle carries deltas only (tools/release.py), never a .pvr and never an original texture.

## 5. Measured: how many original bytes are stored in the deltas (`texdelta.py analyze`)

Method: the instructions of every delta are listed; for each ADD, the longest substring that also occurs ANYWHERE in the
original texture is found (4-byte index over the original, every candidate extended; exact except inside degenerate runs of one
repeated 4-byte pattern, where the lower bound is taken at 64 candidates).

| measure | result |
|---|---|
| largest run of original-equal bytes stored in any ADD of any of the 237 deltas | 9 bytes (the encoder's rule: a run of 10 or more becomes a COPY, 6 or more at the same offset) |
| ADD bytes in total | 3,929,132 (10 to 24 % of the payload of the raw textures) |
| RUN bytes | 1,486,464 (one repeated byte, stored as 1 byte + a count) |
| COPY bytes | 29,219,572 (references only, nothing stored) |
| ADD bytes that equal the original byte at the same offset | 464,972 (11.8 % of the ADD bytes), all inside runs shorter than 6 bytes between two changes (transparent alpha, flat colour): chance coincidences, not unchanged regions |

By data type, ADD bytes as a share of the payload: raw textures 10.2 % to 24.4 %, VQ 46.7 % (13 textures fmt 2 dt 3) and 15.3 %
(1 texture fmt 1 dt 3). For the 14 VQ textures the measured overlap with the original is codebook entries equal to an
original entry 815 of 3,584 (23 %, almost all in the same slot) and index bytes equal at the same position 157,919 of
241,664 (65 %); these equal stretches are the COPYs (they are long enough), the rest is the ADD.

Reading of the numbers: no unchanged original region is embedded as ADD data (largest run 9 bytes, by construction below 10).
The 14 VQ deltas carry a re-quantised codebook and index table (derived pixels) as ADD data.

## 6. Recipe route for the VQ textures: NOT implemented, and why

The alternative would be to ship `translation/art/*.json` (tools/arttext.py specs) and regenerate the repaint from the original
texture on the player's machine. Not done because byte-identical regeneration cannot be proved:

* arttext.py renders text with fonts "looked up by alias among the fonts installed on the machine (Windows Fonts directory
  first); nothing is copied into the repository" (its own documentation): another machine has other fonts or other versions,
  and the result differs in the antialiased edge pixels;
* the repaints of the VQ textures (14 when this was written) went through ad hoc scripts (tools/re/*_edit*.py and similar) plus a VQ re-encode, not through
  one deterministic spec-to-texture command that a script could run.

Mitigations that stay inside the delta route, if the legal reading of section 4 is judged too weak for the VQ ones: (a) keep
the VQ deltas out of the public repository and regenerate them from a private recipe at release time (measured as 14 of 237
textures, 73 kB; on the delivered set 236 of 637, 665 kB; they would be an extra private asset of the release bundle); (b) redraw the VQ textures as raw
ARGB4444 textures of the same size (needs 128 kB instead of 32 kB for 256x256, so a slot check per texture; not investigated); (c) accept as is.
**Decided by the owner on 2026-11-15, with the real count of 236: (c) accept as is for 0.1.0-beta.1.**  Option (b) is the intended
clean-up to look at before a non-beta release.

## 7. Limits and notes

* The delta is only valid against the original texture of Redump disc 27370 (the hash in the manifest enforces it). A different
  revision stops `apply-all` with the texture named.
* A delta carries the repaint's GBIX/PVRT header too; for a TBD record the header is the synthesised one, so the repaint of a
  TBD texture must keep the `extract_pvr` header (all 237 current repaints do: `verify` round-trips them).
* `.gitignore` ignores `*.vcdiff` and `*.tbd` / `*.zar` / `*.pvr` anywhere and then re-includes `/l10n/textures/` (`!/l10n/textures/`, `!/l10n/textures/**`; the
  re-include comes AFTER the generic rules because the last matching rule wins, and the folders there are named like the containers: `BAR.TBD`, `SHTEX0.ZAR`).
  `git check-ignore -v l10n/textures/ATFIRST/BAR.TBD/#0.vcdiff` must print nothing; `translation/textures/` is ignored (the full repaints are not committed).
* Speed: `make` about 30 s, `apply-all` 4 s for all 237 (pure Python; `make` builds a 10-byte-gram index of the original per texture).
* Helper scripts: `tools/re/tdl_size.py` (plain vs LZMA sizes, xdelta3 cross-check), `tools/re/tdl_vq.py` (VQ overlap),
  `tools/re/tdl_dbg.py` (delta instruction listing for one texture).

## 8. build_patch default output unchanged (proof)

`tools/build_patch.py --dry-run` (standard flags) gives patch digest `cdd5866c9fb112bbd6581c41992353dc0943cd2d` three times:
with the file as it was before the `--textures-delta` edit (a temporary copy without the added lines), after the edit (flag
absent), and after the edit with `--textures-delta` pointing at deltas freshly made from the same tree (`make`, then rebuilt
inside the build). The last one also shows that the delta route reproduces the very same disc patch as the working .pvr files.

## 9. Independent review (skeptic run) and what it changed

Re-run in separate scratch directories: two `make` runs are byte-identical (238 files); `apply-all` rebuilds all 237 textures
byte-identically from LZMA and from plain deltas; `xdelta3 -d` accepts 12 sampled LZMA deltas and reproduces the manifest hash;
an independent 10-byte window check finds 0 of 3,929,132 ADD bytes' windows in the original (9-byte windows: 26,662, chance
hits in low-entropy art; the "longest run 9" claim of section 5 holds). File names and manifest contain no Japanese character.
Fixed after review: a damaged xz section raised `lzma.LZMAError` out of `apply_all` (now every decode failure is a
`TexDeltaError` naming the texture; the result size is capped at 64 MiB); a manifest path such as `../../x.pvr` could write outside
`--out` (now refused when the manifest is read); every write is atomic (temporary file + `os.replace`); `make` prunes deltas of
textures that no longer exist (only after a fully successful run); `apply-all` reports a `.vcdiff` that the manifest does not list;
problem lines no longer repeat the path. Known limits: the per-texture hash cannot see a damaged byte of the container that lies
outside the texture (the disc checksums of tools/verify_source_disc.py cover that); a hostile delta with a gigantic RUN is not
rejected before it allocates (bounded only by memory).

## 10. Delivered set of 0.1.0-beta.1 (637 textures) and the VQ known point

* `l10n/textures/`: 637 deltas + `MANIFEST.tsv`, 3,186,183 bytes of deltas (3.2 MB with the manifest and directory overhead on disk); smallest 269 bytes, median 3,236, largest 71,100
  (`TRAINING/TRAINING.TBD#4`), then 52,665 (`TRAINING/TRAINING.TBD#0`), 39,136 (`ETC_DATA/DRSSRANK.TBD#1`), 37,108 (three `DRS*` textures).
  No texture of `translation/textures/` is byte-identical to the original one (0 of 637), so nothing is skipped; an unchanged texture would have no delta and would not belong in the repository.
* Verified: `texdelta.py verify` (637 round-tripped, 0 problems), `apply-all` into a scratch folder and a byte comparison against `translation/textures/` (637 of 637 identical),
  `tools/test_texdelta.py --full` (96 checks), and `tools/build_patch.py --textures-delta l10n/textures` with the standard release flags gives patch digest
  `33be84fd97cab42d34645bb3c049978ba7a2ddce`, the digest of the release build made from the working PVRs.
* **Known point (VQ textures).**  236 of the 637 textures are VQ-compressed (15 fmt 1 and 221 fmt 2, data type 3; the 14 of sections 4 to 6 were counted on the earlier 237-texture set).  Repainting them re-encodes the picture, so the delta carries a re-quantised
  256-entry codebook and index table, i.e. new codebook data derived from the whole picture (section 4), not only our lettering.  It is harmless to how the game runs and was
  accepted as is by the owner (option "VQ as-is" of section 6).  Measured on the 637 (`tools/re/tdl_vq.py`, `texdelta.py analyze`): in all 236 the codebook differs from the original one
  (overall 13,357 of 60,416 codebook entries equal an entry of the original codebook, 653,034 of 1,224,704 index bytes equal the original byte); the 236 deltas carry 941,005 ADD bytes
  (665,364 delta bytes in total). The other 401 deltas carry only the repainted regions.
