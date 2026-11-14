"""s8ha: run the REAL layout function of the overlay found in a Flycast RAM dump on every tsString window object of the dump, with and without
the align cave (the cave is installed into the simulated memory, the dump itself is not changed), and compare the pen traces.
Reports step-limit hits / simulator errors and windows whose traces differ.
usage: s8ha_ramwin.py DUMP [LITERAL_ADDR_OF_THE_HOOK=first hit]   (reads the window list with the same filter as s8ha_ramscan.py)"""
import os
import struct
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fontcheck as FC
import fontpatch as FP
import sh4sim

dump = open(sys.argv[1], 'rb').read()
B = 0x8c000000


class Lazy(dict):
    """byte memory backed by the dump; writes go to the dict"""
    def get(self, a, d=0):
        if a in self:
            return dict.__getitem__(self, a)
        o = a - B
        return dump[o] if 0 <= o < len(dump) else d


def u8(a): return dump[a - B]
def u16(a): return struct.unpack_from('<H', dump, a - B)[0]
def u32(a): return struct.unpack_from('<I', dump, a - B)[0]


lit = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x8c2d5768
hook = lit - 12
fe = dump.rfind(FC.PROLOGUE, hook - 0x500 - B, hook - B)
func = B + fe
join = hook + 0x1a
print('layout function %08x hook %08x join %08x' % (func, hook, join))
ct = FP.placement()
al = FP.align_address()
tbl = bytes(dump[ct[1] - B:ct[1] - B + 256])
ex_on = [(ct[0], FP.cave_bytes(ct, False, al)), (al, FP.align_bytes(al, ct[1]))]
ex_off = [(ct[0], FP.cave_bytes(ct, False, None))]
cands = []
for a in range(0x8c300000, 0x8d000000 - 0x100, 4):
    p = u32(a + 0x30)
    if not (0x8c000000 <= p < 0x8d000000) or p & 1:
        continue
    cnt22 = u16(a + 0x22)
    idx = u16(a + 0x2c)
    W, R, adv, lh = u8(a + 0x3c), u8(a + 0x3d), u8(a + 0x3e), u8(a + 0x3f)
    if 1 <= W <= 60 and 1 <= R <= 20 and adv in (24, 16, 32, 10, 12, 20, 48) and 8 <= lh <= 60 and idx <= cnt22 <= 4000 and u8(a + 0x46) < 4:
        cands.append(a)
print(len(cands), 'windows')


def run(win, on, idx=None):
    m = sh4sim.Machine()
    m.mem = Lazy()
    for a, d in (ex_on if on else ex_off):
        m.load(a, d)
    m.native = [(func - 0x100, func + 0x4000), (ct[0], ct[0] + 0x100), (al, al + 0x100)]
    if idx is not None:
        m.wn(win + 0x2c, idx, 2)
    m.R[4] = win
    m.R[15] = 0x8cff0000
    m.PR = 0x8c000000
    pens = []
    m.run(func, 0x8c000000, watch={join: lambda mm: pens.append((sh4sim.s32(mm.R[10]), sh4sim.s32(mm.R[8])))}, max_steps=3000000)
    return pens


bad = diff = 0
for w in cands:
    for idx in (None, 0):
        try:
            a = run(w, True, idx)
            b = run(w, False, idx)
        except sh4sim.SimError as e:
            bad += 1
            print('SIMERROR win %08x idx=%s: %s' % (w, idx, e))
            continue
        if a != b:
            diff += 1
            print('DIFF win %08x idx=%s n=%d cnt=%d: %s ... vs %s' % (w, idx, u16(w + 0x22), u16(w + 0x2c), a[:6], b[:6]))
print('windows %d, simerrors %d, differing %d' % (len(cands), bad, diff))
