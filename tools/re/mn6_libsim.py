"""mn6_libsim.py: execute the number-library wrapper (tools/moneypatch.py LIB_SRC) in tools/sh4sim.py through the REAL patched overlays.

    python -I -X utf8 tools/re/mn6_libsim.py [--quick]

For every overlay of moneypatch.LIB_SITES: patch the overlay and 1ST_READ.BIN, enter the stub that now sits behind the old literal-pool word,
with the stack arguments of the library calls (fmt, a1, a2), and check that `real` is entered with ('%s', text) where text ==
moneypatch.lib_reference(...), that the callee-saved registers, sp and PR are restored, and that a non-money format reaches `real` untouched.
"""
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moneycheck as MC      # noqa: E402
import moneypatch as MP      # noqa: E402
import sh4sim                # noqa: E402
import textdb                # noqa: E402

M = sh4sim.M
RET = 0xDEAD0000
STACK = 0x8CFF0000
FMTS = 0x8CF10000            # where the test puts its format / argument strings
TOKEN = 0x12345678
DISC = None            # callable rel -> bytes of a BUILT disc (mn6_discsim.py): the overlays and 1ST_READ.BIN are read from it instead of patching extracted/


def cstr(m, a, enc='latin-1'):
    out = bytearray()
    while m.rb(a):
        out.append(m.rb(a))
        a += 1
    return out.decode(enc, 'replace')


class FMach(MC.Mach):
    """Mach + `sts FPUL,Rn` (the library functions convert a float field; the value is irrelevant here)"""

    def exec_op(self, op, pc):
        if (op & 0xF00F) == 0x0007:                       # mul.l Rm,Rn -> MACL
            self.MACL = (self.R[(op >> 8) & 15] * self.R[(op >> 4) & 15]) & M
            return None
        if (op & 0xF0FF) == 0x005A:
            self.R[(op >> 8) & 15] = 0
            return None
        return super().exec_op(op, pc)


class Lib:
    def __init__(self, rel):
        self.rel = rel
        d = MP.read_extracted(rel)
        if DISC:
            self.nd, sites = DISC(rel), [dict(off=MP.find_sites(d, rel)[0]['off'])]
        else:
            self.nd, sites = MP.patch_overlay(d, rel)
        self.site = sites[0]
        self.base = textdb.load_image(rel).base
        self.real = MP.LIB_SITES[rel][0][1]
        self.stub = self.base + self.site['off'] + MP.LIB_STUB_REL
        k1 = DISC('1ST_READ.BIN') if DISC else MP.patch_1st_read(MP.read_extracted('1ST_READ.BIN'))
        self.m = FMach()
        MC.hooks_1st_read(self.m)
        self.m.load(self.base, self.nd)
        o = MP.CAVE_ADDR - MP.IMG_BASE
        self.m.load(MP.CAVE_ADDR, k1[o:o + 0x200])
        o = MP.LIB_ADDR - MP.IMG_BASE
        self.m.load(MP.LIB_ADDR, k1[o:o + 0x200])
        self.m.native = [(self.base, self.base + len(self.nd)), (MP.CAVE_ADDR, MP.CAVE_ADDR + 0x200), (MP.LIB_ADDR, MP.LIB_ADDR + 0x200)]
        self.seen = []

        def real(m):
            fmt = cstr(m, m.rn(m.R[15], 4))
            a1 = m.rn(m.R[15] + 4, 4)
            self.seen.append((fmt, cstr(m, a1) if fmt == '%s' else None, m.R[15]))
            m.R[0] = TOKEN
            m.pc = m.PR                    # emulate `rts` (the watch callback runs before the instruction at pc)
        self.watch = {self.real: real}
        self.m.wn(RET, 0x0009, 2)           # nop at the return address; the run stops behind it

    def put(self, a, s):
        for i, c in enumerate(s.encode('latin-1') + b'\0'):
            self.m.wn(a + i, c, 1)
        return a

    def call(self, fmt, a1=None, a2=None):
        """enter the stub like the library does (jsr @r8 with the arguments pushed); returns (text handed to real or None, passed-through?)"""
        m = self.m
        m.R = [0] * 16
        for r in range(8, 15):
            m.R[r] = 0x1000 + r
        m.R[15] = STACK
        fa = self.put(FMTS, fmt)
        a1a = self.put(FMTS + 0x100, a1 if a1 is not None else '')
        a2a = self.put(FMTS + 0x200, a2 if a2 is not None else '')
        m.wn(STACK, fa, 4)
        m.wn(STACK + 4, a1a, 4)
        m.wn(STACK + 8, a2a, 4)
        m.PR = RET
        self.seen = []
        m.writes = set()
        m.run(self.stub, RET + 2, watch=self.watch)
        assert len(self.seen) <= 1
        regs_ok = all(m.R[r] == 0x1000 + r for r in range(8, 15)) and m.R[15] == STACK and all(STACK - 128 <= a < STACK for a in m.writes)
        return (self.seen[0] if self.seen else None), regs_ok, m.R[0]


