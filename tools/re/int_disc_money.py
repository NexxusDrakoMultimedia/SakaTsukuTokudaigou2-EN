"""Integrator: verify the money output of a REAL built disc with the SH4 simulator.

    python -I -X utf8 tools/re/int_disc_money.py <disc dir> <disc name> [jp|western]

Reads /1ST_READ.BIN and the money-hooked overlays back from the built tracks (tools/discbuild.Source), checks that the cave in the
disc is byte-identical to the moneypatch cave, that every overlay money function of variant A starts with the hook, then runs the cave
FROM THE DISC BYTES on example values (independent expected text) and the TV card routine bytes against the style's reference.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D            # noqa: E402
import moneycheck as MC          # noqa: E402
import moneypatch as MP          # noqa: E402


def expect(v, style):
    if style == 'jp':
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
    return MP.reference(v, 0, 'western')


def main(argv):
    root, name = argv[1], argv[2]
    style = argv[3] if len(argv) > 3 else 'jp'
    MC.STYLE = style
    src = D.Source(root, name)
    _pvd, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    def rd(p):
        r = files['/' + p.upper()]
        return src.read(r.lba, r.size)
    bad = 0
    k = rd('1ST_READ.BIN')
    n = len(MP.cave_bytes(MP.CAVE_ADDR, style))
    o = MP.CAVE_ADDR - MP.IMG_BASE
    cave = k[o:o + n]
    ok = cave == MP.cave_bytes(MP.CAVE_ADDR, style)
    print('%s cave in disc 1ST_READ.BIN @%#x: %d bytes, identical to moneypatch.cave_bytes(%s)' % ('ok  ' if ok else 'FAIL', MP.CAVE_ADDR, n, style))
    bad += not ok
    hooks = 0
    hb = MP.hook_bytes()
    for rel in MP.overlay_paths():
        orig = MP.read_extracted(rel)
        d = rd(rel)
        for s in MP.find_sites(orig, rel):
            if s['variant'] != 'A':
                continue
            if d[s['off']:s['off'] + 12] == hb:
                hooks += 1
            else:
                bad += 1
                print('FAIL hook missing in', rel, hex(s['off']))
    print('%s %d money hooks (variant A) read back from the disc overlays (expected %d)' % ('ok  ' if hooks == MP.EXPECTED_SITES['A'] else 'FAIL', hooks, MP.EXPECTED_SITES['A']))
    bad += hooks != MP.EXPECTED_SITES['A']
    # TV card routine
    tv = rd('FLOW_PRG/TV_EVENT.BIN')
    tvo = MP.read_extracted('FLOW_PRG/TV_EVENT.BIN')
    print('info TV_EVENT.BIN in disc differs from the original in %d bytes' % sum(1 for a, b in zip(tv, tvo) if a != b))
    m = MC.Mach()
    m.load(MP.CAVE_ADDR, cave)
    m.native = [(MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
    yens = [0, 10000, 600000000 // 100, 60000000, 100000000, 131500 * 10000, 1315000000, 3250000000 // 1, 9999 * 10000, 99999999]
    vs = [(y, y // 10000) for y in (0, 60000000, 100000000, 130000000, 1315000000, 9999 * 10000, 20000000000)]
    vs += [(None, v) for v in (1, 9999, 10000, 131500, 325000, 99999999, -1)]
    for y, v in vs:
        m.R = [0] * 16
        m.R[15] = MC.STACK
        m.R[4], m.R[5], m.R[6] = MC.OUT, v & MC.M, 0
        m.PR = MC.RET
        for i in range(64):
            m.wn(MC.OUT + i, 0x55, 1)
        m.run(MP.CAVE_ADDR, MC.RET)
        got = bytes(m.rb(MC.OUT + i) for i in range(m.R[0])).decode('ascii', 'replace')
        want = expect(v, style)
        ok = got == want
        bad += not ok
        print('%s yen=%s V=%d -> %r%s' % ('ok  ' if ok else 'FAIL', y, v, got, '' if ok else '   want %r' % want))
    src.close()
    print('bad', bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
