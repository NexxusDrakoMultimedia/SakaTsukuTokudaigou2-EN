# Shipping the patch as xdelta (VCDIFF) files

PROVEN = checked by running the named script; INFERRED = deduced; UNKNOWN = not tested.
Pure Python 3 stdlib (maintainer side 3.11+ for `tomllib`; the player side 3.8+). Run with `python -I -X utf8 <script>`.

The English patch is shipped as standard xdelta3 / VCDIFF (RFC 3284) patches against the player's OWN dump of the Japanese
disc. No original Sega pixels are distributed. Maintainer workflow: `docs/RELEASING.md`. Player text: `README.md`, generated into every
release folder by `tools/release.py` (it also carries `TRANSLATORS_NOTES.md`, written by the docs stage).

## 1. Files

| File | Role |
|---|---|
| `tools/vcdiff.py` | VCDIFF encoder (positional + move-aware) and decoder (borrowed, see section 8). `make / apply / info / roundtrip` CLI |
| `tools/discformat.py` | detects and resolves `.cue` / `.gdi` / volume `.iso`, file hashing |
| `tools/bincue2iso.py` | raw tracks -> cooked volume ISO (`write_volume`, also a CLI) AND the reverse: Mode 1 sector codec (`encode_sector`: sync, MSF header, EDC, P/Q ECC) and `rebuild_raw_track` (patched ISO + the player's original raw track -> patched raw track) |
| `tools/isoexport.py` | maintainer-side strict exporter (same bytes as `bincue2iso.write_volume`, PROVEN by hash) |
| `tools/release.py` | builds a release bundle: verify source, build (or take a trial disc), patches, re-apply checks, docs, single-file `apply_patch.py`, zip |
| `tools/apply_patch.py` | the player-side patcher; `release.py` embeds `discformat`, `vcdiff` and `bincue2iso` into ONE stdlib-only file |
| `tools/verify_dist.py` | acceptance test of a bundle (also shipped in it, stdlib only): folder checks, and with `--source` every player route |
| `tools/release.toml`, `tools/VERSION` | recorded Redump 27370 source hashes, `[bundle] translators_notes`, `[dev.*]` hash tables; version (default `0.1.0-dev`) |
| `tools/test_vcdiff.py`, `tools/test_release.py`, `tools/test_bincue2iso.py` | self-tests (6 s, 11 s, 15 s) |
| `tools/re/rel_measure.py` | patch size / time measurement of a trial disc (positional vs move-aware) |

## 2. Supported inputs and routes

The disc is a GD-ROM: low-density area tracks 1-2, high-density area tracks 3-5 from LBA 45000 (`docs/disc-layout.md`).

| Form | Definition | Patch files used |
|---|---|---|
| **BIN/CUE** (Redump 27370) | `.cue` with one `FILE` per track; 5 raw 2352-byte files `<title> (Track N).bin`. Track 2 and 4 audio, track 5 starts with its 225 pregap sectors | `track03`, `track05` raw patches, or the ISO patch (route B) |
| **GDI** | `.gdi` (`5`, then `track lba ctl 2352 "file" 0`) naming `track01.bin track02.raw track03.bin track04.raw track05.bin`, raw 2352-byte | the same patch files (identical bytes) |
| **Volume ISO** | ONE file of 2048-byte sectors, file sector k = disc LBA 45000+k (IP.BIN in sectors 0-15, PVD at sector 16). Tracks 3 and 5 contribute their 2048 user bytes, track 4 and anything else zero sectors. 504,150 x 2048 = 1,032,499,200 bytes | `volume-iso` |

`apply_patch.py` (PROVEN end to end, section 7):

* **Route A, raw** (BIN/CUE, GDI whose tracks match the recorded hashes): the raw patch of tracks 3 and 5 is applied to the player's tracks, unchanged tracks
  are copied (or `--link`ed). 8 s for the real disc.
* **Route B, through the ISO** (`--method iso`, and automatically when a required track does not match but the cooked game data does, or when the release has
  no raw patches): the player's tracks are converted to the volume ISO with `bincue2iso.write_volume` (geometry from the manifest for a cue, from the file
  for a gdi), the ISO is hash-checked against the recorded source ISO, the ISO patch is applied (hash-checked against the result), then every changed data
  track is rebuilt by `rebuild_raw_track`: a sector whose 2048 user bytes did not change is copied from the player's own raw track (anything odd in the dump
  survives), every other sector is encoded as a canonical Mode 1 sector (same codec as `tools/discbuild.py`, which is where it comes from), audio and
  unchanged tracks are copied. With a reference dump the rebuilt track is hash-checked against the release's result hash; with another dump the game data
  of the result is re-cooked and compared with the patched ISO instead. 21 s for the real disc (cook, patch, rebuild and the hashes; measured as a whole).
  A manifest entry `raw_rebuild.<n>.encode` lists sector runs that must be encoded although their user bytes equal the original (an original all-zero
  sector that the disc builder rewrote as a real sector). `release.py` computes it by actually rebuilding the built track and comparing; a track that cannot be
  reproduced this way gets no entry and route B is refused for it.
