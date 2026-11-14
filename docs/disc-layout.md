# Disc layout and rebuilder (tools/discbuild.py)

PROVEN = checked by running tools/test_discbuild.py (117 s incl. the Stage 3 tests, all passed); INFERRED = deduced; UNKNOWN = not tested.

## API
```python
import sys; sys.path.insert(0, 'tools')
from discbuild import build_disc
r = build_disc({'/FLOW_PRG/MEETING.BIN': new_bytes}, 'build/out', 'SakaTsuku2-EN', src_dir='.', strategy='gap')
```
Writes `<name> (Track N).bin` (N=1..5), `<name>.cue`, `<name>.gdi` into out_dir. Streaming (9.6 MB chunks, ~3 s
for a 1.1 GB disc when cached). Paths are ISO paths (case-insensitive, `;1` ignored); unknown path -> KeyError.
CLI: `python -I -X utf8 tools/discbuild.py --out build/out --name X /ISO/PATH=localfile ...`.
By default only existing files are replaced and directories never move, so path tables are untouched. Stage 3 added opt-in
extras (new files / directories, dedupe, capacity guard, verifier): see "Stage 3 additions" at the end.

## Track structure (PROVEN from file sizes, headers, IP.BIN TOC)
| track | type | file sectors | first LBA of file | notes |
|---|---|---|---|---|
| 1 | MODE1/2352 | 2380 | 0 | low-density area |
| 2 | audio | 888 | 2380 | INDEX 00 at file start, INDEX 01 at +150 |
| 3 | MODE1/2352 | 6342 | 45000 | IP.BIN = sectors 45000..45015, PVD 45016 |
| 4 | audio | 5323 | 51342 | 150 sector pregap in file |
| 5 | MODE1/2352 | 492485 | 56665 | 225 sector pregap in file (INDEX 01 = 00:03:00), data from LBA 56890; file sectors 0..74 are all-zero 2352 B |

Track 3-5 LBAs are contiguous (45000+6342=51342, +5323=56665; end = 549150). The IP.BIN TOC1 at 0x100 confirms
it: track start FADs 0xB05E (=45000+150), 0xC9BA (=51342+150 pregap+150), 0xDED0 (=56665+225+150); lead-out at
0x290 = dword 0x410861B4, i.e. FAD 0x0861B4 = 549300 = end 549150 + 150, control 0x41. The rebuilder rewrites that lead-out FAD
when track 5 grows. The GDI LBA of tracks 1/2 (0 and 2380) is INFERRED by applying the same rule (file start incl.
pregap); the HD values are consistent with IP.BIN. Header MSF of every sector = LBA+150 (BCD) (PROVEN: all sectors verify).
.gdi lines: `track lba type(4 data/0 audio) 2352 "file" 0`.

## IP.BIN (PROVEN fields, INFERRED conclusion)
Meta header: "SEGA SEGAKATANA", maker, CRC "36E7", "GD-ROM1/1", product HDR-0183, V1.006, boot file name
`1ST_READ.BIN`. Besides that only the TOC1 block (3 track entries at 0x104, first/last/lead-out at 0x288-0x290) holds
layout numbers. No file size/LBA of 1ST_READ.BIN is stored: the BIOS finds it through ISO9660. The CRC covers
the product fields (inferred), not the TOC. So only the lead-out must be kept in sync (done).

## Sector format (PROVEN: all 501132 non-zero data sectors of tracks 1,3,5 regenerate byte-identical)
sync 12 | header 4 (BCD MSF=LBA+150, mode 1) | 2048 data | EDC 4 (CRC32 reflected poly 0xD8018001, init 0, LE, over
bytes 0..2063) | 8 zero | P 172 | Q 104 (RSPC over GF(256)/0x11D, ECMA-130; address included for Mode 1).
The implementation is a vectorised form (RSPC is linear: per-step GF multiplication via bytes.translate on whole
rows); coefficients are derived by running the classic ecm reference loop (`ref_pq`) on unit vectors, and
`ref_pq == ecc_pq` is also tested on 200 random sectors. Counts: track 1 2380/2380, track 3 6342/6342, track 5
492410/492485 identical, 0 mismatches; the other 75 are all-zero 2352-byte sectors (pregap start of track 5), kept
verbatim (never re-encoded unless overwritten).