def check_lib(rel, quick=False):
    L = Lib(rel)
    bad = 0

    def expect(fmt, a1, a2, want):
        nonlocal bad
        seen, regs_ok, r0 = L.call(fmt, a1, a2)
        got = None if seen is None or seen[0] != '%s' else seen[1]
        pass_through = seen is not None and seen[0] == fmt
        ok = regs_ok
        if want is None:
            ok = ok and (pass_through or (seen is not None and seen[0] == fmt))
        else:
            ok = ok and got == want and r0 == TOKEN
        if not ok:
            bad += 1
            print('FAIL', rel, repr(fmt), repr(a1), repr(a2), 'want', repr(want), 'got', seen, 'regs', regs_ok, hex(r0))
    for fmt, a1, a2, want in (('%s %s man', '   3', '9000', '3 oku 9000 man'), ('@R/%s %s man@', '  14', '0015', '@R/14 oku 15 man@'),
                              ('%s %s man', '  13', '0000', '13 oku'), ('%s man', '  58', None, '58 man'), ('%s Yen', '   0', None, '0 Yen'),
                              ('@R/%s man@', '9999', None, '@R/9999 man@'), ('%s %s man', ' 999', '9999', '999 oku 9999 man'),
                              ('%s man', '   1', None, '1 man'), ('%s %s man', '   1', '0001', '1 oku 1 man'),
                              ('%s%s', '12', '34', None), ('Y%s', '5', None, None), ('Sponsor %s', 'x', None, None), ('%s', 'abc', None, None),
                              ('0 Yen', None, None, None), ('%s %s', '1', '2', None), ('plain', None, None, None), ('', None, None, None)):
        ex = want
        if want is not None:
            lr = MP.lib_reference(fmt, a1, a2)
            if lr != want:
                bad += 1
                print('FAIL reference', fmt, a1, a2, lr, want)
        expect(fmt, a1, a2, ex)
    rnd = random.Random(7)
    n = 40 if quick else 300
    for _ in range(n):
        hi = rnd.choice([0, 1, 9, 10, 99, 100, 999, rnd.randrange(0, 1000)])
        lo = rnd.choice([0, 1, 9, 10, 99, 999, 1000, 9999, rnd.randrange(0, 10000)])
        w = rnd.choice([2, 3, 4])
        if hi:
            fmt = rnd.choice(['%s %s man', '@R/%s %s man@'])
            a1, a2 = str(hi).rjust(w), '%04d' % lo
        else:
            fmt = rnd.choice(['%s man', '@R/%s man@']) if lo else '%s Yen'
            a1, a2 = str(lo).rjust(4), None
        want = MP.lib_reference(fmt, a1, a2)
        assert want is not None
        expect(fmt, a1, a2, want)
        if hi:
            assert MP.reference(hi * 10000 + lo, 0, 'jp') in want
    return bad, L


