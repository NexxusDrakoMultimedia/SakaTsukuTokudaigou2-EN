"""Execute HOMETOWN.BIN's club-name composer (file 0x1072a, 0x8c2e072a) in the SH-4 simulator, original and patched.

    python -I -X utf8 tools/re/hnm/hnm_sim_club.py [IMAGE]

The composer calls town_short (0x8c2e0648) / pref_short (0x8c2e06b0) and the 1ST_READ sprintf (0x8c014d80, hooked here: only %s),
strlen (0x8c014de4) runs natively.  Without IMAGE the extracted overlay is used and a few synthetic English strings are written
into the 12-byte slots of the Japanese ones (Kagoshima city / prefecture, Izu Islands, the pool word Mythos / Shadows).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sh4sim  # noqa: E402

BASE = 0x8c2d0000
COMPOSER = 0x8c2e072a
STRLEN = (0x8c014de4, 0x8c014df2)
SPRINTF = 0x8c014d80
TOWN_TBL = 0x43854          # 1-based pointer table (word k at +4*k)
PREF_TBL = 0x42200          # 0-based
POOL_TBL = 0x422c8          # 0-based


class Machine(sh4sim.Machine):
    """tools/sh4sim.py has no bsr (0xBxxx); add it (PR = pc + 4, delayed call)."""

    def exec_op(self, op, pc):
        if op >> 12 == 0xB:
            disp = op & 0xFFF
            if disp & 0x800:
                disp -= 0x1000
            self.PR = pc + 4
            return ('call', pc + 4 + disp * 2)
        return super().exec_op(op, pc)


def cstr_at(m, a):
    out = bytearray()
    while True:
        b = m.rb(a + len(out))
        if b == 0:
            return bytes(out)
        out.append(b)


def compose(image, first, town, pref, pool, mode):
    m = Machine()
    m.load(0x8c010000, first)
    m.load(BASE, image)
    m.native = [STRLEN, (BASE, BASE + len(image))]

    def sprintf(mm):
        sp = mm.R[15]
        fmt = cstr_at(mm, mm.rn(sp, 4))
        args = [mm.rn(sp + 4 + 4 * i, 4) for i in range(4)]
        res = bytearray()
        k = 0
        i = 0
        while i < len(fmt):
            if fmt[i:i + 2] == b'%s':
                res += cstr_at(mm, args[k])
                k += 1
                i += 2
            else:
                res.append(fmt[i])
                i += 1
        for j, b in enumerate(bytes(res) + b'\0'):
            mm.mem[(mm.R[4] + j) & 0xFFFFFFFF] = b
        mm.R[0] = len(res)
    m.ext_ret[SPRINTF] = sprintf
    sp = 0x8cf00000
    out = 0x8c900000
    m.wn(sp, out, 4)
    m.R[15] = sp
    m.R[4], m.R[5], m.R[6], m.R[7] = town, pref, pool, mode
    m.PR = 0x8c000010
    m.run(COMPOSER, 0x8c000010)
    return cstr_at(m, out)


def with_english(image):
    """image copy with English strings written into the slots of (Japanese) pointer-table entries; returns (image, indices)"""
    import struct
    d = bytearray(image)

    def put(tbl, idx, text):
        p = struct.unpack_from('<I', d, tbl + 4 * idx)[0] - BASE
        assert len(text) + 1 <= 12
        d[p:p + 12] = text + b'\0' * (12 - len(text))
    put(TOWN_TBL, 1223, b'Kagoshima')      # 1-based; 12-byte slot (鹿児島市)
    put(PREF_TBL, 46, b'Kagoshima')        # 鹿児島県, 12-byte slot
    put(PREF_TBL, 14, b'Izu Is.')          # 伊豆諸島
    put(PREF_TBL, 13, b'Kanagawa')         # 神奈川県
    put(POOL_TBL, 46, b'Mythos')           # ﾐｭｰﾄｽ
    put(POOL_TBL, 11, b'Shadows')          # ｼｬﾄﾞｳｽﾞ
    return bytes(d)


def main():
    first = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    if len(sys.argv) > 1:
        orig = open(sys.argv[1], 'rb').read()
        eng = orig
    else:
        orig = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
        eng = with_english(orig)
    import layoutpatch as LP
    pat = LP.patch_clubnames(eng, 'HOMETOWN', guard=False)       # the unbounded join: the guard replaces the (dead in HOMETOWN) composer, see tools/re/ovf_sim.py
    for label, args in (('town+pool', (1223, 0, 46, 0)), ('pool+town', (1223, 0, 46, 1)), ('pref+pool', (1223, 46, 46, 2)),
                        ('pool+pref', (1223, 13, 11, 3)), ('Izu Is.', (1223, 14, 11, 2))):
        a = compose(eng, first, *args)
        b = compose(pat, first, *args)
        print('%-10s original %-26r patched %r' % (label, a.decode('cp932', 'replace'), b.decode('cp932', 'replace')))


if __name__ == '__main__':
    main()
