"""sk2_money_edges.py : skeptic check of the money cave. Independent formatter (not MP.reference) vs the cave run in sh4sim.
Values are V in Man (10,000 yen) units, as the game stores them; also the same list read as yen / 10000 and wrapped to int32."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneycheck as MC
import moneypatch as MP
import sh4sim

M = sh4sim.M


def indep(v):
    """independent jp formatter, v is a signed Python int in Man units"""
    if v == 0:
        return '0 Yen'
    s = '-' if v < 0 else ''
    a = abs(v)
    oku, man = divmod(a, 10000)
    parts = []
    if oku:
        parts.append('%d Oku' % oku)
    if man:
        parts.append('%d Man' % man)
    return s + ' '.join(parts)


def s32(x):
    x &= M
    return x - (1 << 32) if x & 0x80000000 else x


def main():
    cave = MP.cave_bytes(MP.CAVE_ADDR, 'jp')
    m = MC.Mach()
    m.load(MP.CAVE_ADDR, cave)
    m.native = [(MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
    vals = [0, 1, 9, 10, 99, 100, 999, 1000, 9999, 10000, 10001, 10010, 99999, 100000, 99999999, 100000000, 131500, 1315000000,
            9999999999999, 2 ** 31 - 1, -1, -9999, -10000, -2 ** 31, 20000, 100000000000, 12345678, 10000000, 1000000]
    yen = [0, 1, 9999, 10000, 99999999, 100000000, 1315000000, 9999999999999]
    bad = 0
    for tag, lst in (('V', vals), ('yen/10000', [y // 10000 for y in yen])):
        for v in lst:
            w = s32(v)
            m.R = [0] * 16
            for r in (8, 9, 10, 11, 12, 13, 14):
                m.R[r] = 0x7000 + r
            m.R[15] = MC.STACK
            m.R[4], m.R[5], m.R[6] = MC.OUT, v & M, 0
            m.PR = MC.RET
            for i in range(64):
                m.wn(MC.OUT + i, 0x55, 1)
            m.writes = set()
            steps = m.run(MP.CAVE_ADDR, MC.RET)
            n = m.R[0]
            raw = bytes(m.rb(MC.OUT + i) for i in range(n))
            want = indep(w)
            okreg = all(m.R[r] == 0x7000 + r for r in (8, 9, 10, 11, 12, 13, 14)) and m.R[15] == MC.STACK
            after = m.rb(MC.OUT + n)
            ascii_ok = all(32 <= c < 127 for c in raw)
            ok = raw.decode('latin1') == want and n == len(want) and okreg and ascii_ok and after == 0x55
            outside = [a for a in m.writes if not (MC.OUT <= a < MC.OUT + n) and not (MC.STACK - 128 <= a < MC.STACK)]
            if outside:
                ok = False
            print('%-9s %-14d (int32 %-12d) %-26r %s steps=%d %s' % (tag, v, w, raw.decode('latin1'), 'OK ' if ok else 'BAD', steps, '' if raw.decode('latin1') == MP.reference(w, 0, 'jp') else 'REF-MISMATCH'))
            bad += not ok
    print('bad:', bad)
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
