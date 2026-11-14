# Expansion study: the disc image layer (can the disc grow, and how)

Author: disc-layout study. READ-ONLY: nothing under translation/ or tools/ was changed; the only additions are small analysis scripts
`tools/re/dxp_*.py` (list at the end) and this file. Flycast and every window were not touched.
Status words: **PROVEN** = measured by a script here or in an earlier doc that ran code; **INFERRED** = deduced from code/spec/statistics;
**UNKNOWN** = needs a test that was not run (the test is named). Companion docs: `docs/disc-layout.md` (existing rebuilder),
`docs/xdelta-release.md`, `docs/texture-injection.md` s3, `docs/text-engine.md` s6, `docs/memory-map.md`.

## 0. Verdict in ten lines

1. The disc is FULL: the HD area ends at LBA 549150 and the last file ends at 549000; usable zero space is 6431 sectors = 13,170,688 bytes (PROVEN). Growing past 549150 is outside the GD-ROM spec; Flycast carries the HD lead-out 549300 as a constant (INFERRED, section 6), so images larger than that are a risk, not a plan.
2. Nothing in the game binaries hard-codes a file LBA, a file size, or the disc end. Files are opened BY NAME through the Sega GDFS; size, extent and sector count come from the ISO directory record (PROVEN for the open path, negative scan PROVEN for the 4-aligned literals, section 4).
3. So files may move and grow freely inside the ISO9660 volume, provided directory records, PVD volume size, (path tables only when directories move) and the IP.BIN lead-out stay consistent. The existing `tools/discbuild.py` already does this for REPLACING files (in place / zero gap / append) and is tested; it cannot ADD files or directories, cannot share extents, cannot reclaim space, cannot change track geometry.
4. Reclaimable space without touching content that matters: +3726 sectors (7.6 MB) by letting byte-identical duplicate files share one extent (PROVEN by sha1); +5846 sectors (12.0 MB) if the Dream Passport browser tree (DP*, 2_DP.BIN, ...) is reduced to 1-sector stubs (a content decision, reachability UNKNOWN); +5023 sectors (10.3 MB) if CDDA track 4 is shrunk (use UNKNOWN, and it shifts every later LBA). With the first two the budget is about 32 MB, plenty: the text growth measured in docs/capacity-ratio.md is about 0.3-3 MB.
5. The real limits of "grow" are not on the disc: they are RAM slots, load windows and in-container offsets (section 7). The disc layer never blocks a file that fits in RAM.
6. The delta problem: today's xdelta encoder is positional. A file that moves costs its whole size in the patch (about 43 MB if 108 overlays grow by 10 percent), and raw 2352-byte tracks cannot match moved data at all (MSF header and EDC/ECC change with the LBA). Fix = ship the patch against the cooked 2048-byte volume ISO only, regenerate raw tracks on the player side (109 s in pure python, deterministic), and give the VCDIFF encoder a move table so moved files are COPYed from their old place.
7. Save-game compatibility: the disc layer cannot affect it (no save data lives on the disc; IP.BIN product fields are left untouched).
8. Design (section 9): a two-phase rebuild, metadata first (directories, path tables, PVD, IP.BIN) then file extents with a pin list (big untouched files never move) and an allocator over zero gaps plus vacated and shared extents; output = cooked volume ISO (canonical) and raw tracks/GDI/CUE.
9. Tests (section 10): identity, structure walk with two independent readers, read-back of all 1215 files, grow/move/alias/add-file/add-dir/overflow cases, raw round trip, xdelta size and xdelta3 cross-check.
10. Boot check list for the user: section 11.

## 1. How the disc is built today (code map, PROVEN by reading the code and running tests earlier)

* `tools/build_patch.py` `build_patches(...)` returns `Result.patches = {iso path: new bytes}` for files whose bytes CHANGED only; `main()` (line 906) then calls `discbuild.build_disc(res.patches, out, name, ROOT, a.strategy)` (`--strategy gap|append`). `--dry-run` skips the disc. No other disc code path.
* `tools/discbuild.py` (529 lines): `Source` reads the original five tracks by absolute LBA through the hard-coded `TRACK_LBA = {1:0, 2:2380, 3:45000, 4:51342, 5:56665}`, `TRACK_PREGAP = {5:225}`, `PVD_LBA = 45016`, `HD_BASE = 45000`. `read_filesystem` walks the directory tree (records only; path tables are never read), `used_extents` + `free_gaps` find the zero space, `plan_patches` places files, `write_track` streams every track (copy raw sector, re-encode only overridden LBAs with `encode_sector`), `cue_text` / `gdi_text` are fixed templates.
* Placement rules (`plan_patches`): new size fits the old extent's sector count -> same LBA, zero-fill the rest; else first fit into zero-only gap sectors of the data tracks (also extents vacated earlier in the same build); else append after track 5 and raise the PVD volume space size (+80..87, both-endian) and the IP.BIN lead-out dword at 0x290. Directory records are patched in place (extent +2/+6, size +10/+14); only the directory sector holding the record is rewritten.
* Limits found in the code (these are the gaps the rebuild mode must close):
  1. no add / delete / rename of files or directories; `KeyError` for unknown paths;
  2. no shared extents (an alias list exists only for records that ALREADY share an extent: none do, PROVEN);
  3. directory sectors and path tables are never re-authored (a directory cannot gain a record beyond its slack; EVENT has 68 free bytes, SSONG 64, section 3);
  4. track geometry is a constant: tracks 3/4 cannot change length, track 5 can only grow at its end; `gdi_text`/`cue_text` do not take geometry;
  5. no capacity check: it silently appends past LBA 549150 (emulator-only, the doc says so, the code does not warn);
  6. `tools/gdrom.py` (`HD = [(3,45000),(4,51342),(5,56665)]`) and `Source` read only the ORIGINAL geometry, so a rebuilt disc with other track lengths cannot be re-read by them;
  7. every build re-reads and rewrites all 1.1 GB; the gap scan reads sector by sector in python (acceptable, about 1 s).