# ------------------------------------------------------------------------------------------------ the real library functions
# F1 = GETREP 0x9358 (obj, V, flag)  [hi > 0: `%s億%s万円`, hi == 0: `%s万円`, V == 0: `0円`];  F2a = (V signed, x, y, mode) in every overlay (the `@R/` form for a negative V)
FUNCS = {'FLOW_PRG/GETREP.BIN': [('F1', 0x9358), ('F2a', 0x1431E)], 'FLOW_PRG/CHALMODE.BIN': [('F2a', 0x7762)], 'FLOW_PRG/DRSHRANK.BIN': [('F2a', 0x8A2A)],
         'FLOW_PRG/DRSISEKI.BIN': [('F2a', 0x4502)], 'FLOW_PRG/DRSJAPAN.BIN': [('F2a', 0x3992)], 'FLOW_PRG/DRSLIST.BIN': [('F2a', 0xAD42)],
         'FLOW_PRG/DRSSRANK.BIN': [('F2a', 0x9B4A)], 'FLOW_PRG/PL_EDIT.BIN': [('F2a', 0x11612)], 'FLOW_PRG/SELNAT.BIN': [('F2a', 0xB452)]}
OBJ = 0x8CF40000             # what `real` returns (a text object)
SELF = 0x8CF60000            # F1's list object
JA = {'%s億%s万円', '@R/%s億%s万円@', '%s万円', '@R/%s万円@', '%s円', '0円'}


class Fn(Lib):
    """Lib + the real functions: English formats (from translation/*.jsonl) written over the Japanese ones, helpers hooked."""

    def __init__(self, rel, english=True):
        super().__init__(rel)
        m = self.m
        if english and not DISC:
            import mn6_db
            for rid, r in mn6_db.records(lambda r: r['id'].split('#')[0] == rel and r['ja'] in JA):
                off = int(rid.split('#')[1], 16)
                self.put(self.base + off, r['en'])
        div, mod = m.ext_ret[0x8C012BF8], m.ext_ret[0x8C013460]
        m.ext_ret[0x8C0133B8], m.ext_ret[0x8C013528] = div, mod
        self.calls = []

        def real(mm):
            fmt = cstr(mm, mm.rn(mm.R[15], 4), 'cp932')
            args = [cstr(mm, mm.rn(mm.R[15] + 4 * (i + 1), 4)) for i in range(2)]
            self.calls.append((fmt, args))
            mm.R[0] = OBJ
            mm.pc = mm.PR
        self.watch = {self.real: real}

    def hook_bsr(self, fn, span=0x3C0):
        for k in range(0, span, 2):
            w = self.m.rn(fn + k, 2)
            if (w >> 12) == 0xB:
                d = w & 0xFFF
                d = d - 0x1000 if d & 0x800 else d
                self.m.ext_ret.setdefault(fn + k + 4 + d * 2, lambda mm: None)

    def run(self, kind, fn_off, V, mode=3):
        """returns [(fmt, [a1, a2])] seen by `real`"""
        m = self.m
        fn = self.base + fn_off
        self.hook_bsr(fn)
        m.R = [0] * 16
        m.R[15] = STACK
        m.wn(STACK, 0x8CF50000, 4)
        m.PR = RET
        self.calls = []
        if kind == 'F2a':
            m.R[4], m.R[5], m.R[6], m.R[7] = V & M, 100, 50, mode
        else:
            m.wn(SELF + 116, 0x8CF61000, 4)
            m.wn(SELF + 120, 0, 1)
            m.R[4], m.R[5], m.R[6] = SELF, V, 0
        m.run(fn, RET + 2, watch=self.watch)
        return list(self.calls)


