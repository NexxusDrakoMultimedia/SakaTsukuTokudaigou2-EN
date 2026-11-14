"""Unit tests of the integer opcodes added to tools/sh4sim.py for the patch engine (docs/patch-engine.md).
Every opcode is executed on random inputs and compared with an independent Python reference; when capstone is installed the
hand-encoded words are also decoded and their mnemonic compared (so the encodings themselves are checked).
    python -I -X utf8 tools/test_sh4sim.py"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sh4sim  # noqa: E402

try:
    import capstone as _cs
    MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception:      # pragma: no cover
    MD = None

M = 0xFFFFFFFF
BASE = 0x1000
s32 = sh4sim.s32


def w(hi, n=0, m=0, lo=0):
    return (hi << 12) | (n << 8) | (m << 4) | lo


def mnemonic(word):
    if MD is None:
        return None
    ins = list(MD.disasm(word.to_bytes(2, 'little'), BASE))
    return ins[0].mnemonic if ins else None


def run(words, regs=None, T=0, Q=0, Mf=0, macl=0, mach=0, pr=0, native=False):
    m = sh4sim.Machine()
    code = b''.join(x.to_bytes(2, 'little') for x in words)
    m.load(BASE, code)
    for k, v in (regs or {}).items():
        m.R[k] = v & M
    m.T, m.Q, m.Mf, m.MACL, m.MACH, m.PR = T, Q, Mf, macl, mach, pr
    if native:
        m.native = [(BASE, BASE + 0x100)]
    m.run(BASE, BASE + len(code))
    return m


RND = random.Random(1234)
EDGE = [0, 1, 2, 0x7F, 0x80, 0xFF, 0x7FFF, 0x8000, 0xFFFF, 0x10000, 0x7FFFFFFF, 0x80000000, 0x80000001, 0xFFFFFFFE, 0xFFFFFFFF]


def vals(n=60):
    return EDGE + [RND.getrandbits(32) for _ in range(n)]


class Opcodes(unittest.TestCase):
    def two(self, word, mnem, ref, flags=False, regs_n=3, regs_m=5):
        """execute `word` (Rn = r3, Rm = r5 encodings given by the caller) on EDGE x EDGE pairs"""
        if mnem and MD is not None:
            self.assertEqual(mnemonic(word), mnem, hex(word))
        for a in EDGE:
            for b in EDGE + [RND.getrandbits(32) for _ in range(6)]:
                for t in ((0, 1) if flags else (0,)):
                    m = run([word], {regs_n: a, regs_m: b}, T=t)
                    want = ref(a, b, t)
                    self.assertEqual((m.R[regs_n], m.T) if flags else m.R[regs_n], want, '%04x a=%x b=%x t=%d' % (word, a, b, t))

    def test_not(self):
        self.two(w(6, 3, 5, 7), 'not', lambda a, b, t: ~b & M)

    def test_swap(self):
        self.two(w(6, 3, 5, 8), 'swap.b', lambda a, b, t: (b & 0xFFFF0000) | ((b & 0xFF) << 8) | ((b >> 8) & 0xFF))
        self.two(w(6, 3, 5, 9), 'swap.w', lambda a, b, t: ((b & 0xFFFF) << 16) | (b >> 16))

    def test_xor_xtrct(self):
        self.two(w(2, 3, 5, 0xA), 'xor', lambda a, b, t: a ^ b)
        self.two(w(2, 3, 5, 0xD), 'xtrct', lambda a, b, t: ((b & 0xFFFF) << 16) | (a >> 16))

    def test_xor_imm(self):
        if MD is not None:
            self.assertEqual(mnemonic(0xCA5A), 'xor')
        m = run([0xCA5A], {0: 0xF0F0F0F0})
        self.assertEqual(m.R[0], 0xF0F0F0F0 ^ 0x5A)

    def test_negc_subc(self):
        self.two(w(6, 3, 5, 0xA), 'negc', lambda a, b, t: ((-b - t) & M, int(b + t > 0)), flags=True)
        self.two(w(3, 3, 5, 0xA), 'subc', lambda a, b, t: ((a - b - t) & M, int(a - b - t < 0)), flags=True)

    def test_addv_subv(self):
        def ovf(x):
            return int(not -(1 << 31) <= x < (1 << 31))
        self.two(w(3, 3, 5, 0xF), 'addv', lambda a, b, t: ((a + b) & M, ovf(s32(a) + s32(b))), flags=True)
        self.two(w(3, 3, 5, 0xB), 'subv', lambda a, b, t: ((a - b) & M, ovf(s32(a) - s32(b))), flags=True)

    def test_cmp_str(self):
        def ref(a, b, t):
            x = a ^ b
            return int(any(((x >> s) & 0xFF) == 0 for s in (0, 8, 16, 24)))
        if MD is not None:
            self.assertEqual(mnemonic(w(2, 3, 5, 0xC)), 'cmp/str')
        for a in vals(20):
            for b in vals(20) + [a, a ^ 0xFF00, a ^ 0x00FF0000]:
                self.assertEqual(run([w(2, 3, 5, 0xC)], {3: a, 5: b}).T, ref(a, b, 0))

    def one(self, sub, mnem, ref, flags=True):
        word = w(4, 3, 0, 0) | sub
        if MD is not None:
            self.assertEqual(mnemonic(word), mnem, hex(word))
        for a in vals(40):
            for t in (0, 1):
                m = run([word], {3: a}, T=t)
                self.assertEqual((m.R[3], m.T), ref(a, t), '%s %x t=%d' % (mnem, a, t))

    def test_shifts_and_rotates(self):
        self.one(0x09, 'shlr2', lambda a, t: (a >> 2, t))
        self.one(0x19, 'shlr8', lambda a, t: (a >> 8, t))
        self.one(0x29, 'shlr16', lambda a, t: (a >> 16, t))
        self.one(0x04, 'rotl', lambda a, t: (((a << 1) | (a >> 31)) & M, a >> 31))
        self.one(0x05, 'rotr', lambda a, t: ((a >> 1) | ((a & 1) << 31), a & 1))
        self.one(0x24, 'rotcl', lambda a, t: (((a << 1) | t) & M, a >> 31))
        self.one(0x25, 'rotcr', lambda a, t: ((a >> 1) | (t << 31), a & 1))
        self.one(0x10, 'dt', lambda a, t: ((a - 1) & M, int(((a - 1) & M) == 0)))

    def test_shad_shld(self):
        def shad(v, sh):
            c = sh & 31
            if not sh & 0x80000000:
                return (v << c) & M
            if c == 0:
                return M if v >> 31 else 0
            return (s32(v) >> (32 - c)) & M

        def shld(v, sh):
            c = sh & 31
            if not sh & 0x80000000:
                return (v << c) & M
            return 0 if c == 0 else v >> (32 - c)
        for word, mn, ref in ((w(4, 3, 5, 0xC), 'shad', shad), (w(4, 3, 5, 0xD), 'shld', shld)):
            if MD is not None:
                self.assertEqual(mnemonic(word), mn)
            for v in vals(12):
                for sh in list(range(-33, 34)) + [0x80000000, 0x7FFFFFFF, 0xFFFFFFE0, 0xFFFFFFFF]:
                    m = run([word], {3: v, 5: sh & M})
                    self.assertEqual(m.R[3], ref(v, sh & M), '%s v=%x sh=%d' % (mn, v, sh))
        # hand checked values: shad by -1 is an arithmetic shift right by one, shld by -1 a logical one
        self.assertEqual(run([w(4, 3, 5, 0xC)], {3: 0x80000000, 5: M}).R[3], 0xC0000000)
        self.assertEqual(run([w(4, 3, 5, 0xD)], {3: 0x80000000, 5: M}).R[3], 0x40000000)

    def test_multiplies(self):
        if MD is not None:
            for word, mn in ((w(2, 3, 5, 0xE), 'mulu.w'), (w(2, 3, 5, 0xF), 'muls.w'), (w(3, 3, 5, 5), 'dmulu.l'), (w(3, 3, 5, 0xD), 'dmuls.l')):
                self.assertEqual(mnemonic(word), mn)
        for a in vals(15):
            for b in vals(15):
                self.assertEqual(run([w(2, 3, 5, 0xE)], {3: a, 5: b}).MACL, (a & 0xFFFF) * (b & 0xFFFF) & M)
                self.assertEqual(run([w(2, 3, 5, 0xF)], {3: a, 5: b}).MACL, (sh4sim.s16(a) * sh4sim.s16(b)) & M)
                m = run([w(3, 3, 5, 5), w(0, 4, 0, 0xA), w(0, 6, 1, 0xA)], {3: a, 5: b})        # dmulu.l; sts mach,r4; sts macl,r6
                self.assertEqual((m.R[4] << 32) | m.R[6], a * b)
                m = run([w(3, 3, 5, 0xD), w(0, 4, 0, 0xA), w(0, 6, 1, 0xA)], {3: a, 5: b})
                self.assertEqual((m.R[4] << 32) | m.R[6], (s32(a) * s32(b)) & (2 ** 64 - 1))

    def test_flags_and_mac(self):
        self.assertEqual(run([0x0018]).T, 1)
        self.assertEqual(run([0x0008], T=1).T, 0)
        m = run([0x0028], macl=5, mach=6)
        self.assertEqual((m.MACL, m.MACH), (0, 0))
        m = run([w(4, 3, 0, 0x0A), w(4, 5, 0, 0x1A), w(0, 6, 0, 0xA), w(0, 7, 1, 0xA)], {3: 0x1234, 5: 0x5678})   # lds r3,mach; lds r5,macl; sts
        self.assertEqual((m.R[6], m.R[7]), (0x1234, 0x5678))
        m = run([w(4, 3, 0, 0x2A), w(0, 4, 2, 0xA)], {3: 0xABCD0})                                              # lds r3,pr; sts pr,r4
        self.assertEqual(m.R[4], 0xABCD0)

    def test_div0s_div0u(self):
        for a in EDGE:
            for b in EDGE:
                m = run([w(2, 3, 5, 7)], {3: a, 5: b})
                self.assertEqual((m.Q, m.Mf, m.T), (a >> 31, b >> 31, (a >> 31) ^ (b >> 31)))
        m = run([0x0019], T=1, Q=1, Mf=1)
        self.assertEqual((m.Q, m.Mf, m.T), (0, 0, 0))

    def test_div1_unsigned_division(self):
        """the manual's 32 / 32 unsigned division: div0u; (rotcl r1; div1 r0,r2) x 32; rotcl r1   (r1 = dividend -> quotient,
        r0 = divisor, r2 = running remainder).  Valid for divisors below 2**31."""
        prog = [0x0019] + [w(4, 1, 2, 4), w(3, 2, 0, 4)] * 32 + [w(4, 1, 2, 4)]
        if MD is not None:
            self.assertEqual(mnemonic(w(3, 2, 0, 4)), 'div1')
        cases = [(0, 1), (1, 1), (100, 7), (0xFFFFFFFF, 1), (0xFFFFFFFF, 0x7FFFFFFF), (0x80000000, 3), (12345678, 12345), (5, 6)]
        cases += [(RND.getrandbits(32), RND.randrange(1, 1 << RND.randrange(1, 32))) for _ in range(300)]
        for a, b in cases:
            m = run(prog, {1: a, 0: b, 2: 0})
            self.assertEqual(m.R[1], a // b, 'div %d / %d' % (a, b))

    def test_bsr_bsrf_braf_pref(self):
        # 1000: bsr +2 ; 1002: nop ; 1004: nop ; 1006: <stop>  | 1008: rts ; 100a: mov #7,r0
        words = [0xB002, 0x0009, 0x0009, 0x0009, 0x000B, 0xE007]
        m = sh4sim.Machine()
        m.load(BASE, b''.join(x.to_bytes(2, 'little') for x in words))
        m.native = [(BASE, BASE + 0x100)]
        m.run(BASE, BASE + 6)
        self.assertEqual((m.R[0], m.PR), (7, BASE + 4))
        # bsrf r1 (r1 = 6 -> target 1000+4+6 = 100a: rts with mov #9,r0 in its slot)  /  braf r1 (skips two movs)
        m = sh4sim.Machine()
        words = [w(0, 1, 0, 3), 0x0009, 0x0009, 0x0009, 0x0009, 0x000B, 0xE009]
        m.load(BASE, b''.join(x.to_bytes(2, 'little') for x in words))
        m.native = [(BASE, BASE + 0x100)]
        m.R[1] = 6
        m.run(BASE, BASE + 6)
        self.assertEqual((m.R[0], m.PR), (9, BASE + 4))
        m = sh4sim.Machine()
        words = [w(0, 1, 2, 3), 0xE001, 0xE005, 0xE006, 0x0009, 0x0009]
        m.load(BASE, b''.join(x.to_bytes(2, 'little') for x in words))
        m.R[1] = 4                                                                          # target = 1000 + 4 + 4 = 1008
        m.run(BASE, BASE + 8)
        self.assertEqual(m.R[0], 1)                                                         # only the delay slot (mov #1,r0) ran
        for op in (w(0, 3, 8, 3),):
            if MD is not None:
                self.assertEqual(mnemonic(op), 'pref')
            m = run([op], {3: 0x1234})
            self.assertEqual(m.R[3], 0x1234)

    def test_unknown_opcode_still_raises(self):
        with self.assertRaises(sh4sim.SimError):
            run([0x0002])                                                                   # stc sr,r0 : not modelled


if __name__ == '__main__':
    unittest.main()
