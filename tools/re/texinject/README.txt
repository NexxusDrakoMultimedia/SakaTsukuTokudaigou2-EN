Evidence for docs/texture-injection.md.  Everything runs with  python -I -X utf8 <script>  from the repo root; nothing writes
outside tools/re/texinject/ and build/.  Ghidra: project copy $GHIDRA_PROJECTS\ghproj_texinject (copy of ghproj),
SuperH4:LE:32, base 0x8c010000, headless, -readOnly.

Ghidra
  run.ps1 <out> <addr|range:lo-hi|ref:addr>...   decompile (Dec.java);   dis.ps1 <out> lo-hi ...   disassemble (Dis.java)
  t1.txt  ZSARC lookup wrappers / FUN_8c15a942 (texture list from a TBD in memory)
  t2.txt  PVRT/GBIX chunk parsers (file based: FUN_8c0266e8/...; in memory: FUN_8c029a90) + descriptor init FUN_8c02985c/6a
  t3.txt  FUN_8c0a6024 (texture create from descriptor: calls FUN_8c029a90 and takes fmt/dt/w/h/GBIX from the PVR header)
  t4.txt, t5.txt  zs jump-table users, file read FUN_8c15eede + FUN_8c15f0f4 (size check against the destination block)
  t6.txt  FLOW script interpreter FUN_8c15cffc (module / texture opcodes);  t7.txt  FLOW CRC opcode FUN_8c1648f0
  t8.txt  GDFS wrappers (file size = handle + 0xc)
  d_tbd.txt  disassembly of FUN_8c15a776 (TBD loader), the proof of the flag-bit mapping
  (older, reused: tools/re/ghidra/d2.txt = FUN_8c15a45a ZSARC walker, FUN_8c15a1cc header, FUN_8c15a776; d3.txt decoders)
Helpers: litpool.py (literal pool words), fnstarts.py (SH-4 prologues), strs.py (strings), findlit.py

Data analysis
  census.py -> census.tsv       texture-bearing files by container kind
  analyze_tbd.py                TBD alignment / padding / slack statistics over the disc
  analyze_pvr.py                PVR member structure (GBIX len 8, no trailing bytes, payload size formula)
  trailing.py                   whole-file TBDs that have data after the last record (KENPIC.BIN, SP_DATA.DAT, EVENTBG.DAT)
  scan_pvr.py                   real GBIX+PVRT images outside PVR files (all inside ZSARC members)
  hardcoded_sizes.py, lbahits.py  does any image hard-code a file size / LBA?  (only coincidences)
  ovl_tbl_ptrs.py               absolute pointers to the TBD tables embedded in overlays (52 of 67)
  why_nogrow.py                 why a ZSARC container is not growable
  cmp_compress.py, opt_timing.py  greedy vs original vs optimal-parse encoder
  fitstats.py -> fitstats.txt   unchanged compressed textures re-encoded into their original slot (optimal parse: 100 %)
  sweep.py -> sweep.txt         no-op + exact-length modified injection on every texture-bearing file
Whole-disc texture index: python -I -X utf8 tools/texinject.py index   (-> build/texindex.tsv)
