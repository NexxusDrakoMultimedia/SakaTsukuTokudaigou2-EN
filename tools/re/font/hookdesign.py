"""Concrete (UNTESTED, static) in-place patch for layout variant A: builds the replacement words for the two hook sites,
applies them to an in-memory copy of an overlay and prints a before/after disassembly with a self-check of every
branch/pool displacement.  Nothing is written to disk.
  python -I -X utf8 hookdesign.py [OVERLAY.BIN]      (default MEETING.BIN)
Sites (offsets from the layout function entry F, see hooksites.tsv):
  WRAP  F+0xa0 .. F+0xe4  (34 words)   units based wrap test      -> call WRAPFN(code, obj, penx) ; wrap action kept
  ADV   F+0x1f6 .. F+0x216 (16 words)  half/full advance (+units) -> call ADVFN(code, obj) -> r0 = px advance
WRAPFN/ADVFN addresses are placeholders (in 1ST_READ pre-BSS gap, see docs/trans-bank.md s2.4)."""
import struct, sys, os, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sh4dis import Image, dis, load_overlay

ADVFN = 0x8c13c000      # placeholder
WRAPFN = 0x8c13c100     # placeholder
W = lambda x: struct.pack('<H', x & 0xFFFF)
L = lambda x: struct.pack('<I', x)

def site(name):
    for r in csv.DictReader(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hooksites.tsv')), delimiter='\t'):
        if r['overlay'].upper() == name.upper() and r['variant'] == 'A':
            return {k: (int(v, 16) if v.startswith('0x') else v) for k, v in r.items()}
    raise KeyError(name)

def bra(a, t): return 0xA000 | (((t - (a + 4)) >> 1) & 0xFFF)
def bt(a, t):  return 0x8900 | (((t - (a + 4)) >> 1) & 0xFF)
def movl_pc(a, n, pool): d, rem = divmod(pool - (((a) & ~3) + 4), 4); assert rem == 0 and 0 <= d < 256, (hex(a), hex(pool)); return 0xD000 | (n << 8) | d

def build(s):
    """returns dict addr -> bytes for both blocks"""
    out = {}
    # ---- ADV block: 0x..48a .. 0x..4aa  (32 bytes) ----
    a0 = s['adv_ext']; nxt = s['loop_next']
    assert nxt - a0 == 32
    a = a0; w = []
    w.append(0x6CCD)                                        # extu.w r12,r12      (kept: code, 0x8000 for blank)
    w.append(0x64C3)                                        # mov r12,r4
    pool = a0 + 0x16                                        # 4-aligned pool inside the block (checked below)
    assert pool % 4 == 0
    w.append(movl_pc(a0 + 4, 3, pool))                      # mov.l @(pool),r3
    w.append(0x430B)                                        # jsr @r3
    w.append(0x65E3)                                        # mov r14,r5          (delay slot: window object)
    w.append(0x3A0C)                                        # add r0,r10          pen x += returned advance
    w.append(bra(a0 + 12, nxt))                             # bra loop_next
    w.append(0x7B01)                                        # add #1,r11          (delay) units++  (kept so unpatched wrap still works)
    while a0 + 2 * len(w) < pool: w.append(0x0009)          # nop
    blk = b''.join(W(x) for x in w) + L(ADVFN)
    while len(blk) < 32: blk += W(0x0009)
    assert len(blk) == 32
    out[a0] = blk
    # ---- WRAP block: wrap_lo .. draw_start (68 bytes) ----
    b0 = s['wrap_lo']; end = s['draw_start']
    assert end - b0 == 0x44
    w = []
    w.append(0x64CD)                                        # extu.w r12,r4        code
    w.append(0x65E3)                                        # mov r14,r5           obj
    pool2 = b0 + 0x1c                                       # 4-aligned
    assert pool2 % 4 == 0
    w.append(movl_pc(b0 + 4, 3, pool2))                     # mov.l @(pool2),r3
    w.append(0x430B)                                        # jsr @r3
    w.append(0x66A3)                                        # mov r10,r6           (delay) pen x
    w.append(0x2008)                                        # tst r0,r0
    w.append(bt(b0 + 12, end))                              # bt draw_start        (r0 == 0: no wrap)
    w.append(0xE03F)                                        # mov #63,r0           wrap action (unchanged from the original, 0x8c2de34a..)
    w.append(0x02EC)                                        # mov.b @(r0,r14),r2   line height
    w.append(0xE04A)                                        # mov #74,r0
    w.append(0x0AED)                                        # mov.w @(r0,r14),r10  x = x origin
    w.append(0x382C)                                        # add r2,r8            y += line height
    w.append(bra(b0 + 24, end))                             # bra draw_start
    w.append(0x6BD3)                                        # mov r13,r11          (delay) units = 0
    assert b0 + 2 * len(w) <= pool2, (hex(b0 + 2 * len(w)), hex(pool2))
    while b0 + 2 * len(w) < pool2: w.append(0x0009)
    blk = b''.join(W(x) for x in w) + L(WRAPFN)
    while len(blk) < 0x44: blk += W(0x0009)
    out[b0] = blk
    return out

if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'MEETING.BIN'
    img = load_overlay(name); s = site(name)
    patched = bytearray(img.d)
    for a, b in build(s).items():
        patched[a - img.base:a - img.base + len(b)] = b
    new = Image(bytes(patched), img.base)
    for title, lo, hi in (('WRAP', s['wrap_lo'], s['draw_start']), ('ADV', s['adv_ext'], s['loop_next'])):
        print('==', title, 'before / after  (', name, ')')
        old = img.listing(lo, hi); nw = new.listing(lo, hi)
        for i in range(max(len(old), len(nw))):
            print('%-60s | %s' % (old[i][:58] if i < len(old) else '', nw[i][:70] if i < len(nw) else ''))
    # sanity: bytes outside the two blocks are untouched
    diff = [i for i in range(len(img.d)) if img.d[i] != patched[i]]
    lo = min(s['wrap_lo'], s['adv_ext']) - img.base
    print('changed bytes:', len(diff), 'range', hex(img.base + diff[0]), '..', hex(img.base + diff[-1]))
