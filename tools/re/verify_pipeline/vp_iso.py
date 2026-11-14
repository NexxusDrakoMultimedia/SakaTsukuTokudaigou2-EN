"""Independent verifier (verify_pipeline agent).  Shares NO code with tools/discbuild.py or tools/gdrom.py.
Usage: python -I -X utf8 vp_iso.py <orig_prefix> <new_prefix> [--ecc-sample N]
 own ISO9660 walker, own EDC/ECC (validated against the ORIGINAL disc's real sectors), sector diff + attribution.
"""
import sys, os, struct, collections, random
SS = 2352
TRK = {1: 0, 2: 2380, 3: 45000, 4: 51342, 5: 56665}
DATA = (1, 3, 5)
SYNC = b'\x00' + b'\xff' * 10 + b'\x00'

_t = []
for i in range(256):
    c = i
    for _ in range(8):
        c = ((c >> 1) ^ 0xD8018001) if c & 1 else (c >> 1)
    _t.append(c)
def edc(b):
    c = 0
    for x in b:
        c = (c >> 8) ^ _t[(c ^ x) & 0xFF]
    return c
F = [((i << 1) ^ (0x11D if i & 0x80 else 0)) & 0xFF for i in range(256)]
B = [0] * 256
for i in range(256):
    B[i ^ F[i]] = i
def _blk(src, maj, mnr, mult, inc, dest):
    size = maj * mnr
    for major in range(maj):
        idx = (major >> 1) * mult + (major & 1)
        a = b = 0
        for _ in range(mnr):
            t = src[idx]
            idx += inc
            if idx >= size: idx -= size
            a ^= t; b ^= t
            a = F[a]
        a = B[F[a] ^ b]
        dest[major] = a
        dest[major + maj] = a ^ b
def ecc(sec):
    buf = bytearray(sec[12:12 + 2064 + 8 + 172 + 104])
    # P over header+user+edc+zero (2064+... ) : bytes 12..2075 -> 2064 bytes
    src = bytes(buf[0:2064])
    p = bytearray(172); _blk(src, 86, 24, 2, 86, p)
    q = bytearray(104); _blk(src + bytes(p), 52, 43, 86, 88, q)
    return bytes(p), bytes(q)
def msf(lba):
    m, r = divmod(lba + 150, 4500); s, f = divmod(r, 75)
    bcd = lambda v: ((v // 10) << 4) | (v % 10)
    return bytes((bcd(m), bcd(s), bcd(f), 1))
def check_sector(lba, raw):
    """list of problems for a Mode1 sector at absolute lba (empty = canonical)"""
    pr = []
    if raw[:12] != SYNC: pr.append('sync')
    if raw[12:16] != msf(lba): pr.append('header %s != %s' % (raw[12:16].hex(), msf(lba).hex()))
    if struct.unpack_from('<I', raw, 2064)[0] != edc(raw[:2064]): pr.append('edc')
    if raw[2068:2076] != bytes(8): pr.append('zero8')
    p, q = ecc(raw)
    if raw[2076:2248] != p: pr.append('P')
    if raw[2248:2352] != q: pr.append('Q')
    return pr

class Disc:
    def __init__(self, prefix):
        self.f = {}; self.n = {}
        for t in TRK:
            p = prefix + ' (Track %d).bin' % t
            self.f[t] = open(p, 'rb'); self.n[t] = os.path.getsize(p) // SS
            assert os.path.getsize(p) % SS == 0, p
    def loc(self, lba):
        for t in (5, 4, 3, 2, 1):
            if TRK[t] <= lba < TRK[t] + self.n[t]: return t, lba - TRK[t]
        raise IndexError(lba)
    def raw(self, lba):
        t, i = self.loc(lba); self.f[t].seek(i * SS); return self.f[t].read(SS)
    def user(self, lba, nbytes):
        out = b''.join(self.raw(lba + i)[16:2064] for i in range((nbytes + 2047) // 2048))
        return out[:nbytes]
    @property
    def end(self): return TRK[5] + self.n[5]

def dirents(d, lba, size, path):
    data = d.user(lba, size); pos = 0; out = []
    while pos < size:
        l = data[pos]
        if l == 0:
            pos = (pos // 2048 + 1) * 2048; continue
        rec = data[pos:pos + l]
        el, = struct.unpack_from('<I', rec, 2); eb, = struct.unpack_from('>I', rec, 6)
        sl, = struct.unpack_from('<I', rec, 10); sb, = struct.unpack_from('>I', rec, 14)
        fl = rec[25]; nl = rec[32]; nm = rec[33:33 + nl]
        out.append(dict(lba=el, lba_be=eb, size=sl, size_be=sb, flags=fl, name=nm, recpos=(lba + pos // 2048, pos % 2048), parent=path))
        pos += l
    return out
def walk(d):
    pvd = d.user(45016, 2048)
    assert pvd[0] == 1 and pvd[1:6] == b'CD001', 'no PVD'
    rl, = struct.unpack_from('<I', pvd, 158); rs, = struct.unpack_from('<I', pvd, 166)
    files = {}; dirs = {}; issues = []
    stack = [(rl, rs, '')]; seen = set()
    while stack:
        lba, size, path = stack.pop()
        if lba in seen: continue
        seen.add(lba); dirs[path or '/'] = (lba, size)
        for e in dirents(d, lba, size, path):
            if e['name'] in (b'\x00', b'\x01'): continue
            nm = e['name'].decode('ascii').split(';')[0]
            p = path + '/' + nm
            if e['lba'] != e['lba_be']: issues.append('lba LE!=BE ' + p)
            if e['size'] != e['size_be']: issues.append('size LE!=BE ' + p)
            if e['flags'] & 2: stack.append((e['lba'], e['size'], p))
            else: files[p] = e
    return pvd, rl, rs, files, dirs, issues