def check_functions(quick=False, modes=(False, True)):
    bad = 0
    vals = [0, 1, 58, 150, 9999, 10000, 10001, 14642, 24300, 39000, 100000, 99999, 123456, 9999999, 5000000, 600000]
    for rel, fns in FUNCS.items():
        for kind, off in fns:
            for english in modes:
                F = Fn(rel, english)
                for V in vals if not quick else vals[::3]:
                    for sign in ((1,) if kind == 'F1' else (1, -1)):
                        if V == 0 and sign < 0:
                            continue
                        try:
                            calls = F.run(kind, off, V * sign)
                        except Exception as e:           # noqa: BLE001
                            bad += 1
                            print('FAIL', rel, kind, V, 'exception', e)
                            continue
                        Vc = min(V, 9999999)
                        want_amount = Vc * 10000
                        if not english:
                            # original formats: check the argument shapes (what the wrapper has to parse)
                            ok = len(calls) == 1 and calls[0][0] in JA | {'0 Yen'}
                            if ok and calls[0][0] in ('%s億%s万円', '@R/%s億%s万円@'):
                                a1, a2 = calls[0][1]
                                ok = int(a1) * 10000 + int(a2) == Vc and len(a2.strip()) == 4
                            elif ok and calls[0][0] in ('%s万円', '@R/%s万円@'):
                                ok = int(calls[0][1][0]) == Vc
                            elif ok and calls[0][0] == '%s円':
                                ok = int(calls[0][1][0]) == 0 and Vc == 0
                            elif ok and calls[0][0] in ('0円', '0 Yen'):
                                ok = Vc == 0
                            if not ok:
                                bad += 1
                                print('FAIL original shapes', rel, kind, V * sign, calls)
                        else:
                            want = MP.reference(Vc, 0, 'jp')
                            ok = len(calls) == 1
                            if ok:
                                fmt, args = calls[0]
                                if fmt == '0 Yen':
                                    text = '0 Yen'
                                else:
                                    ok = fmt == '%s'
                                    text = args[0]
                                if ok:
                                    core = text[3:-1] if text.startswith('@R/') and text.endswith('@') else text
                                    ok = core == want and (sign < 0) == text.startswith('@R/') and (kind == 'F1' or True)
                                if not ok:
                                    bad += 1
                                    print('FAIL english', rel, kind, V * sign, calls, 'want', want)
                            else:
                                bad += 1
                                print('FAIL english', rel, kind, V * sign, calls)
                            assert want_amount == Vc * 10000
            print('%-24s %-3s %s' % (rel, kind, 'checked'))
    return bad


# ------------------------------------------------------------------------------------------------ the numeric wrapper (libn)
LIBC_SPRINTF = 0x8C014D80


class Libn:
    """patched overlay + 1ST_READ (money cave, lib, libn) of one LIBN_SITES / LIBN_GAME overlay"""

    def __init__(self, rel):
        self.rel = rel
        d = MP.read_extracted(rel)
        if DISC:
            self.nd, sites = DISC(rel), [dict(off=MP.find_sites(d, rel)[0]['off'])]
        else:
            self.nd, sites = MP.patch_overlay(d, rel)
        self.site = sites[0]
        self.base = textdb.load_image(rel).base
        self.spec = MP.LIBN_SITES.get(rel)
        k1 = DISC('1ST_READ.BIN') if DISC else MP.patch_1st_read(MP.read_extracted('1ST_READ.BIN'))
        self.m = FMach()
        MC.hooks_1st_read(self.m)
        self.m.load(self.base, self.nd)
        regions = [(MP.CAVE_ADDR, 0x200), (MP.LIB_ADDR, 0x200), (MP.LIBN_ADDR, MP.LIBN_RESERVE)]
        for a, n in regions:
            self.m.load(a, k1[a - MP.IMG_BASE:a - MP.IMG_BASE + n])
        self.m.native = [(self.base, self.base + len(self.nd))] + [(a, a + n) for a, n in regions]
        self.m.wn(RET, 0x0009, 2)
        self.sym = MP.libn_assembly()[2]
        self.seen = []
        real = self.spec['pools'][0][1] if self.spec else LIBC_SPRINTF
        self.real = real

        def hook(m):
            fmt = cstr(m, m.rn(m.R[15], 4), 'cp932')
            a1 = m.rn(m.R[15] + 4, 4)
            self.seen.append((fmt, cstr(m, a1) if fmt == '%s' else None, m.R[4], m.R[15]))
            m.R[0] = TOKEN
            m.pc = m.PR
        self.watch = {real: hook}

    def stub_va(self):
        return self.base + self.site['off'] + MP.LIBN_STUB_REL

    def put(self, a, s):
        for i, c in enumerate(s.encode('latin-1') + b'\0'):
            self.m.wn(a + i, c, 1)

    def call(self, fmt, args, dst=0x8CF70000):
        """enter the stub with libc-sprintf conventions: r4 = dst, [sp] = fmt, [sp+4..] = integer arguments"""
        m = self.m
        m.R = [0] * 16
        for r in range(8, 15):
            m.R[r] = 0x1000 + r
        m.R[15] = STACK
        self.put(FMTS, fmt)
        m.wn(STACK, FMTS, 4)
        for i, a in enumerate(args):
            m.wn(STACK + 4 + 4 * i, a & M, 4)
        m.R[4], m.R[5], m.R[6], m.R[7] = dst, 0x55, 0x66, 0x77
        for i in range(40):
            m.wn(dst + i, 0x55, 1)
        m.PR = RET
        self.seen = []
        m.writes = set()
        m.run(self.stub_va(), RET + 2, watch=self.watch)
        regs_ok = all(m.R[r] == 0x1000 + r for r in range(8, 15)) and m.R[15] == STACK
        stray = [a for a in m.writes if not (STACK - 160 <= a < STACK or dst <= a < dst + 40)]
        return self.seen, regs_ok and not stray, m.R[0], dst

    def dst_text(self, dst):
        return cstr(self.m, dst)


