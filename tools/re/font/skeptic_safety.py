"""Skeptic check of the live test tools/emu/fonttest.lua (safety side).  Reads only; writes nothing but stdout.

    python -I -X utf8 tools/re/font/skeptic_safety.py

Checks
  1  embedded cave / table / glyph / variant bytes in the lua == what tools/fontpatch.py generates
  2  the cave executed in tools/sh4sim.py with the lua's own CAVE_HEX: TABLE and FIXED ('control') behaviour for the blank cell 0x8000
  3  CAVE/TABLE range [0x8c299800,0x8c299a00): zero in all 5 dumps, where the nearest data is, who points there (all dumps, 1ST_READ, overlays)
  4  slot / heap geometry of every dump: the range is outside every slot and heap; the glyph block is inside the loaded root FONT.BIN
  5  the lua's arena scan replayed on every dump: how many sites, in which slot, image area or heap (used/free) block
"""
import glob
import os
import re
import struct
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import fontpatch as FP  # noqa: E402
import memmap as MM  # noqa: E402
import sh4sim  # noqa: E402

BASE = 0x8C000000
lua = open(os.path.join(ROOT, 'tools', 'emu', 'fonttest.lua'), encoding='utf8').read()


def grab(name):
    return re.search(r'local %s = "([0-9a-f]+)"' % name, lua).group(1)


CAVE_ADDR, TABLE_ADDR = [int(x, 16) for x in re.search(r'local CAVE, TABLE = (0x[0-9A-Fa-f]+), (0x[0-9A-Fa-f]+)', lua).groups()]
CAVE = bytes.fromhex(grab('CAVE_HEX'))
TABLE = bytes.fromhex(grab('TABLE_HEX'))
FIXED = bytes.fromhex(grab('FIXED_HEX'))
print('lua CAVE %#x (%d B) TABLE %#x (%d B)' % (CAVE_ADDR, len(CAVE), TABLE_ADDR, len(TABLE)))

# ------------------------------------------------------------------ 1
ct = FP.placement()
print('1) cave bytes == fontpatch.cave_bytes:', CAVE == FP.cave_bytes(ct), '; placement', [hex(x) for x in ct])
tbl_py = None
try:
    import font as F
    fnt = FP.read_extracted('FONT.BIN')
    new, tbl_py = FP.proportional_font(fnt, F.Font(fnt).half())
    print('   lua TABLE_HEX == fontpatch table:', bytes(tbl_py) == TABLE)
except Exception as e:  # pragma: no cover
    print('   (could not regenerate table: %s)' % e)
variants = {}
for v, m in re.findall(r'(\w) = \{(h1_old=.*?)\}', lua):
    variants[v] = dict(re.findall(r'(\w+)="([0-9a-f]+)"', m))
    variants[v]['back'] = int(re.search(r'h2_back=(\d+)', m).group(1))