## ISO9660 facts of this disc (PROVEN)
* 1235 directory records (1215 files, 20 dirs), no overlapping extents, no shared extents, no zero-size files.
* Volume space size in PVD = 504150 = end(549150) - 45000 (both-endian). Updated when track 5 grows.
* Root dir 45020; /BCAST/BCAST.BIN (307326 sectors at 68002) is part of the filesystem.
* Layout: system area 45000-45015, PVD 45016, terminator 45017, path tables 45018/45019, directories from 45020
  up to 45060, then unused 45061..51341 (6281 sectors, 12.8 MB, rest of track 3), track 4 audio, track 5 pregap,
  files from 56890 on (first file at 56890), 1ST_READ.BIN last (547560, 1440 sectors), then 150 unused sectors
  549000..549149. These 6431 unused data-track sectors are all all-zero and are the only reusable space.
  The disc is effectively FULL: the GD-ROM HD area ends at LBA 549150, so growth beyond the free area works in
  emulators but not on a real GD-R.

## Patch rules implemented
1. New size fits in the old extent's sector count -> same LBA; record size (both-endian) updated; rest of the
   extent zero-filled.
2. Otherwise relocate: strategy `gap` = first-fit into free all-zero sectors of the data tracks (the unused area
   above, plus extents vacated earlier in the same build); if none is large enough, append after the last sector
   of track 5 (file grows, PVD volume size and IP.BIN lead-out updated). `append` always appends.
3. Directory sector(s) are rewritten (extent + size, both-endian), then re-encoded with new EDC/ECC. Records that
   point to the same extent (none exist) would follow the data.
4. Only sectors that change are re-encoded; all others are copied raw, so an empty patch dict gives a
   byte-identical disc (sha1 of all 5 tracks equal to the originals: PROVEN).
5. File order affects seek time only. Not optimised.

## Test results (tools/test_discbuild.py, PROVEN)
1. EDC/ECC identity: see above. 2. No-op rebuild identical in 5 files; generated cue == original cue text.
3. In place: /DP3.INI same size (5619 B random) and /FLOW_PRG/MEETING.BIN 874298 -> 437272 B: re-read with
   tools/gdrom.py, exactly those 2 of 1215 files differ, extents unchanged, tracks 2 and 4 identical, structure ok.
4. Relocation: /DP3.INI 5619 -> 10619 B moved 59038 -> 45061 (gap); MEETING.BIN -> 14336777 B appended at 549150
   (track 5 grows 7001 sectors, new end 556151); all 1215 files re-read, the 2 changed ones match, the other 1213
   unchanged; every sector of all three data tracks of the output verifies (0 invalid); only 10 sectors of track 3
   differ from the original (IP.BIN sector 0, PVD, 3 dir sectors, 6 relocated data sectors -- counted 10).
5. Structure walk of the output: all extents inside data-track ranges (not in track 4 or the pregap), no overlaps,
   both-endian fields equal in 1277 directory records, L and M path tables list every directory extent,
   PVD volume size and IP.BIN lead-out equal the real end.

## Stage 3 additions (disc owner; PROVEN = run by `tools/test_discbuild.py` / `tools/test_discbuild_dsc.py`)

### Files
* `tools/discbuild_geom.py`: geometry model (`Track`, `Geometry`: default = this game, `from_gdi`, `from_cue`, `hd_regions()`, `check()`,
  `gdi_text` / `cue_text`). The default geometry's sheets equal `discbuild.gdi_text/cue_text` and the Redump cue (PROVEN).
* `tools/discbuild.py`: `DiscSpec`, `add_file`, `add_directory`, `DiscError`, `DiscFull`, `HD_END = 549150`; `build_disc(...)` and
  `plan_patches(...)` gained keyword options (all default to the old behaviour); `path_table()`, `DirModel`, `make_record()`.
* `tools/verify_disc.py`: the checker (CLI and `verify_disc()`), `Gdfs` (a minimal model of how the game opens a file).
* `tools/test_discbuild_dsc.py` (called by `test_discbuild.py`; `test_discbuild.py --only-dsc` runs only these).
* Helpers: `tools/re/dsc_cmp_default.py` (default-output proof), `dsc_trial.py` (trial disc from a `--dump` dir + report),
  `dsc_probe.py`, `dsc_plantry.py`, `dsc_ipbin.py` (read-only probes).

