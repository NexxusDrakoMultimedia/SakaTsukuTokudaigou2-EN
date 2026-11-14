"""Static evidence for two repack/sharing assumptions, from the four existing RAM dumps:
  (1) the game never writes into string pools (needed for share=dup: identical strings share one copy),
  (2) the pointer words of strings are not modified at run time (needed for every repack: we rewrite them in the file).
For every (dump, overlay) pair where the overlay is known to be resident at its documented base, compare the RAM bytes with the
file image over (a) all pool ranges of movable strings, (b) all fixed string regions, (c) all pointer words of strings.
  python -I -X utf8 tools/re/capacity/synth/poolwrite.py [DUMP SOURCE BASEHEX [IMAGEFILE]]   (no args: the 8 built-in pairs)
Caveat: a snapshot proves nothing about states that were not dumped (match, season, training, news...)."""
import sys, os, importlib.util, struct
here = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(here, '..', '..', '..', '..'))
os.chdir(ROOT); sys.path.insert(0, 'tools')
import textdb as T, textrepack as R

PAIRS = [   # (dump, source, load address)   bases verified in docs/memory-map.md / task statement
    ('ram_2400.bin', 'FLOW_PRG/TITLE.BIN', 0x8c6d0000),
    ('ram_5400.bin', 'FLOW_PRG/TITLE.BIN', 0x8c6d0000),
    ('live1_ram.bin', 'FLOW_PRG/N_ENTRY.BIN', 0x8c8d0000),
    ('live3_ram.bin', 'FLOW_PRG/CLUBEDIT.BIN', 0x8c2d0000),
    ('ram_2400.bin', 'FLOW_PRG/HELP.BIN', 0x8cb60000),
    ('live3_ram.bin', 'FLOW_PRG/HELP.BIN', 0x8cb60000),
    ('ram_2400.bin', 'FLOW_PRG/FACEMDUL.BIN', 0x8cba0000),
    ('live3_ram.bin', 'FLOW_PRG/FACEMDUL.BIN', 0x8cba0000),
]
IMGFILE = sys.argv[4] if len(sys.argv) == 5 else None
if len(sys.argv) in (4, 5):      # poolwrite.py DUMP SOURCE BASEHEX  (DUMP = file name under build/emu/, e.g. c1.bin)
    PAIRS = [(sys.argv[1], sys.argv[2], int(sys.argv[3], 16))]
cache = {}
for dump, source, base in PAIRS:
    if dump not in cache:
        cache[dump] = open(os.path.join('build', 'emu', dump), 'rb').read()
    ram = cache[dump]
    img = T.load_image(source)
    assert img.base == base, (source, hex(img.base), hex(base))
    r = ram[base - 0x8c000000: base - 0x8c000000 + img.size]
    strs, ptrs, _ = T.extract_image(img)
    data = open(IMGFILE, 'rb').read() if IMGFILE else img.data     # compare against a patched build instead of the original
    pools, where = R.find_pools(strs)
    pool_b = pool_diff = 0
    for p in pools:
        a = data[p.a:p.z]
        b = r[p.a:p.z]
        pool_b += len(a)
        pool_diff += sum(1 for x, y in zip(a, b) if x != y)
    fix_b = fix_diff = 0
    for s in strs:
        if not R.is_movable(s):
            a = data[s.off:s.off + s.max_bytes]; b = r[s.off:s.off + s.max_bytes]
            fix_b += len(a); fix_diff += sum(1 for x, y in zip(a, b) if x != y)
    words = sorted({w for s in strs for w in s.refs})
    w_diff = sum(1 for w in words if data[w:w + 4] != r[w:w + 4])
    whole = sum(1 for x, y in zip(data, r) if x != y)
    print('%-14s %-22s pool bytes %7d differ %5d | fixed-string bytes %6d differ %4d | pointer words %5d differ %4d | whole image %d of %d bytes differ' % (
        dump, source, pool_b, pool_diff, fix_b, fix_diff, len(words), w_diff, whole, img.size))