* Existing test evidence (docs/disc-layout.md, `tools/test_discbuild.py`, 74 s): all 501,132 non-zero data sectors regenerate byte-identical (EDC/ECC codec PROVEN); no-op rebuild is bit-identical; in-place, gap relocation and append all re-read correctly; the output tracks verify sector by sector.

## 2. Geometry and capacity (PROVEN unless marked; `dxp_layout.py`, `dxp_dirs.py`, `dxp_gapcheck.py`)

| track | kind | file sectors | first LBA (file start) | note |
|---|---|---|---|---|
| 1 | data | 2380 | 0 | low density, left alone |
| 2 | audio | 888 | 2380 | left alone |
| 3 | data | 6342 | 45000 | IP.BIN 45000-45015, PVD 45016, terminator 45017, path tables 45018 (L) / 45019 (M), root 45020, 20 directories 45021-45060, FREE 45061-51341 |
| 4 | audio | 5323 | 51342 | 71 s of real music (rms>100 in 5057 sectors, `dxp_audio.py`) |
| 5 | data | 492485 | 56665 | 225 pregap sectors (75 all-zero raw), files from 56890, last file 1ST_READ.BIN ends 549000, FREE 549000-549149 |

* Volume: 1215 files + 20 directories, total file bytes 1,006,614,223 (492,110 sectors); volume space size in the PVD 504,150 (= 549150 - 45000); the volume id is the placeholder `SAMPLE_GAME_TITLE`.
* **Free space, exact**: track 3 tail 6281 sectors = 12,863,488 B; track 5 tail 150 sectors = 307,200 B; total **6431 sectors = 13,170,688 B**. Every one of those sectors has zero user data and is a valid Mode 1 sector (not all-zero raw): 6281/6281 and 150/150 (`dxp_gapcheck.py`). The gap 45061..56889 is 11,829 sectors = 6281 + track 4 (5323) + the 225 pregap, so only the 6281 are file space. A file must lie wholly inside one data track (it cannot cross 51342 or touch the pregap): the largest file that fits the track 3 hole is 6281 sectors (12.9 MB).
* Per-file sector rounding wastes 1,227,057 bytes in total (average 1010 B per file): free only as "grow within the last sector" (no extent change, directory size field only).
* Where the bytes are: BCAST 644.0 MB (3 files: BCAST.BIN 629.4 MB, ENDING_L.P04 / ENDING_R.P04 7.3 MB each), GAME 169.5 MB (BINDUNIF.BIN 120 MB, BINDFLAG.BIN 15.4 MB, JPHOTO.BIN 5.8 MB ...), FLOW_PRG 57.4 MB (176 files, the 114 overlays are 39.1 MB / 19,136 sectors), ETC_DATA 40.8 MB, EVENT 26.5 MB, SOUND 15.5 MB, rest below 10 MB each. `BCAST.BIN` starts with the text `PCM FILE START` followed by `kk\kk_aidu_0001.p04`: a self-describing concatenation of ADPCM voice files (INFERRED; the game prints `Bcast Error !! : Ring Buf Status is PLAY`, i.e. it streams it through a ring buffer, `FLOW_PRG/GAME.BIN` 0x196d00).
* **Reclaimable space** (`dxp_dups.py`, `dxp_plan.py`):

| lever | sectors | bytes | status | cost / risk |
|---|---|---|---|---|
| A zero gaps (above) | 6431 | 13.2 MB | PROVEN | none |
| B byte-identical files share one extent | 3726 (20 extents, largest 520) | 7.6 MB | PROVEN (sha1) | both names keep working; the two copies must stay identical in every build (BPINFO, TITLE, HELP.DAT ... are patched in both copies today, `translation` stages already do that); a later divergence needs un-sharing |
| C Dream Passport browser tree stubbed to 1 sector each (108 files: 2_DP.BIN 3.6 MB, DPFONT 4.0 MB, DPETC 2.3 MB incl. DP3SOUND.MLT 1.7 MB, DPTEX 1.55 MB, DPSS, DPWWW, MANATEE/NAMIHEI.DRV, MAIGO.BIN, SG_DPLDR.BIN, DP3.INI) | 5846 | 12.0 MB | INFERRED that nothing else needs them; DP3.INI names them by path; `DPETC/MESSAGE.INI` is being translated, so reachability from the game's network menu is UNKNOWN | content decision; a stubbed file makes the browser fail with FILE OPEN or garbage instead of an error screen |
| D CDDA track 4 shrunk to the minimum (keep 150 pregap + 150) | 5023 | 10.3 MB | UNKNOWN whether the game plays it (it contains music); needs a shift of track 5 (every LBA of track 5 changes) and a TOC edit | high: breaks positional deltas unless the encoder is move-aware; do last |
| E tail slack | 1.2 MB total | | PROVEN | not usable across files |
| F ECC/EDC/header | none | | | Mode 1 2048 user bytes per sector is fixed |

A+B+C = 16,003 sectors = 32.8 MB; with D 43.1 MB. Biggest hole after A only: 6281 contiguous sectors; B and C free many smaller extents (largest 1759 for 2_DP.BIN).
* What the text work needs (docs/capacity-ratio.md): about 319 KB extra over 114 overlays if everything is natural English; the prose overlays grow most (NEWS +51 KB, MEETING +24 KB, DRAFT +22 KB). Even a 10 percent growth of all 114 overlays needs a net 1911 sectors (`dxp_plan.py 10`: 108 files cross a sector boundary, new extents 21,011 sectors, vacated 19,100). A 40 percent growth needs a net 7646 sectors = more than lever A alone (6431), but A+B is enough. So the disc budget is not the binding constraint.

## 3. ISO9660 and IP.BIN facts a rebuild must reproduce (PROVEN, `dxp_dirs.py`, `dxp_ipcrc.py`)