* **ISO output** (`--to iso`, or ISO input): a patched volume ISO, 13 s from a cue, 8 s from an ISO. An ISO input cannot produce raw tracks (the audio tracks and
  the low-density area are not in it).
* Detection is by content and hash: extension, then content (`discformat.sniff`); then every track (or the ISO) is hashed and classed `original` /
  `patched` / `unknown` against the manifest (SHA-1 and SHA-256 and size). `--verify` only reports that. Already patched input is recognised and left alone.
* Tracks 1, 2 and 4 are NOT changed (PROVEN: `release.py` compares the built tracks with the source). A differing hash of one of them is only a warning; a differing
  hash of a required track (3, 5) goes to the game-data check of route B, and refuses (nothing written) if the game data differs too.
* Refused with a message (`discformat.explain`): a single `.bin` with all tracks, a `.gdi` with 2048-byte track files, a lone track file, an ISO whose sector 0 is
  LBA 0, an ordinary ISO without IP.BIN, CHD/CSO/CDI/NRG.

## 3. How a release bundle is made (tools/release.py)

1. The source (default: the repo's Redump cue) is hashed per track and compared with `tools/release.toml` (a mismatch names file and value). The
   translators' notes (`[bundle] translators_notes`, `doc/TRANSLATORS_NOTES.md`) must exist and must not contain the word `PLACEHOLDER` (`--allow-placeholder` for development bundles).
2. `tools/build_patch.py` builds the patched disc into `<work>/disc` (unknown options are passed through), or `--built-disc X.gdi` takes a finished trial disc
   (development bundle: README carries a banner, `MANIFEST.json` has `dev_build`; the `[dev.NAME]` table of release.toml is compared and reported).
3. Built tracks are hashed; a changed track gets a patch. Source and built disc are exported to volume ISOs; the exported source ISO is checked against the recorded hash.
4. `vcdiff.encode(move=...)` for each changed data track (`(2352, 16, 2048)`) and the ISO (`(2048, 0, 2048)`), then each patch is re-applied by `vcdiff.py`
   and by `xdelta3 -d -s` (on PATH or `C:\ProgramData\chocolatey\bin`) and compared with the built file; `compute_rebuild` for route B.
5. `<out>/<project>-<version>/`: the `.xdelta` files, `MANIFEST.json` (v2), `HASHES.txt`, `SHA256SUMS`, `README.md`, `TRANSLATORS_NOTES.md`, `apply_patch.py`
   (single file), `verify_dist.py`, `LICENSE`, `NOTICE.txt`, `VERSION`, `BUILD-SUMMARY.txt`; plus `<folder>.zip` and `.zip.sha256`. The date is `--date` (also the zip entry time:
   the zip is reproducible). `--no-raw-patches` leaves out the two raw patches (route B only; needs every changed data track rebuildable).
6. An empty translation DB gives a release with no patches (PROVEN with a tiny fixture).

`MANIFEST.json` v2 keys: `manifest_version, project, version, build_date, git_commit, dev_build?, game.title, layout.{hd_base, tracks.{n}.{kind,lba}}, tools, build,
tracks.{1..5}.{kind, lba, redump_name, gdi_name, source{hashes}, result{hashes}, changed, patch?{file, size, hashes, moved_sectors, moved_runs, checks, seconds}},
volume_iso.{source, result, changed, patch}, raw_rebuild.{n}.{encode, sectors}, raw_patches`. (v1 manifests, without `layout.tracks` and `raw_rebuild`, still apply by route A.)

The single file: `release.write_docs` replaces the block between `# @@EMBED-BEGIN@@` and `# @@EMBED-END@@` of `tools/apply_patch.py` with the verbatim
sources of the three modules as raw string literals executed as modules by name (`_load_embedded`). 83 KB. Imports are stdlib only (checked by `verify_dist.py` with `ast`).

## 4. The VCDIFF encoder

Windows of at most 8 MiB (xdelta3's default); COPY (unchanged), ADD (new bytes) and RUN (runs of >= 32 equal bytes, i.e. zero fill), default code table, no secondary
compression, no application header, so xdelta3, xdelta UI, DeltaPatcher and open-vcdiff decode it (xdelta3 3.0.11 PROVEN). The decoder also reads xdelta3-made patches incl.
secondary LZMA/DJW, the Adler-32 flag and VCD_TARGET windows (PROVEN against `xdelta3 -e`, `tools/test_vcdiff.py`).

**Positional match** (`move=None`): window n takes the same range of the source as its source segment; changed bytes are found by a hierarchical equality compare
(8 MiB, 1 MiB, 64 KiB, 4 KiB, 256 B, 64 B).

**Move-aware match** (`move=(sector, user_off, user_len)`, new): pass 1 finds the positionally changed ranges of the whole image; the target sectors in them are looked up (BLAKE2b of their
user bytes) among the source sectors in the SAME changed ranges (where a relocated file came from: its old extent was zero-filled or reused). Runs of target sectors with one constant shift
(`delta`) are joined, also across up to 512 edited sectors in between, and each run becomes its own window(s) whose source segment is the matching source range at the shifted offset; inside it
the normal byte diff applies, so a moved AND edited file stores only the edits, and for a raw track only the 16-byte header and 288 bytes of EDC/ECC per moved sector (about 300 B instead of 2352 B). Every window stays
<= 8 MiB, source segments too, so xdelta3's default 64 MiB source window limit is never reached (PROVEN: `xdelta3 -d` applies move-aware patches). Cost: one extra compare pass, +1 s on 1.1 GB. Limit: matches are
sector aligned (a shift that is not a multiple of the sector size, e.g. an insertion inside a file, is not found: the rest of that file is ADDed) and need identical user bytes per sector.
Zero sectors are never matched (RUN covers them). `LAST_STATS` reports `move_regions, move_sectors, windows`.

Speed (this machine, 1.2 GB tracks): ISO patch make 2.6 s, raw track 5 make 3.5 s, decode 3-5 s.

## 5. Hash tables

Source = Redump 27370 as dumped into the repo (also in `tools/release.toml`; the comparison with Redump's own database was NOT done):

| File | Size | SHA-1 |
|---|---|---|
| Track 1 / track01.bin | 5,597,760 | `ec178640c03ab98de4d07b76fd5555417137def1` |
| Track 2 / track02.raw | 2,088,576 | `0ecd537e42946f3e74c80c9fcb8d0bccccfc96f1` |
| Track 3 / track03.bin | 14,916,384 | `8a7c7484489d42896e3b73a8b2d4588720a3936d` |
| Track 4 / track04.raw | 12,519,696 | `fbdd698c67ee95d4223f9c873bb3697ee8447132` |
| Track 5 / track05.bin | 1,158,324,720 | `753b66f8a2a5553cce8abe804fa68145cf3522e4` |
| Volume ISO (exported) | 1,032,499,200 | `62a9ccfd3a965328861e5b46fa71e5686642e5e1` |

CRC-32 / MD5 / SHA-256: `tools/release.toml`. Result hashes change with every translation merge; they are in each release's `HASHES.txt` and `MANIFEST.json`.
`[dev.prop5]`, `[dev.prop6]` and `[dev.prop7]` (final disc, 2026-11-11: track 3 `64eec15d...`, track 5 `6e15e5e8...`, volume ISO `cc872a43...`) in release.toml hold the result hashes of the trial discs `build/trial/prop5/prop5.gdi` (stage 2) and `build/trial/prop6/prop6.gdi` (stage 3, 2026-11-11) as DEVELOPMENT records only
(prop5, tracks 3 and 5: SHA-1 `64eec15d...` and `6481afd4...`, volume ISO `5a06b8d8...`; prop6: track 3 the same `64eec15d...`, track 5 `9b017a74...`, volume ISO `794728f8...`); release.py compares a `--built-disc` against the table named by `--dev-name` and says so.  The patch sizes of section 6 were measured on prop5 and not repeated on prop6 (`tools/re/rel_measure.py` does it).  The prop5 / prop5r trial discs were deleted on 2026-11-11 to free disk space (the hash records stay as history only; the translation has moved on, so they can no longer be reproduced bit for bit), and the tools/verify_dist.py usage example that names `prop5.gdi` is only an example path.

## 6. Sizes (prop5 trial disc, 2026-11-11, no relocated file: "0 sectors in 0 moved runs")

| Form | Files | Bytes |
|---|---|---|
| BIN/CUE | `track03.xdelta` 253 + `track05.xdelta` 18,888,726 | 18,888,979 |
| GDI | the same two files (identical bytes) | 18,888,979 |
| ISO | `volume-iso.xdelta` | 15,662,332 |
| zip, all three forms + scripts | | 23,270,901 |
| zip, `--no-raw-patches` (ISO patch only) | | 9,978,002 |

The raw patch is larger by the header and EDC/ECC of every rewritten sector (about 304 B each, incompressible: the zip hardly shrinks it, 34.5 MB -> 23.3 MB, while the ISO patch zips to 9.9 MB).
Shipping only the ISO patch (`--no-raw-patches`) halves the download and costs the player 13 s more per apply (route B, 21 s instead of 8 s); decision for the maintainer.
An earlier first build (0.1.0-dev, 2026-11-10, 116 files, no proportional font): track 5 5.2 MB, ISO 4.0 MB.
Expectations: track 3 changes only in a handful of directory / IP.BIN sectors (a few hundred bytes); an in-place rewritten overlay costs about its size (cooked) or 1.15x (raw); a relocated file
costs about its edits (move-aware) instead of its size twice; the vacated extent is a RUN. If track 5 grows the patched disc exceeds the GD-R capacity (emulator only, `docs/disc-layout.md`); `README.md` says so.

## 7. Tests (what is PROVEN)

* `tools/test_vcdiff.py` (135 checks, 6 s): `changed_ranges` property; round trips (equal, edits, growth, shrink, empty, insertion, zero fill) at three window sizes; CLI; NEW move-aware: a synthetic cooked
  and a synthetic raw (position-dependent header and parity) disc with a 40-sector and a 20-sector file moved (one with an edited sector), vacated extents zeroed, appended sectors: decoded by `vcdiff.py` and by
  `xdelta3 -d`, patch at most a few KB over the real new data and under half the positional patch, moved runs found, windows cut at WINDOW, degenerate pairs; our patches applied by `xdelta3 -d -s`; `xdelta3 -e` patches applied by our decoder.
* `tools/test_release.py` (175 checks, 11 s as of 2026-11-11, including the bundled guide): release.toml vs files; detection and refusals; exporter; a tiny synthetic disc through `release.produce` and the shipped single-file `apply_patch.py` (subprocess, run with `-I` from another folder)
  in cue, gdi and iso forms, route A and route B, `--to iso`, `--verify`, refusals, second run refuses to overwrite, `--link`, a moved 2-sector file found in ISO and raw patch, forced-encode run (zero sector rewritten as a real sector), a dump with
  a damaged EDC but the same game data (patched through the ISO, the player's own sector kept), a dump with different game data (refused, nothing written), no-raw-patches bundle, PLACEHOLDER notes failing the bundle and `--allow-placeholder`, missing notes, release.toml
  `[bundle]` and `[dev.*]` sanity, `bincue2iso.encode_sector == discbuild.encode_sector`, empty release, reproducible zip, Python 3.8 syntax of every shipped file.
* `tools/test_bincue2iso.py` (15 s): also checks that the cooked ISO SHA-1 equals `release.toml` (so `bincue2iso` and `isoexport` produce the same bytes).
* End to end on the prop5 trial (2026-11-11): `release.py --built-disc build/trial/prop5/prop5.gdi --dev-name prop5 --allow-placeholder` built `build/release_dev/SakaTsuku2-EN-0.1.0-dev` in 46 s (patches re-applied with vcdiff.py and xdelta3, rebuildability of tracks 3 and 5 proven), then
  the bundle's own `verify_dist.py --source <repo cue> --built build/trial/prop5/prop5.gdi` (80 checks, 114 s): the original BIN/CUE in the repo root (hard links, read-only), a synthetic GDI and the cooked ISO were patched in every route; every output track /
  ISO is byte-equal (`filecmp`) to the trial disc and has the promised hash:

| Run | apply_patch.py time |
|---|---|
| BIN/CUE, route A (raw patches) | 8 s |
| BIN/CUE, route B (`--method iso`) | 21 s |
| BIN/CUE `--to iso` | 13 s |
| GDI, route A / route B | 8 s / 21 s |
| ISO input | 8 s |
| `--verify` (hash 1.2 GB) | 3 s |

  The same suite on the `--no-raw-patches` bundle (76 checks, 173 s): BIN/CUE and GDI automatically take route B (21-35 s), the rest unchanged.
* UNKNOWN: xdelta UI, DeltaPatcher and open-vcdiff were not run; Flycast was not launched; a real GDI from another dumper and real volume ISOs from other tools were not available (the gdi in the test is synthetic, tracks renamed);
  the Redump database was not consulted for the hashes; route B on a dump with differently stored audio tracks was only tested with synthetic damage (tiny disc).

## 8. Borrowed code (the author's own, GPL-3.0-or-later)

* `tools/vcdiff.py` <- `LMAST-Reverse/SRC/vcdiff.py` (SPDX and copyright header kept). Changes: `cso` import dropped, generic warning, hierarchical block compare, RUN encoding, empty target = header only, source hash of the last window fixed,
  Python 3.8-compatible, and now the move-aware encoder. The decoder (code table, address cache, RUN, VCD_TARGET, Adler-32, LZMA and DJW secondary compression) is unchanged.
* `tools/release.py` <- `LMASTER-Mod/tools/build_release.py` (header kept): structure (verify source, build, make patch, re-apply with the own decoder, cross-check with xdelta3, `HASHES.txt`, `SHA256SUMS`, zip + `.sha256`, build date as an input) carried over.
* `tools/bincue2iso.py` sector codec (`edc`, `ecc_pq`, `encode_sector`) is copied from `tools/discbuild.py` (same author and licence) so the shipped file needs no other module.
* The repo root has the GPL-3.0 `LICENSE`; `release.py` copies it into the bundle and `NOTICE.txt` names the licence of the shipped code.

## 9. Limits and open points

* Only the three forms in section 2; no per-track 2048-byte iso, no single-bin cue, no CHD. The cue route needs the track geometry of the manifest (a cue has no absolute LBAs).
* Move matching is sector aligned and needs identical user bytes (section 4). The disc builder currently relocates nothing in the trial disc, so the real-data benefit is untested; the synthetic tests prove the mechanism.
* The patcher needs Python 3.8+; there is no GUI. xdelta UI / DeltaPatcher can do the raw tracks by hand (`README.md` section 3), unverified here. A manual xdelta user of the `--no-raw-patches` bundle can only patch an ISO.
* Disk: route A needs one extra copy of the disc (~1.2 GB); route B about 2 GB more (temporary cooked and patched ISO in the output folder, removed afterwards).
* Result hashes embedded in a release are only valid for that translation DB snapshot; re-run `release.py` after every merge. `dist/SakaTsuku2-EN-0.1.0-dev` from 2026-11-10 is an older layout (PATCHING.md, `patcher/`); rebuild before use.
* `discbuild` writes a rewritten sector as a canonical Mode 1 sector even when its user bytes are unchanged; `release.py` records such sectors in `raw_rebuild.encode` instead of requiring the builder to avoid them. If the disc builder ever writes non-canonical sectors, route B is
  switched off for that track (route A keeps working).