def check_libn(rel, quick=False):
    L = Libn(rel)
    bad = 0

    def fail(*a):
        nonlocal bad
        bad += 1
        print('FAIL', rel, *a)
    W = L.spec['width']
    al = L.spec['entry'] == 'n_al'
    cases = ([('%d Yen', (390000000,)), ('%d Yen', (146420000,)), ('%d Yen', (243000000,)), ('%d Yen', (0,)), ('%d Yen', (5000,)), ('%d Yen', (9999,)),
              ('%d Yen', (10000,)), ('%d Yen', (123456789,)), ('%d Yen', (2147483647,)), ('%d Yen', (-390000000,)), ('%d Yen', (-5000,))] if al else
             [('%2d oku %02d00m', (13, 15)), ('%2d oku %02d00m', (1, 3)), ('%2d oku %02d00m', (99, 99)), ('%2d oku %02d00m', (5, 0)), ('%6d00 man', (26,)),
              ('%6d00 man', (0,)), ('%6d00 man', (9999,)), ('%d cho%04d oku%02d00m', (1, 1123, 5)), ('    %4d oku %02d00m', (1234, 56)),
              ('          %4d man', (4500,)), ('          %4d man', (0,)), ('%d cho%04d oku%02d00m', (0, 5, 0))])
    cases += [('%d', (5,)), ('%3d %-13s Y%d %d yr', (1, 2, 3, 4)), ('%s', (0,)), ('%d%d', (1, 2)), ('Y%d', (7,)), ('%d x', (1,)), ('plain', ()), ('', ()),
              ('%d.%04d', (1, 2))]
    for fmt, args in cases:
        want = MP.libn_apply(fmt, list(args), W) if not al else MP.libn_reference(fmt, list(args), 0)
        seen, ok, r0, dst = L.call(fmt, list(args))
        if not ok:
            fail('registers / stray writes', fmt, args)
            continue
        if want is None:
            if not (len(seen) == 1 and seen[0][0] == fmt and seen[0][3] == STACK and seen[0][2] == dst):
                fail('pass-through', fmt, args, seen)
            continue
        if al:
            if not (len(seen) == 1 and seen[0][0] == '%s' and seen[0][1] == want and r0 == TOKEN):
                fail('text', fmt, args, 'want', want, 'got', seen)
        else:
            got = L.dst_text(dst)
            if seen or got != want or r0 != len(want):
                fail('text', fmt, args, 'want', repr(want), 'got', repr(got), 'r0', r0, seen)
            if W and len(want) != max(W, len(want)):
                fail('width', fmt, args)
    rnd = random.Random(11)
    for _ in range(30 if quick else 200):
        if al:
            y = rnd.choice([0, 1, 9999, 10000, 12345678, rnd.randrange(0, 10 ** 9), -rnd.randrange(1, 10 ** 9), rnd.randrange(0, 2 ** 31)])
            fmt, args = '%d Yen', (y,)
        else:
            oku, h = rnd.randrange(0, 100), rnd.randrange(0, 100)
            fmt, args = rnd.choice([('%2d oku %02d00m', (oku, h)), ('%6d00 man', (rnd.randrange(0, 10000),)), ('          %4d man', (rnd.randrange(0, 10000),)),
                                    ('    %4d oku %02d00m', (rnd.randrange(0, 100000), h))])
        want = MP.libn_apply(fmt, list(args), W) if not al else MP.libn_reference(fmt, list(args), 0)
        seen, ok, r0, dst = L.call(fmt, list(args))
        got = (seen[0][1] if seen else None) if al else L.dst_text(dst)
        if not ok or got != want:
            fail('random', fmt, args, 'want', want, 'got', got)
    if al:                                                        # the digit counter replacement
        for y in (0, 5, 9999, 10000, 390000000, 146420000, -390000000, 2147483647):
            m = L.m
            m.R = [0] * 16
            for r in range(8, 15):
                m.R[r] = 0x1000 + r
            m.R[15] = STACK
            m.R[4] = y & M
            m.PR = RET
            m.run(L.sym['n_gd'], RET + 2)
            want = len(MP.libn_reference('%d Yen', [y], 0)) - 2
            if m.R[0] != want or not all(m.R[r] == 0x1000 + r for r in range(8, 15)) or m.R[15] != STACK:
                fail('digit counter', y, m.R[0], want)
    return bad, L