* PVD at 45016: volume space size at +80 (both-endian) = 504150; logical block 2048; path table size 290 at +132; L path table LBA 45018 at +140, M path table LBA 45019 at +148 (the optional ones at +144/+152 are 0); root record at +156 (extent 45020, size 2048).
* Path table: 21 entries (root + 19 top-level dirs + `HELP` in `DPWWW`, parent index 9), one sector each (290 of 2048 bytes). Only extents of directories appear in it, so moving FILES never touches it; moving or adding a DIRECTORY does (both tables, sorted by parent number then name, parent numbers renumber).
* Directories: 20 + root, all contiguous in 45020..45060 with no gap in between (TRAINING 45060 is last, 45061 is the start of the free hole). Free bytes in the last sector of each: root 830, ETC_DATA 940, FLOW_PRG 1960, GAME 470, EVENT 68, SSONG 64, others 700-1900. A record is 33 + name + `;1` (+1 pad byte for even length), so about 46 bytes: EVENT/SSONG hold 1 more file at most, FLOW_PRG about 40. Adding a file to a full directory needs the directory extent to grow by a sector, i.e. relocation of that directory (parent record, own `.` and `..`, children's `..`, path table entry in both tables).
* Records are ISO level 1 names with `;1`, flags 0 / 2, 7-byte date, system-use area absent; the root is sorted. Keep records sorted and never straddle a sector boundary (zero padding to the next 2048).
* No extent is shared today, no extent overlaps, no zero-size file; 1ST_READ.BIN is the LAST file (547560, 1440 sectors) and its extent is the only one near the end.
* IP.BIN (32,768 bytes, sectors 45000-45015): header `SEGA SEGAKATANA`, boot file name `1ST_READ.BIN` at 0x60, product HDR-0183 V1.006, date 20011111. The 4-hex-digit CRC at 0x20 (`36E7`) is **CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over bytes 0x40..0x4F** (product number + version): PROVEN by search (exactly one range matches). The TOC copy is NOT covered: `0x100` = `TOC1` magic, track entries at 0x104 (0x4100b05e: ctl 4, FAD 0xB05E = 45150), 0x108 (0x0100c9ba: FAD 0xC9BA = 51642), 0x10c (0x4100ded0: FAD 0xDED0 = 57040); 0x288 / 0x28c = first/last track (3 / 5), 0x290 = lead-out 0x410861B4 (FAD 549300). Changing the lead-out or track entries needs no CRC fix. IP.BIN contains NO word equal to 1ST_READ's LBA/FAD/size, to the PVD, or to the disc end (scan, PROVEN): the bootstrap finds 1ST_READ.BIN by name (the header field) through ISO9660 (standard Katana bootstrap behaviour: INFERRED; every homebrew disc places 1ST_READ.BIN freely).

## 4. Does the game hard-code any LBA, size, or disc end?  (answer: no)

Evidence, strongest first:
* **The open path is name based and the size comes from the directory record (PROVEN by decompilation, `tools/re/texinject/t8.txt`, `docs/text-engine.md` s6)**: `FUN_8c15eede(name, ..)` opens by name ("FILE OPEN ERROR (%s)"), `FUN_8c15fb72` copies the handle length (`handle+0xc`, set by the GDFS from the dirrec) to `+0x28` and computes `(len + 0x7ff) >> 11` sectors; `FUN_8c15fc3c` opens + seeks a byte offset inside the file (BCAST streaming); no size table exists.
* **GDFS init (this study, Ghidra 12.2 headless on a copy of the project, `1ST_READ.BIN` base 0x8c010000)**: `FUN_8c159da0` calls the GDFS init wrapper `thunk_FUN_8c01d304` -> `FUN_8c01bd26` with arguments (8, work, **1024**, dirtab): the halfword at 0x8c159e92 is 0x0400, the open-handle count is 8. `FUN_8c01bd26` is the standard Sega gdFsInit: it reads the PVD (`CD001` check, function `FUN_8c01b696`), takes the root record and the path table location/size from the PVD, loads the path table into the directory table, returns -0xc if it does not fit, and records the volume info. Consequence (INFERRED from the standard library): up to 1024 directory-table entries are supported, we have 21; the open handle holds start, byte length and sector count taken from the record. The literal 45150 (0xB05E, the GD-ROM HD base FAD) appears in 1ST_READ at 0x8c01bc60 / 0x8c01c364 / 0x8c01c65c (mount code): it is the standard HD base, equal on any valid GD-ROM and independent of our layout.
* **Negative scan, all 1215 files** (`dxp_lbascan.py`, output `build/dxp_lbascan.txt`): 4-aligned u32 words equal to the start LBA or FAD (LBA+150) of any file, to the byte size or sector count of any file >= 4096 B / 64 sectors, or to 549150 / 549300 / 504150 / 56665 / 56890. Result: **`1ST_READ.BIN`, `IP.BIN`, `2_DP.BIN`, `MAIGO.BIN`, `SG_DPLDR.BIN`, `DP3.INI`: no LBA/FAD/disc-end hit** (their only special hits are 45150 = HD base, and size coincidences: 131104 = 0x20020 = a 256x256 16-bit PVR + header, which is also the exact size of `0GDTEX.PVR`: a texture buffer constant, not a link). The overlays (`FLOW_PRG/*`, `ATFIRST/*`) have a few LBA-valued words (e.g. 393402/393425/393451 in DRSDENDO.BIN = the LBAs of ETC_DATA/SECFTEX0-2.ZAR; 524418 in four overlays); inspected: they sit in dense tables of packed 16-bit sprite coordinates (`0x00470 01b1`-style pairs), the earlier `lbahits.py` reached the same verdict. The data files' hits (BCAST.BIN 386, SCN_DATA.BIN 352, BINDUNIF.BIN 28 ...) are random matches in compressed/ADPCM/graphics payloads (expected count for random 32-bit data over 157 M words and 1215 values is about 44; the excess is structured data, not checked word by word; none in a file that has a file-table role is known).
* Limits of the scan: aligned words only; run-time computed constants (`mov #imm` + shifts) and 16-bit-split values are not covered; but the SH-4 loads a 32-bit constant from a literal pool, so a hard-coded LBA >= 65536 would appear as an aligned word. INFERRED safe, PROVEN for literal words.
* Container index tables are file-relative, not LBA based: `ETC_DATA/ESTABLIS.ARC` begins with 87 entries (name, offset 0x1000.., size) relative to the file (first words 0x57, name, 0x1000, 0x864d), `FLOW_PRG` bind-style archives and `GAME/BIND*.BIN` are offset-indexed from code (docs/texture-injection.md s7: addressed by offset from outside, INFERRED). Moving such a file on the disc is harmless; changing bytes INSIDE it is the problem (section 7).
* Disc end: 549150, 549300 and 504150 occur in no code image and no data file (`special` list of the scan): the game never asks how big the disc is.

Verdict: **PROVEN** for name-based opening and directory-supplied size; **INFERRED** that nothing else addresses the disc by LBA; the only way to be certain is the boot test list in section 11 (a relocated file that the game then still finds proves it per file).

## 5. IP.BIN, TOC and what must change when geometry changes

| change | must update | evidence |
|---|---|---|
| file moves / grows inside the volume | its directory record (extent, size, both-endian); nothing else | PROVEN (`test_discbuild.py`) |
| files added to an existing directory | the record list (sorted, padded), directory size if it crosses a sector | spec; INFERRED GDFS scans records linearly or by name |
| directory moves/added | its record in the parent, `.`/`..` entries, children `..`, path tables L and M (entries, parent numbers, size at PVD +132, PVD +140/+148 if they move), PVD root record if root moves | spec |
| last data sector index changes (track 5 grows or shrinks) | PVD volume space size (+80); IP.BIN lead-out dword at 0x290 (FAD = end + 150 | 0x41 << 24); `.gdi`/`.cue` unchanged (they carry starts only) | PROVEN code path in `discbuild.plan_patches` |
| track 3 or 4 length changes | IP.BIN TOC1 entries at 0x108 / 0x10c (FADs), `.gdi` LBAs of tracks 4 and 5, every sector header MSF of track 5 and 4's position, `TRACK_LBA` | INFERRED; also changes every extent LBA after the point |
| IP.BIN touched | nothing else: the CRC covers 0x40..0x4F only | PROVEN |

## 6. How far can the image grow?  (capacity ceiling)

* GD-ROM HD area: LBA 45000 to 549150 = 504,150 sectors = 1,032,499,200 bytes; our volume is exactly that size. Real GD-R media cannot hold more. GDEMU and other loaders read a GDI from storage; whether their BIOS-facing TOC accepts a last track longer than the spec is UNKNOWN (not tested here).
* Flycast (static look at `C:/Games/Emulators/Flycast/flycast.exe`, file read only, never started): the 32-bit immediate 0x000861B4 (= 549300 = the HD lead-out FAD) occurs 7 times (0x1bad7d `cmp esi, 549300; je`, 0x1bae4d, 0x1bae58, 0x1c008e, 0x1c009d, 0x1c2275, 0x1c227f in code that stores `0x0104` and 549300 together, i.e. the GD-ROM TOC / disc-info reply). INFERRED: Flycast reports the standard lead-out regardless of the tracks and may compare read addresses with it. The existing append mode (track 5 longer than 549150) is therefore UNPROVEN in Flycast, and unlikely to be accepted by a real GD drive. Recommendation: treat 549150 as a hard ceiling; make the builder fail by default beyond it (`--allow-overflow` only for experiments); decide by the Flycast / GDEMU tests of section 11 (test T9).
* Low-density area (tracks 1-2, LBA 0..3267) holds nothing usable for files here (data track 1 is 2380 sectors of the SEGA disc area); not touched.

## 7. Sizes carried inside container files (what must stay in sync; PROVEN from earlier docs unless marked)

| thing | carries | consequence for growth |
|---|---|---|
| ISO9660 directory record | extent LBA, byte length (both-endian) | the ONLY size/offset the GDFS needs to read the file; the file loader reads `ceil(len/2048)` sectors |
| ZSARC container (`.ZAR`, `GAME/*.BIN`, ...) | per member header: packed size, orig size, CRC-16 of the decoded data, header CRC (verified at every load), member walk is sequential, `hdrlen == 0` ends an archive; no total length, no member table | members can change as long as headers are rebuilt (`bzlib.build_header`); bind-style files with several archives padded to 2048 are indexed from outside by file-relative offset: do not shift later archives (INFERRED) |
| TBD texture tables | relative offsets, no size field | rebuild offsets after a record changes |
| FONT.BIN (root and ATFIRST) | header words (glyph count, table offsets 0x10 / 0x3910 / 0x9c51c) | loader reads `ceil(size/2048)` sectors into a window of 679,936 B (0x8cd5c000-0x8ce02000, 332 sectors); the next fixed load (SHTEX0.ZAR at 0x8ce02000) follows: a larger FONT.BIN overwrites it (docs/font.md) |
| ATFIRST boot files (SHTEX0.ZAR, BAR.TBD, SECFTEX0.ZAR) | none | fixed load addresses with 16,234 / 8,488 / 100,818 spare bytes (docs/memory-map.md) |
| overlays (FLOW_PRG/*.BIN) | none on disc; `_end` word inside the image, descriptor slot count | file must stay inside its `count` 1 MiB slots; BSS beyond the file is not loaded or cleared; growth needs the `_end` word raised (docs/memory-map.md s3) |
| ESTABLIS.ARC | in-file index (87 entries: name, offset, size) | file-relative; a changed member needs the index rewritten |
| BCAST.BIN | in-band `PCM FILE START <name>` headers, read through a ring buffer with a byte-offset seek | keep byte-identical; pin it (never move, never rewrite) |
| DP3.INI / DPSS | path names | name-based; stubbing breaks the browser only |
| 1ST_READ.BIN | loaded by the BIOS at 0x8c010000, 2,949,120 B ends at 0x8c2e0000 where overlay slot 1 starts | cannot grow (RAM), in-place patches only (INFERRED from docs/memory-map.md) |

So the disc layer's contract is simple: **given new bytes for a path, put them in a contiguous extent of one data track and update the record**; the file's internal consistency is the caller's job.

## 8. Patch size when files move (xdelta)  (INFERRED from the encoder code; numbers from `dxp_plan.py`)

* `tools/vcdiff.py` `encode` is positional: window n of the target is encoded against the SAME range of the source (`encode_window(src, tgt, src_pos)`); a moved or grown file is stored whole. Raw tracks add a second, harder problem: each raw sector carries its own LBA in the header and EDC/ECC computed over it, so even a perfect move leaves every moved raw sector different from every source sector; no copy instruction can match them.
* Examples (`dxp_plan.py`): 10 percent growth of the 114 overlays = 108 files cross a sector boundary, new extents 43.0 MB (positional patch of about that size, no compression in our encoder; xdelta3 with LZMA would about halve code but not text); 40 percent = 54.8 MB. If a growing overlay stays inside its last sector slack (average 1010 B) it costs only the edited bytes.
* The cooked ISO is better: 2048 user bytes per sector, no header/ECC. With a MOVE TABLE the encoder can emit, for a moved file, windows whose source segment is the OLD extent (`src_pos = old_lba * 2048 - HD_BASE * 2048`, any position is legal in VCDIFF; `vcdiff.decode` already reads `w.seg_pos`), so a moved overlay costs only its edited bytes. Windows must be split at file boundaries (at most about 1300 windows, each under the 8 MiB limit; xdelta3's default source window is 64 MiB, so any segment of 8 MiB or less is fine). xdelta3 itself never needs to be the encoder.
* Consequence for the release format: ONE xdelta against the player's cooked volume ISO (the project's `volume-iso` form already exists, docs/xdelta-release.md s2) + a small manifest of the new geometry; the player tool rebuilds raw tracks 3 and 5 from the patched ISO with `discbuild.encode_sector` (measured here: 216 microseconds per sector = 109 s for 504,150 sectors single-threaded, `dxp_bench.py`; all-zero sectors and track 4 can be skipped; multiprocessing makes it about 10 s), copies tracks 1, 2, 4 from the player's dump, writes `.gdi`/`.cue`. The result is hash-checked against the maintainer's build (the codec is byte-exact on 501,132 sectors, PROVEN). If this change is not wanted, the pin policy below keeps moves small.
* Pin policy (recommended even with the move table): never move files that are unchanged by the patch and large (BCAST.BIN 629 MB, BINDUNIF.BIN 120 MB, BINDFLAG, ENDING_*.P04, JPHOTO, ESTABLIS.ARC, SOUND/*, FACE, EVENT data). Movers are only changed files that outgrew their extent. This keeps every unchanged byte at its original LBA in both the raw and cooked forms.

## 9. Design: rebuild-the-image mode  (`tools/discimage.py`, new; reuses the `discbuild.py` codec)

Goal: write a disc in which any file can grow, shrink, be added, or share an extent, without a per-case workaround, with an invariant checker that can reject a bad image before anybody boots it.

### 9.1 Data model
* `Geometry`: ordered tracks `[{no, kind data|audio, lba_start, nsec, pregap_in_file, file}]` read from a `.gdi`/`.cue` (or defaults for this game), plus `hd_base = 45000`, `max_lba = 549150` (first LBA after the last usable sector), `track5_pregap = 225`. It replaces the constants `TRACK_LBA`, `TRACK_PREGAP`, `HD_BASE`, `PVD_LBA` in `discbuild.py` and in `gdrom.py` (so a rebuilt disc can be read back).
* `Volume`: parsed from the SOURCE disc: PVD (raw 2048 bytes), path tables, a tree of `Dir` (record template bytes incl. date, flags, `.`/`..`) and `File` (name, dir, old_lba, old_size, source = `orig | bytes | alias(of) | stub(n sectors)`, `pin` flag). Extents known for system area, volume descriptors, path tables, directories, files.
* `Spec` (what the caller wants): `{iso_path: bytes}` for replaced files (same as today), plus optional `add: {iso_path: bytes}`, `alias: {iso_path: other_iso_path}` (or `--dedupe` to alias all byte-identical sets), `stub: {iso_path: n_sectors}` (zero or marker file of n sectors, size field kept honest: one zero sector, size 2048), `pin: [globs]` (default: every file not in `replace`), `max_lba`, `overflow = error|append`.

### 9.2 Algorithm (two phases)
1. **Metadata first.** Re-serialise the whole tree from the model (the existing bytes are reproduced when nothing changes: required by test T1): directories as sorted records per sector with zero padding; path tables L and M from a breadth-first numbering (ISO order: level, parent index, name); PVD (volume size, path table size and LBAs, root record); IP.BIN dwords. If a directory outgrows its sectors or a directory is added, give it a new extent from the free list BEFORE files are placed; the metadata block 45017..45060 stays where it is whenever it fits (so its sectors are byte-identical and cost nothing in a delta); otherwise it is rewritten at the start of the track 3 hole (a few sectors, order in the hole is irrelevant). Alignment: files start at sector boundaries, size field is the byte length, tail zero-filled.
2. **Extents.** Pass over files in a fixed order: (a) pinned or unchanged: keep LBA; (b) changed and new sector count <= old: keep LBA, zero-fill the tail; (c) aliases point to the extent of their target (and the vacated extent of the alias joins the free list); (d) changed and larger, or new: allocate. Allocator = free list of `[start, count]` ranges, initially the zero gaps of the data tracks that are valid (tracks 3 and 5 only, never across 51342 or inside the pregap) PLUS extents vacated by moves/aliases/stubs in this build; best fit (smallest range that holds it), largest files first; vacated ranges are merged. Extents stay contiguous; a file never straddles tracks. Failure (no range large enough, or beyond `max_lba`) -> `DiscFull` listing the largest free ranges and the shortfall; with `overflow=append` the track 5 grows and the build prints a loud warning.
3. **Emit.** Produce the sector map `{lba: 2048 bytes}` for every sector that differs from the source, then (a) the cooked volume ISO by streaming the source ISO and overlaying the map (zero cost for unchanged bulk), (b) raw tracks by the existing `write_track` approach generalised to `Geometry` (copy unchanged raw sectors, `encode_sector` for overridden ones), (c) `.gdi`/`.cue` from `Geometry`, (d) a `layout.json` manifest (every moved file: path, old LBA, new LBA, size, sha1) used by the move-aware xdelta encoder and by the verifier.
4. **Verify (always run, fails the build).** Invariants of section 10 (V1..V12).

### 9.3 Interfaces
* `build_disc2(spec, out_dir, name, src_dir, geometry=None) -> Report` (moves, freed sectors, free sectors left, new end LBA, sector counts, manifest path); `discbuild.build_disc` stays as a thin wrapper for compatibility (same results for the old calls).
* `tools/build_patch.py`: new options `--layout inplace|rebuild` (default inplace until tested), `--dedupe`, `--stub-dp`, `--pin GLOB...`, `--max-lba N`, `--allow-overflow`, `--emit-iso`. `Result.patches` stays `{path: bytes}`; new `Result.add`, `.alias`, `.stub`.
* `tools/release.py` / `apply_patch.py`: `volume-iso` becomes the only xdelta; add `layout.json` (geometry + hashes) to the manifest; the player tool adds a `build-tracks` step (section 8). `tools/vcdiff.py`: `make(src, tgt, out, moves=layout_moves)` splits windows at moved-file boundaries.
* Diagnostics: `tools/discimage.py report` prints free space per track, largest free range, moved files with size, pinned files, the sectors beyond which the disc would overflow, and the estimated patch size (sum of changed + moved-only-if-not-aware).

### 9.4 Implementation notes / pitfalls found while reading the code
* `used_extents` already lists system area, volume descriptors, path tables, directories, files: reuse it as the occupancy map (the zero-content check in `plan_patches` is a belt-and-braces check that a free sector holds nothing the game might read; keep it).
* `Source.locate` and `write_track` assume `TRACK_LBA` and that track 5 is the last: parametrise.
* Directory record fields to copy from a sibling when adding a file: length byte, date (7 bytes), flags 0, volume sequence number 1 (both-endian), name length, `NAME.EXT;1`, pad byte for even name length. Directory sort order: byte-wise ASCII.
* Aliases: two records with the same extent and size are legal ISO9660 and read-only for the game; any patch stage that writes a file must treat all names of an alias group as one (the builder should refuse a patch that changes only one member of an alias group).
* Do not put anything into the 225 pregap sectors or past `max_lba`; do not shrink the volume size below the last used sector (keep `504150` while track 5 keeps its length, even if the tail is empty: it has no effect and keeps IP.BIN TOC and PVD identical).
* Keep 1ST_READ.BIN where it is (last file; anything placed after it forces track 5 to grow).
* Moving 1ST_READ.BIN or the first files is allowed by the loader (name based) but gives no benefit.

## 10. Test plan (all offline, no emulator)  (numbered for tracking)

**Properties (V, checked by `verify_disc()` after every build)**
V1 every Mode 1 sector of tracks 1, 3, 5 re-encodes to itself (EDC/ECC/header MSF = LBA + 150), except sectors that are all-zero raw in the source pregap.
V2 every extent (system area, VDs, path tables, directories, files) lies wholly inside one data track, outside the pregap, and below `max_lba`; no two extents overlap unless they are the same extent of an alias group.
V3 PVD volume space = last used LBA + 1 - 45000 (or the original 504150 when the tail is merely empty); IP.BIN lead-out FAD = end + 150; IP.BIN CRC (0x40..0x4F) unchanged; boot name still `1ST_READ.BIN`, TOC entries equal the geometry.
V4 two independent walks agree: directory-record traversal and path-table-driven traversal give the same set of directories, extents and parent numbers (the second reader is written from the ISO9660 spec, not from `discbuild._walk`).
V5 both-endian fields agree in every directory record; records sorted; no record crosses a sector; `.` and `..` correct; PT L/M equal byte-swapped; PT size in the PVD right.
V6 file count and names equal the spec (original names minus deletions plus additions).
V7 each file read back through the SECOND reader equals the expected bytes (sha1), all 1215+ files; sizes equal record sizes.
V8 gap sectors are zero and aliases really share bytes.
V9 track files have the exact expected length; GDI and CUE parse back to the geometry (and the generated CUE equals the original text when the geometry is the original).
V10 no file crosses 51342 / enters the pregap / exceeds the HD end.
V11 `layout.json` replays: applying its moves to the source ISO reproduces the target ISO.
V12 pinned files have unchanged LBA and bytes.

**Cases (T)**
T1 identity: empty spec -> all 5 tracks, cue, and the cooked ISO are byte-identical to the originals (sha1 equal to `tools/release.toml`); the re-serialised metadata equals the source bytes (directories, path tables, PVD) exactly.
T2 grow in place inside the last sector (+1..2047 B of a file whose size is not sector-aligned): only the record and the file's last sector change.
T3 grow across a sector boundary with a free neighbour absent -> relocation: file placed in the track 3 hole, old extent returns to the free list and is reused by the next mover (3 files, check best fit), V1-V12.
T4 big mover: a 6000-sector file fits the hole; a 6300-sector file raises `DiscFull` with a useful message; a file bigger than the hole but smaller than a vacated extent after another file moves out.
T5 shrink (a file smaller): in place, tail zero.
T6 dedupe: all 15 duplicate groups aliased -> 3726 sectors freed; a patch that changes only one alias member is rejected; changing both identically works and keeps the alias.
T7 stubs: DP tree stubbed (108 files, 5846 sectors), name still listed, size 2048.
T8 add a file into a directory with slack (FLOW_PRG) and into a full directory (EVENT/SSONG): the second relocates the directory, updates parent record, `.`/`..`, children `..` (EVENT has no subdirs; DPWWW has HELP: test it), both path tables.
T9 add a directory (e.g. `/EN`) at root level: path tables renumber, root grows if needed (30 records, 830 B free: fine), L and M tables stay one sector; plus a synthetic 120-directory run to force a 2-sector path table and verify PVD, root and directory LBAs shift consistently.
T10 overflow: a spec needing more than the free space -> error; `--allow-overflow` -> track 5 grows, lead-out and PVD size updated, a warning printed, and V2 reports exceeding 549150 as a WARNING instead of PASS.
T11 pin: BCAST.BIN, BINDUNIF.BIN, ENDING_L/R.P04 keep their LBAs in every case; a spec that tries to replace a pinned file with a larger one fails unless it is explicitly unpinned.
T12 raw round trip: the raw tracks written by the streaming path equal the raw tracks rebuilt from the cooked ISO by `build_tracks` (all sectors, sha1 of tracks 3 and 5).
T13 xdelta: make the cooked-ISO patch for T3 and the 10 percent overlay-growth case with the positional encoder and with the move table; assert size(move-aware) < 1.2 x (changed bytes) and size(positional) >= moved bytes; decode with `vcdiff.py` and with `xdelta3 -d -s` (installed at `C:/ProgramData/chocolatey/bin/xdelta3`); sha1 equals the target.
T14 stress: random choice of 200 files grown by random amounts, 20 seeds, run V1-V12 (each run about 80 s with streaming; cooked-only variant for speed).
T15 reader compatibility: `tools/gdrom.py` (parametrised) lists the new image; a minimal GDFS emulator (path table lookup by name, directory scan, handle = start/len/sectors) opens every file by name and reads the sector count the game would read; compare bytes.
T16 save path: nothing to test here (the disc layer does not touch saves); a regression test that IP.BIN bytes 0..0x4F and 0x60..0x70 stay unchanged.

## 11. Boot check list for the user  (needs Flycast / GDEMU; I did not run any of it)

Prepare: build with the rebuild mode into a new folder; keep the original dump next to it; use the `.gdi` first, then the `.cue`.
1. Flycast boots to the SEGA licence/IP screen and the game title screen (proves bootstrap + 1ST_READ by name even though files moved). Repeat with a build where 1ST_READ.BIN was forced to move (T-flag `--force-move 1ST_READ.BIN`) once.
2. New game, walk through team creation: touches BPINFO, FONT.BIN, SECFTEX0-2.ZAR in ATFIRST/ETC_DATA (shared extents when dedupe is on): names appear, no FILE OPEN ERROR / FILE SEEK ERROR / `illegal memory for fileread LARGER FILESIZE` text.
3. One match with the commentary on (BCAST.BIN streaming; the file is pinned and must not have moved). Watch for `Bcast Error !!` text and for silence.
4. One in-game week for each of the biggest grown overlays: MEETING, NEWS, TRAINING, DRAFT, EVENT (each loads by name from its new extent).
5. SOUND: music from a shared extent (the five 1,029,056-byte MLT duplicates) in at least two screens (ending, game over, victory).
6. Save and reload on a VMU image (disc layer should not matter: confirm the save screen works).
7. Check the Flycast log/console for ISO or GDROM errors (open the log file only; do not attach screenshots of the desktop).
8. GDEMU: copy the folder as `disc.gdi` + track files named by the GDI; boot; same steps 1-3. If the track sizes changed, confirm GDEMU shows the disc (no `invalid TOC`).
9. Only if overflow mode was ever used: it is likely to fail on real hardware; Flycast result decides whether the experiment is kept.
10. If anything fails: record which file name appears in the error text; the builder's `layout.json` says where that file moved from/to; revert exactly that file to its original extent (pin it) and rebuild.

## 12. Recommended order of work (benefit / risk)

(Status of each step after Stage 3: section 15 at the end of this file.)

1. `Geometry` + `verify_disc` + parametrised readers (V1-V12, T1): benefit = every later step is checkable, no behaviour change; risk none.
2. Capacity guard (`max_lba`, `DiscFull`) in `discbuild` today: benefit = stops silent emulator-only images; risk none.
3. `--dedupe` aliases (+3726 sectors) and best-fit allocator with vacated extents: benefit = 6431 -> 10,157 sectors of room, tiny code; risk low (aliases must stay identical; guard in the builder).
4. Metadata re-author (directories, path tables, add file / add directory): benefit = new data files (for example an extra text/code bank, `/EN/*.BIN`) and no 64-byte directory limits; risk low-medium (path table ordering is the classic bug: V4/V5 catch it).
5. Cooked-ISO canonical patch + move-aware encoder + player-side track rebuild: benefit = patch size stays proportional to edited text however much moves, one patch for BIN/CUE, GDI and ISO; risk medium (new player-side step: 109 s single-threaded, hash-gated; xdelta3 cross-check T13). Needed only once files really move; the current `gap` strategy with positional deltas is fine up to a few tens of MB.
6. Decide lever C (stub the Dream Passport tree, +12 MB) after checking whether the game reaches it: benefit = large; risk = a network menu entry that now fails; best decided by the user.
7. Lever D (shrink track 4) only if a hard need remains: shifts every track 5 LBA and the TOC; needs a CDDA-usage answer first (static: find the GD-ROM play command in the GDFS/sound code; or a Flycast run that logs CDDA play).
8. Overflow mode: keep as an experiment flag; test in Flycast and GDEMU (checklist item 9) before anyone relies on it.

## 13. UNKNOWN / not done

* No boot, no Flycast, no GDEMU test (hard rule).
* Whether GDFS searches a directory linearly or by binary search (keep records sorted to satisfy both); whether shared extents confuse any cache keyed by extent (the loader keys handles by name; test T15 + boot steps 2/5).
* Whether the Dream Passport tree is reachable from the game; whether track 4 is played.
* BCAST.BIN index location (in-band headers; the byte-offset table that selects voices was not found).
* Real behaviour of Flycast and GDEMU for images longer than 549150 sectors (section 6).
* `dirmax` semantics of the GDFS init (1024) are the standard-library reading, not traced to the compare instruction.
* Hash of this rebuilt disc is not claimed: no rebuild was run.

## 14. Scripts added (all read-only, `python -I -X utf8 tools/re/<name>`)

`dxp_layout.py` (files per directory, biggest files, gaps, directory table), `dxp_dirs.py` (PVD, path table, directory slack, IP.BIN TOC), `dxp_gapcheck.py` (free sectors are zero and valid), `dxp_dups.py` (sha1 duplicate groups and savings), `dxp_plan.py [pct]` (what-if capacity and movement), `dxp_lbascan.py` (negative scan for LBA/size/end constants over all files; output `build/dxp_lbascan.txt`), `dxp_scan1st.py` / `dxp_peek.py` / `dxp_peek16.py` / `dxp_ctx.py` / `dxp_find.py` (small image probes), `dxp_audio.py` (CDDA energy), `dxp_ipcrc.py` (IP.BIN CRC range), `dxp_bench.py` (sector encode speed). Ghidra work was done on a copy of the texinject project in the session scratchpad with the existing `tools/re/ghidra/Dec.java` (no new project files in the repo).

## 15. Status after Stage 3 (disc owner; details and proofs in docs/disc-layout.md "Stage 3 additions")

| # | Recommended step (section 12 / tests of section 10) | Status | Evidence / what is left |
|---|---|---|---|
| 1 | `Geometry` + `verify_disc` (V1-V12, T1) | DONE (writer geometry still fixed) | `tools/discbuild_geom.py`, `tools/verify_disc.py`. Geometry model reads gdi and cue, sheets of the default geometry equal the Redump cue and discbuild's gdi. Verifier covers G1/G2, V2-V5, V7, V9, free space; V1 on every sector with `--sectors all`; V6 (names) as "no file of the original is missing" + announced changes; V8 reported (free / stale), aliases checked; V10 inside V2; V11 (`layout.json`), V12 (pins) NOT done (no layout.json, no pin list). Two readers (records, path tables) plus a Gdfs model of the game's open path. 14 damage classes detected in `test_discbuild_dsc.py`. Left: parametrise the WRITER (`TRACK_LBA`) and `tools/gdrom.py` |
| 2 | Capacity guard (`max_lba`, `DiscFull`) | DONE | `plan_patches(max_lba=549150, allow_overflow=False)`; `build_patch` stops with exit 1; `--allow-overflow` = old behaviour + warning (T10 partly: no flag-less "overflow warning" in verify beyond V2 error) |
| 3 | `--dedupe` aliases + allocator with vacated extents | DONE, default off | `--dedupe-files on|off` (build_patch, discbuild CLI, `DiscSpec.dedupe`): 15 groups / 20 followers / 3726 sectors, free 6431 -> 10157; vacated extents merged and reused (7 x 1000-sector movers fit only with dedupe); one-sided patch un-shares, grown keeper moves once and followers follow (T6 as a build test). Best-fit allocation was NOT done (first fit as before, default output must not change); largest-first ordering NOT done. Game-side acceptance of shared extents: INFERRED, boot items 2 and 5 of section 11 still owed |
| 4 | Metadata re-author: add file / add directory, no 64-byte directory limit | DONE (add), not done (delete / rename / stub) | `DiscSpec.add_file/add_directory`, `build_patch --add-file`: sorted insertion, directory relocation (parent record, `.`, children `..`, PVD root record), both path tables regenerated (equal the original bytes when nothing changes), table relocation when it needs a second sector. T8 and T9 including a 100-directory run (path table 2524 bytes, root, EVENT, DPWWW moved) pass in one build |
| 5 | Cooked-ISO canonical patch + move-aware encoder + player-side track rebuild | NOT DONE | not in the disc owner's scope this stage (release owner: vcdiff / release.py) |
| 6 | Lever C: stub the Dream Passport tree | NOT DONE | content decision for the user |
| 7 | Lever D: shrink track 4 | NOT DONE | needs a CDDA-usage answer first |
| 8 | Overflow mode as an experiment flag | DONE (flag), UNPROVEN in an emulator | `--allow-overflow`; Flycast / GDEMU tests (section 11 item 9) not run |

Section 10 tests: T1 (identity; test 2 of `test_discbuild.py`, plus the `cmp` proof against the pre-stage-3 writer on the real standard patch set),
T2/T5 (in place; legacy test 3), T3/T4 (gap relocation, hole limit 6281/6282), T6, T8, T9, T10, T15 (Gdfs model opens every file by name) and the
verify damage cases are implemented; T7 (stubs), T11 (pin), T12 (raw round trip from the cooked ISO), T13 (xdelta), T14 (stress), T16 are not.
New open facts: the directory packing of EVENT and SSONG on the original disc is not the standard greedy packing (a repack of the unchanged records
differs in padding), so a directory that is re-serialised gets the standard packing (valid ISO9660); `Geometry.from_cue` needs the track files
next to the cue (sector counts come from file sizes).

## Status after stage 3 (docs, 2026-11-11)

Section 15 above is the status table of this study; `docs/expansion/status.md` has the cross-study table.  Disc work done since: capacity guard, `--dedupe-files`, `--add-file`, `verify_disc`; the xdelta release path (items 5 of section 12) is in `tools/release.py`, `tools/vcdiff.py` and `docs/xdelta-release.md` (the ISO-only patch with the move-aware encoder and the player-side raw rebuild exist, so item 5 of the table in section 15 is DONE although the table still says NOT DONE).