### 1. verify_disc (PROVEN on the original dump and on every disc the tests build)
`python -I -X utf8 tools/verify_disc.py DIR NAME [--source DIR] [--sectors auto|all|none] [--read-files]` (`--original` = the repo dump).
Checks: G1 gdi and cue parse, same track files / type / LBA / sector counts, files are whole sectors; G2 areas contiguous, HD area starts
at 45000, last sector below the ceiling 549150; V3 PVD (`CD001`, 2048 B blocks, volume space size = end - 45000 both-endian, terminator),
IP.BIN (`SEGA SEGAKATANA`, CRC-16/CCITT over 0x40..0x4F, TOC1 entry of every HD track from the geometry incl. pregaps, first/last track,
lead-out = end + 150, boot file present in the root); V5 every directory record (both-endian, even length, none across a sector,
strictly sorted, `.`/`..` right), path tables L and M identical and ordered (level, parent, name), size in the PVD; V4 two independent readers
(A = records from the PVD root, B = path-table driven) agree on all directories and extents; V2 every extent (system area, descriptors,
path tables, directories, files) lies in ONE HD data track after the pregap and below the ceiling, overlaps only when identical (= alias);
V7 patched / added files read back through their records equal the expected bytes, every changed file is announced or an identical copy
(dedupe follower); V9 EDC/ECC/MSF of every sector of tracks 1 and 3 plus every sector that differs from the original (and, with
`--sectors all`, every sector of every data track, multiprocess; 501,207 sectors on a standard build); with `rewritten` every differing
sector must be a planned one; free sectors, largest holes and stale ones (left by dedupe) are reported.
Result on the original: OK, 1215 files, 21 dirs, 6431 free sectors, 0 headroom. `test_discbuild_dsc.py` also corrupts a copy 14 ways
(PVD size, IP.BIN CRC / TOC / lead-out, both-endian field, `..` record, overlap, extent in the audio track, extent past the ceiling,
path table, unsorted records, EDC byte, gdi vs cue, partial sector) and checks that each is reported.
`build_patch.py` runs it after the build (`--verify-disc fast|full|off`, default fast) and prints the report; an error exits with 3.

### 2. Capacity guard (PROVEN, plan-level and build-level)
Content that would end past LBA 549150 (`max_lba`, the end of track 5) raises `DiscFull` (`build_patch`: `ERROR: disc full ...`, exit 1)
with the end LBA, the shortfall in sectors / bytes, the free sectors and three largest holes still unused, and the remedies. A file
cannot straddle the audio track 4 or start in the pregap (the allocator only uses the HD data regions). `allow_overflow=True`
(`--allow-overflow`) keeps the old append behaviour with a `plan.warnings` entry, for emulator experiments only (UNPROVEN in Flycast
and impossible on a real GD-R, docs/expansion/disc-layout.md s6). Tests: a 6281-sector file fits the track 3 hole, 6282 raises;
`append` strategy raises on the first appended sector; `tools/test_discbuild.py` test 4 (append of 7001 sectors) now passes
`allow_overflow=True`. The standard patch set of stage 2 needs no move at all (0 moves, end LBA 549150), so the guard does not trigger.

