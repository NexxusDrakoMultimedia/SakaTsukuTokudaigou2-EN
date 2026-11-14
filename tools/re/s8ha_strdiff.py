"""s8ha: differential layout of every English string of an overlay (as read from a built disc) through the REAL layout function, with the align cave
of that disc ON versus the same cave bytes with the `bra at_snap` hook removed (= align off).  A fast lazy memory is used (image + a small dict).
usage: s8ha_strdiff.py OVERLAY_FILE 1ST_READ_FILE DB_JSONL [W=20] [MAX=100000]"""
import json
import os
import re
import struct
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fontcheck as FC
import fontpatch as FP
import sh4sim

BASE = 0x8c2d0000
img = open(sys.argv[1], 'rb').read()
k = open(sys.argv[2], 'rb').read()
W = int(sys.argv[4]) if len(sys.argv) > 4 else 20
MAXN = int(sys.argv[5]) if len(sys.argv) > 5 else 100000


class Lazy(dict):
    def __init__(self, base, data):
        super().__init__()
        self.base, self.data = base, data

    def get(self, a, d=0):
        if a in self:
            return dict.__getitem__(self, a)
        o = a - self.base
        return self.data[o] if 0 <= o < len(self.data) else d


ct = FP.placement()
al = FP.align_address()
offb = bytearray(k)
bra_off = ct[0] - FP.IMG_BASE + FP.ADV_RET_OFF
assert offb[bra_off:bra_off + 4] != bytes.fromhex('0b000900')
offb[bra_off:bra_off + 4] = bytes.fromhex('0b000900')
OFFB = bytes(offb)
# the overlay on a disc is already hooked: locate the hook by its literal (the font cave entry)
lit = struct.pack('<I', ct[0])
hooks = [i for i in range(0, len(img) - 3, 4) if img[i:i + 4] == lit]
assert hooks, 'no hook'
hook = hooks[0] - 12
fe = img.rfind(FC.PROLOGUE, hook - 0x500, hook)
func, join = BASE + fe, BASE + hook + 0x1a


def run(codes, W, on):
    src = k if on else OFFB
    m = sh4sim.Machine()
    m.mem = Lazy(0x8c010000, src)
    # overlay image over the first-read image: a second lazy layer
    ov = Lazy(BASE, img)
    base_get = m.mem.get
    def get(a, d=0, _b=base_get, _o=ov):
        if a in m.mem:
            return dict.__getitem__(m.mem, a)
        o = a - BASE
        if 0 <= o < len(img):
            return img[o]
        return _b(a, d)
    m.mem.get = get
    win = 0x8D000000 - 0x4000
    arr = win + 0x800
    for i, c in enumerate(codes):
        m.wn(arr + 2 * i, c, 2)
    m.wn(win + 0x30, arr, 4)
    m.wn(win + 0x2c, len(codes), 2)
    m.wn(win + 0x22, len(codes), 2)
    m.wn(win + 0x3c, W, 1)
    m.wn(win + 0x3e, 24, 1)
    m.wn(win + 0x3f, 24, 1)
    m.wn(win + 0x45, 1, 1)
    m.wn(win + 0x4a, 20, 2)
    m.wn(win + 0x4c, 240, 2)
    m.wn(win + 56, 0x20, 4)
    m.R[4] = win
    m.R[15] = 0x8D000000 - 0x100
    m.PR = 0x8C000000
    m.native = [(BASE, BASE + len(img)), (ct[0], ct[0] + 0x100), (al, al + 0x100)]
    pens = []
    m.run(func, 0x8C000000, watch={join: lambda mm: pens.append((sh4sim.s32(mm.R[10]), sh4sim.s32(mm.R[8])))}, max_steps=3000000)
    return pens


def codes_of(s):
    return [0x2020 if ch == ' ' else (0x200A if ch == '\n' else 0x8000 | ord(ch)) for ch in s]


n = bad = diff = nrun = 0
for line in open(sys.argv[3], encoding='utf-8'):
    r = json.loads(line)
    en = r.get('en') or ''
    s = re.sub(r'<[^>]+>', '', en)
    s = re.sub(r'=[a-z]/', '', s).replace('@Y/', '').replace('@P/', '').replace('@', '').replace('$1', 'Kenji')
    s = s.replace('%2d', '12').replace('%d', '1234').replace('%s', 'Name').replace('%4d', '2026')
    if not s or re.search(r'[^\x20-\x7e\n]', s) or len(s) > 200:
        continue
    n += 1
    if n > MAXN:
        break
    codes = codes_of(s)
    try:
        a, b = run(codes, W, True), run(codes, W, False)
    except sh4sim.SimError as e:
        bad += 1
        print('SIMERROR', e, repr(s[:60]))
        continue
    if a != b:
        diff += 1
        hasrun = re.search(r'\S {2,}\S', s) is not None
        if not hasrun:
            print('DIFF without blank run:', repr(s[:80]))
print('strings %d, simerrors %d, differing %d' % (n, bad, diff))