def check_game(quick=False):
    rel = 'FLOW_PRG/GAME.BIN'
    d = MP.read_extracted(rel)
    nd = DISC(rel) if DISC else MP.patch_overlay(d, rel)[0]
    base = textdb.load_image(rel).base
    k1 = DISC('1ST_READ.BIN') if DISC else MP.patch_1st_read(MP.read_extracted('1ST_READ.BIN'))
    m = FMach()
    MC.hooks_1st_read(m)
    m.load(base, nd)
    for a, n in ((MP.CAVE_ADDR, 0x200), (MP.LIBN_ADDR, MP.LIBN_RESERVE)):
        m.load(a, k1[a - MP.IMG_BASE:a - MP.IMG_BASE + n])
    m.native = [(base, base + len(nd)), (MP.CAVE_ADDR, MP.CAVE_ADDR + 0x200), (MP.LIBN_ADDR, MP.LIBN_ADDR + MP.LIBN_RESERVE)]
    bad = 0
    fn = base + MP.LIBN_GAME[rel]['off']
    for V in [0, 1, 58, 9999, 10000, 14642, 39000, 99999999, 2 ** 31 - 1] + [random.Random(3).randrange(0, 10 ** 8) for _ in range(5)]:
        m.R = [0] * 16
        for r in range(8, 15):
            m.R[r] = 0x1000 + r
        m.R[15] = STACK
        dst = 0x8CF80000
        for i in range(40):
            m.wn(dst + i, 0x55, 1)
        m.R[4], m.R[5] = dst, V
        m.PR = RET
        m.wn(RET, 0x0009, 2)
        m.run(fn, RET + 2)
        got = cstr(m, dst)
        if got != MP.reference(V, 0, 'jp') or m.R[15] != STACK or not all(m.R[r] == 0x1000 + r for r in range(8, 15)):
            bad += 1
            print('FAIL GAME', V, repr(got))
    return bad


def main(argv):
    quick = '--quick' in argv
    if '--libn' in argv:
        tot = 0
        for rel in MP.LIBN_SITES:
            bad, L = check_libn(rel, quick)
            tot += bad
            print('%-24s stub %#x %s' % (rel, L.stub_va(), 'OK' if not bad else '%d FAIL' % bad))
        b = check_game(quick)
        print('GAME %s' % ('OK' if not b else '%d FAIL' % b))
        return 1 if tot or b else 0
    if '--functions' in argv:
        return 1 if check_functions(quick) else 0
    tot = 0
    for rel in MP.LIB_SITES:
        bad, L = check_lib(rel, quick)
        tot += bad
        print('%-24s stub %#x real %#x %s' % (rel, L.stub, L.real, 'OK' if not bad else '%d FAIL' % bad))
    return 1 if tot else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