### 3. Dedupe, `dedupe=True` / `--dedupe-files on` (default off; PROVEN as a disc image, INFERRED in the game)
Groups are built from the FINAL bytes (patched files by their patch, others from the disc) so a patch that changes only one member splits the
group. The member with the lowest LBA keeps its extent (a changed keeper is placed by the normal rules and the others follow it), every other
member's directory record gets the same extent and size, the followers' old extents go to the free list (merged), so later movers /
added files can use them. Nothing is zeroed: the vacated sectors stay as they were (smaller xdelta; they are unreferenced; verify_disc
counts them as stale-free). On this disc: 15 groups, 20 followers, 3726 sectors (7.6 MB); free sectors 6431 -> 10157; only 6 directory
sectors are rewritten for a build without patches (`test_discbuild_dsc.py`: verify OK, all 1215 files read back through the Gdfs model
equal the original; patched case: BAR.TBD patched in both copies stays shared with the new bytes, HELP.DAT patched in one copy un-shares,
the four COMM/CON_REP/NF_CON/PASS_PL grown identically move ONCE and the three followers follow). Capacity effect proven at plan level:
seven 1000-sector movers fit only with dedupe (the seventh lands in an extent vacated by a duplicate).
Standard build with `--dedupe-files on`: 31,218 sectors rewritten (the same as without, plus 6), verify full OK.
**Default proof**: `tools/re/dsc_cmp_default.py build/dsc_discbuild_old.py DUMP [--grow]` builds the standard patch set (197 files, 64 MB,
`build_patch --dry-run --dump`) with the pre-stage-3 `discbuild.py` and the new one: tracks 1-5, cue and gdi are `cmp`-identical, with and
without extra growing files (2 gap moves). **Game side**: INFERRED harmless (name-based open, size from the record, no LBA anywhere,
docs/expansion/disc-layout.md s4); the boot test list s11 item 2/5 is the proof still owed. Not done: lever C (stubbing the Dream Passport tree).

### 4. Add file / add directory (PROVEN as a disc image, the game never reads the files)
```python
spec = discbuild.DiscSpec(res.patches, dedupe=False)
spec.add_file('/README.TXT', text_bytes)        # or discbuild.add_file(spec, path, data)
spec.add_directory('/EN')                       # optional; missing parents of an added file are created
discbuild.build_disc(spec, out, name)           # CLI: --add-file /ISO/PATH=LOCAL (build_patch.py too), repeatable; default none
```
Names are upper-cased and validated (A-Z 0-9 _, one dot, at most 30 chars; 8.3 is the safe choice). Records are inserted in sorted position with
the date of the directory's `.` record; the data goes into free sectors (hole first, like a relocated file). A directory without room moves to
free sectors and everything that points at it is kept in step: its `.`, the parent's record, every child's `..`, the PVD root record (root),
both path tables (regenerated from the tree; the regeneration reproduces the ORIGINAL L and M bytes exactly, tested), the table size / location
in the PVD (a table that outgrows one sector moves to new extents). Directories that are only touched in a link are re-serialised with the
standard packing (EVENT and SSONG were packed differently on the original; still valid). Test (one build): 45 files, 103 new directories (a nested
chain, 100 at the root), `/EVENT` (68 free bytes) and `/DPWWW` (has a sub-directory) and the root all move, the path table grows to 2524 bytes
(2 sectors), patches into the moved directories (shorter file included) land in the right records; verify_disc OK and all 1260 files read back
by name through the Gdfs model. Default (no adds): the planner produces no directory edit and the output is byte-identical (cmp proof above).

### 5. Verifier on the standard build with the stage 3 options
`build_patch.py ... --dedupe-files on --add-file /README.TXT=...`: 0 moves, 1216 files, 15 alias groups, 10,156 free sectors, verify fast OK in 10 s,
`verify_disc.py --sectors all --read-files` OK in 24 s (all 1216 files read through their records, 501,207 sectors valid, 11,241 sectors differ
from the original dump).

### Limits that remain (not done)
* Writer geometry is still fixed except track 5 growing at its end (`discbuild.TRACK_LBA`); the reader / verifier are geometry based
  (`Geometry`), a rebuilt disc with other track 3 / 4 lengths is not produced. `tools/gdrom.py` still reads only the original geometry.
* Deleting / renaming files, stubbing files, pinning, the cooked-ISO + move-aware xdelta path and the player-side track rebuild
  (docs/expansion/disc-layout.md s8-s9 steps 5-7) are not implemented.
* Nothing was booted: dedupe and added files are proven only as a structurally valid ISO9660/GD-ROM image read by two independent readers.

## UNKNOWN
* Never booted in Flycast/Redream here (no emulator run); the no-op build is bit-identical so it boots iff the
  original does. Growing track 5 and the GDI LBAs for tracks 1/2 are unverified in an emulator.
* Whether the game addresses data by absolute LBA outside ISO9660 (a relocated file would then break); the
  loader appears to use file names/ISO lookups, not verified.
* Exact Flycast behaviour with .cue for GD-ROM; use the .gdi to be safe.