for v, t in variants.items():
    print('   variant %s: h1 %d B, h2_old %d B, h2_new %d B, h2_back %d' % (v, len(t['h1_old']) // 2, len(t['h2_old']) // 2, len(t['h2_new']) // 2, t['back']))


# ------------------------------------------------------------------ 2
def run_cave(tbl, code, entry_off=0, A=24):
    m = sh4sim.Machine()
    m.load(CAVE_ADDR, CAVE)
    m.load(TABLE_ADDR, tbl)
    win = 0x8D000000 - 0x4000
    m.wn(win + 62, A & 0xFF, 1)
    m.R[14] = win
    m.R[4] = code
    m.PR = 0x8C000000
    m.native = [(CAVE_ADDR, CAVE_ADDR + len(CAVE))]
    m.run(CAVE_ADDR + entry_off, 0x8C000000, max_steps=1000)
    return sh4sim.s32(m.R[0])


print('2) cave executed (entry A, window advance 24):')
for name, tb in (('TABLE', TABLE), ('FIXED', FIXED)):
    print('   %-5s blank cell 0x8000 -> %2d px | 0x8020 -> %2d | "a" 0x8061 -> %2d | "i" 0x8069 -> %2d | "W" 0x8057 -> %2d | digit "1" 0x8031 -> %2d | katakana 0x80b1 -> %2d' % (
        (name,) + tuple(run_cave(tb, c) for c in (0x8000, 0x8020, 0x8061, 0x8069, 0x8057, 0x8031, 0x80B1))))
print('   original game (A>>1) for every half-width code: 12 px')
print('   FIXED table entries that differ from 12:', [(i, FIXED[i]) for i in range(256) if FIXED[i] != 12])

# ------------------------------------------------------------------ 3
dumps = {}
for n in ('ram_2400', 'ram_5400', 'live1_ram', 'live3_ram', 't1_ram'):
    dumps[n] = open(os.path.join(ROOT, 'build', 'emu', n + '.bin'), 'rb').read()
lo, hi = CAVE_ADDR - BASE, TABLE_ADDR + 256 - BASE
print('3) range [%#x,%#x) zero in dumps:' % (CAVE_ADDR, TABLE_ADDR + 256))
for n, d in dumps.items():
    seg = d[lo:hi]
    # nearest nonzero byte before / after
    b = d[:lo].rstrip(b'\0')
    a = d[hi:hi + 0x20000]
    na = len(a) - len(a.lstrip(b'\0'))
    print('   %-10s nonzero bytes in range: %d | last nonzero byte below: %#x | first nonzero byte above: %#x' % (
        n, len(seg) - seg.count(0), BASE + len(b) - 1, BASE + hi + na if na < len(a) else -1))
fr = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
fo = CAVE_ADDR - 0x8C010000
print('   1ST_READ.BIN file size %d (0x%x); file bytes at [%#x,+0x300) nonzero: %d; file ends at %#x' % (
    len(fr), len(fr), CAVE_ADDR, 0x300 - fr[fo:fo + 0x300].count(0), 0x8C010000 + len(fr)))

# pointer scan: any aligned word in any dump or file that points into [0x8c299400, 0x8c29a000) in any alias
LOP, HIP = 0x0C299400, 0x0C29A000
print('   words (aligned) pointing into [0x8c299400,0x8c29a000) in cached/uncached/physical alias:')
for n, d in dumps.items():
    arr = np.frombuffer(d, dtype='<u4')
    m = arr & np.uint32(0x1FFFFFFF)
    idx = np.nonzero((m >= LOP) & (m < HIP) & (arr != 0))[0]
    print('     dump %-10s %d hits %s' % (n, len(idx), ['%#x:%#x' % (BASE + int(i) * 4, int(arr[i])) for i in idx[:6]]))
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', '**', '*.BIN'), recursive=True))
hits = 0
for f in files:
    d = open(f, 'rb').read()
    d = d[:len(d) // 4 * 4]
    arr = np.frombuffer(d, dtype='<u4')
    m = arr & np.uint32(0x1FFFFFFF)
    idx = np.nonzero((m >= LOP) & (m < HIP) & (arr != 0))[0]
    if len(idx):
        hits += len(idx)
        print('     file', os.path.relpath(f, ROOT), len(idx), ['%#x:%#x' % (int(i) * 4, int(arr[i])) for i in idx[:5]])
print('   total file hits over %d .BIN files: %d' % (len(files), hits))

# ------------------------------------------------------------------ 4
print('4) slots / heaps:')
HALF_BASE = int(re.search(r'local HALF_BASE = (0x[0-9A-Fa-f]+)', lua).group(1), 16)
for n, d in dumps.items():
    sl = MM.walk_slots(d)
    ext = [(s['base'], s['base'] + s['size'], s['index']) for s in sl if s['size']]
    inside = [e for e in ext if e[0] <= CAVE_ADDR < e[1]]
    lowest = min(e[0] for e in ext) if ext else 0
    bad = [s['index'] for s in sl if s['bad']]
    print('   %-10s slots with size: %d, lowest slot base %#x, cave inside a slot: %s, heap chains with errors: %s' % (n, len(ext), lowest, bool(inside), bad))
fb = HALF_BASE
print('   glyph block %#x..%#x lies in the loaded root FONT.BIN image [0x8cd5c000, 0x8cd5c000+663324=%#x)' % (fb, fb + 23040, 0x8CD5C000 + 663324))

# ------------------------------------------------------------------ 5
ARENA_LO, ARENA_HI = 0x8C2D0000, 0x8CD5C000
wA = struct.unpack('<I', bytes.fromhex(variants['A']['h1_old'])[:4])[0]
wB = struct.unpack('<I', bytes.fromhex(variants['B']['h1_old'])[:4])[0]
wAn = struct.unpack('<I', bytes.fromhex(variants['A']['h1_new'])[:4])[0]
print('5) replay of scan_arena on the dumps (first word match then 16 B + H2 old/new):')
for n, d in dumps.items():
    arr = np.frombuffer(d, dtype='<u4')
    a0, a1 = (ARENA_LO - BASE) >> 2, (ARENA_HI - BASE - 16) >> 2
    seg = arr[a0:a1]
    cand = np.nonzero((seg == wA) | (seg == wB) | (seg == wAn))[0]
    sites = []
    for c in cand:
        a = ARENA_LO + int(c) * 4
        s = d[a - BASE:a - BASE + 16]
        for v, t in variants.items():
            old, new = bytes.fromhex(t['h1_old']), bytes.fromhex(t['h1_new'])
            if s == old or s == new:
                h2 = a - t['back']
                o2, n2 = bytes.fromhex(t['h2_old']), bytes.fromhex(t['h2_new'])
                c2 = d[h2 - BASE:h2 - BASE + len(o2)]
                if c2 == o2 or c2 == n2:
                    sites.append((v, a, h2, 'old' if s == old else 'new'))
    sl = MM.walk_slots(d)
    cls = {}
    rows = []
    for v, a, h2, st in sites:
        where = 'no slot'
        for s in sl:
            if s['size'] and s['base'] <= a < s['base'] + s['size']:
                if s['heap_size'] and s['heap_start'] <= a < s['end']:
                    blk = [b for b in s['blocks'] if b[0] <= a < b[0] + b[1]]
                    where = 'slot%d HEAP %s' % (s['index'], 'used' if blk and blk[0][2] else 'free')
                else:
                    where = 'slot%d image' % s['index']
        cls[where] = cls.get(where, 0) + 1
        rows.append((v, hex(a), where, st))
    print('   %-10s %d sites  %s' % (n, len(sites), cls))
    for r in rows[:6]:
        print('        ', r)
    # does a site's patched span touch a malloc block header?  check the 16 B and H2 span against block starts
    heads = set()
    for s in sl:
        for b in s['blocks']:
            heads.add(b[0])
    clash = [hex(a) for v, a, h2, st in sites for t in [variants[v]] for x in heads if h2 <= x < a + 16]
    print('        patched spans containing a malloc block header:', clash[:5])
