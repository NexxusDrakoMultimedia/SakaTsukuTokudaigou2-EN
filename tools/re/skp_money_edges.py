"""skp_money_edges: skeptic check of the jp money cave on edge values, with an INDEPENDENT expected text.

    python -I -X utf8 tools/re/skp_money_edges.py

Values are given in yen (as the stage-2 brief lists them) and as raw game units (V = 10,000 yen).  A yen value that is not a multiple of
10,000 is floored by the game's own unit (V = yen // 10000); the cave only sees V.  V must fit a signed 32 bit word.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE)))
import moneycheck as MC          # noqa: E402
import moneypatch as MP          # noqa: E402


def expect(v):
    if v == 0:
        return '0 Yen'
    s = '-' if v < 0 else ''
    a = abs(v)
    t = []
    if a // 10000:
        t.append('%d Oku' % (a // 10000))
    if a % 10000:
        t.append('%d Man' % (a % 10000))
    return s + ' '.join(t)


def main():
    cave = MP.cave_bytes(MP.CAVE_ADDR, 'jp')
    m = MC.Mach()
    m.load(MP.CAVE_ADDR, cave)
    m.native = [(MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
    yens = [0, 9999, 10000, 99999999, 100000000, 1315000000, 9999999999999, 21474836470000 - 1]
    vs = [(y, y // 10000) for y in yens]
    vs += [(None, v) for v in (0, 1, 9999, 10000, 10001, 19999, 20000, 99999, 100000, 131500, 999999999, 2 ** 31 - 1, -1, -10000, -2 ** 31)]
    bad = 0
    for y, v in vs:
        if not -2 ** 31 <= v < 2 ** 31:
            print('SKIP (does not fit s32) yen=%s V=%d' % (y, v))
            continue
        for flag in (0, 1):
            m.R = [0] * 16
            for r in (8, 9, 10, 11, 12, 13, 14):
                m.R[r] = 0x1000 + r
            m.R[15] = MC.STACK
            m.R[4], m.R[5], m.R[6] = MC.OUT, v & MC.M, flag
            m.PR = MC.RET
            for i in range(64):
                m.wn(MC.OUT + i, 0x55, 1)
            m.writes = set()
            m.run(MP.CAVE_ADDR, MC.RET)
            n = m.R[0]
            raw = bytes(m.rb(MC.OUT + i) for i in range(n))
            nxt = m.rb(MC.OUT + n)
            ok = raw.decode('ascii', 'replace') == expect(v) and nxt == 0x55 or (nxt == 0)
            ok = ok and raw.decode('ascii', 'replace') == expect(v) and all(32 <= b < 127 for b in raw)
            ok = ok and all(m.R[r] == 0x1000 + r for r in (8, 9, 10, 11, 12, 13, 14)) and m.PR == MC.RET and m.R[15] == MC.STACK
            if not ok:
                bad += 1
            print('%s yen=%s V=%d flag=%d -> %r (n=%d, next byte %#x) %s' % ('ok  ' if ok else 'FAIL', y, v, flag, raw.decode('ascii', 'replace'), n, nxt, '' if ok else 'want ' + expect(v)))
    print('bad', bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
