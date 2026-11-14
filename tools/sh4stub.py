"""Minimal SH-4 interpreter used ONLY to run the entry stub of a FLOW_PRG/ATFIRST overlay
up to its first call to code outside the image, and report the call target and r4..r7.

For the standard stub that call is the loader hook 0x8c159144 = FUN_8c163194(desc, base, end):
r4 = descriptor address, r5 = load base, r6 = heap start ('_end' rounded as computed by the stub).
Anything it cannot decode raises StubError (never guesses).
"""
import struct

M32 = 0xFFFFFFFF


class StubError(Exception):
    pass


def s8(x):
    return x - 256 if x & 0x80 else x


def s16(x):
    return x - 65536 if x & 0x8000 else x


def s12(x):
    return x - 4096 if x & 0x800 else x


def s32(x):
    x &= M32
    return x - (1 << 32) if x & 0x80000000 else x


class Mem:
    def __init__(self, regions):
        self.regions = regions            # list of (base, bytearray)
        self.ov = {}                      # written bytes (overlay)

    def _find(self, a, n):
        for b, d in self.regions:
            if b <= a and a + n <= b + len(d):
                return b, d
        raise StubError('unmapped access %#x' % a)

    def rb(self, a):
        a &= M32
        if a in self.ov:
            return self.ov[a]
        b, d = self._find(a, 1)
        return d[a - b]

    def rn(self, a, n):
        return int.from_bytes(bytes(self.rb(a + i) for i in range(n)), 'little')

    def wn(self, a, v, n):
        for i in range(n):
            self.ov[(a + i) & M32] = (v >> (8 * i)) & 0xFF


def run_stub(image, base, extra_regions=(), max_steps=200000, ext_lo=None, ext_hi=None, follow=False):
    """Execute from `base`. Returns dict(target, r4..r7, steps, writes)."""
    mem = Mem([(base, bytearray(image))] + list(extra_regions))
    R = [0] * 16
    R[15] = 0x8CFFFF00
    pr = 0
    T = 0
    gbr = 0
    mach = macl = 0
    pc = base
    steps = 0
    img_hi = base + len(image)

    def ld(a, n, signed=True):
        v = mem.rn(a, n)
        if signed:
            if n == 1:
                v = s8(v)
            elif n == 2:
                v = s16(v)
            else:
                v = s32(v)
        return v & M32

    def st(a, v, n):
        mem.wn(a & M32, v & M32, n)

    state = {'pc': pc}
    reads = []
    calls = []

    def exec1(pc, in_delay):
        """execute one instruction at pc. return ('next',) | ('branch', target, has_delay) | ('call', target) ."""
        nonlocal T, pr, gbr, mach, macl
        op = mem.rn(pc, 2)
        n = (op >> 8) & 15
        m = (op >> 4) & 15
        hi = op >> 12
        lo = op & 15
        if hi == 0xE:
            R[n] = s8(op & 0xFF) & M32
        elif hi == 0x9:
            R[n] = ld(pc + 4 + (op & 0xFF) * 2, 2)
        elif hi == 0xD:
            R[n] = ld(((pc + 4) & ~3) + (op & 0xFF) * 4, 4)
        elif hi == 0x7:
            R[n] = (R[n] + s8(op & 0xFF)) & M32
        elif hi == 0x1:
            st(R[n] + lo * 4, R[m], 4)
        elif hi == 0x5:
            R[n] = ld(R[m] + lo * 4, 4)
        elif hi == 0x6:
            if lo == 0:
                R[n] = ld(R[m], 1)
            elif lo == 1:
                R[n] = ld(R[m], 2)
            elif lo == 2:
                R[n] = ld(R[m], 4)
                reads.append((R[m], R[n]))
            elif lo == 3:
                R[n] = R[m]
            elif lo == 4:
                R[n] = ld(R[m], 1)
                if n != m:
                    R[m] = (R[m] + 1) & M32
            elif lo == 5:
                R[n] = ld(R[m], 2)
                if n != m:
                    R[m] = (R[m] + 2) & M32
            elif lo == 6:
                R[n] = ld(R[m], 4)
                if n != m:
                    R[m] = (R[m] + 4) & M32
            elif lo == 7:
                R[n] = (~R[m]) & M32
            elif lo == 8:
                v = R[m]
                R[n] = (v & 0xFFFF0000) | ((v & 0xFF) << 8) | ((v >> 8) & 0xFF)
            elif lo == 9:
                v = R[m]
                R[n] = ((v & 0xFFFF) << 16) | (v >> 16)
            elif lo == 0xB:
                R[n] = (-R[m]) & M32
            elif lo == 0xC:
                R[n] = R[m] & 0xFF
            elif lo == 0xD:
                R[n] = R[m] & 0xFFFF
            elif lo == 0xE:
                R[n] = s8(R[m] & 0xFF) & M32
            elif lo == 0xF:
                R[n] = s16(R[m] & 0xFFFF) & M32
            else:
                raise StubError('op %04x' % op)
        elif hi == 0x2:
            if lo == 0:
                st(R[n], R[m], 1)
            elif lo == 1:
                st(R[n], R[m], 2)
            elif lo == 2:
                st(R[n], R[m], 4)
            elif lo == 4:
                R[n] = (R[n] - 1) & M32
                st(R[n], R[m], 1)
            elif lo == 5:
                R[n] = (R[n] - 2) & M32
                st(R[n], R[m], 2)
            elif lo == 6:
                R[n] = (R[n] - 4) & M32
                st(R[n], R[m], 4)
            elif lo == 8:
                T = 1 if (R[n] & R[m]) == 0 else 0
            elif lo == 9:
                R[n] &= R[m]
            elif lo == 0xA:
                R[n] ^= R[m]
            elif lo == 0xB:
                R[n] |= R[m]
            else:
                raise StubError('op %04x' % op)
        elif hi == 0x3:
            a, b = R[n], R[m]
            if lo == 0:
                T = int(a == b)
            elif lo == 2:
                T = int(a >= b)
            elif lo == 3:
                T = int(s32(a) >= s32(b))
            elif lo == 6:
                T = int(a > b)
            elif lo == 7:
                T = int(s32(a) > s32(b))
            elif lo == 8:
                R[n] = (a - b) & M32
            elif lo == 0xC:
                R[n] = (a + b) & M32
            else:
                raise StubError('op %04x' % op)
        elif hi == 0x4:
            k = op & 0xFF
            if k == 0x00:
                T = (R[n] >> 31) & 1
                R[n] = (R[n] << 1) & M32
            elif k == 0x01:
                T = R[n] & 1
                R[n] >>= 1
            elif k == 0x04:
                T = (R[n] >> 31) & 1
                R[n] = ((R[n] << 1) | T) & M32
            elif k == 0x05:
                T = R[n] & 1
                R[n] = (R[n] >> 1) | (T << 31)
            elif k == 0x08:
                R[n] = (R[n] << 2) & M32
            elif k == 0x09:
                R[n] >>= 2
            elif k == 0x18:
                R[n] = (R[n] << 8) & M32
            elif k == 0x19:
                R[n] >>= 8
            elif k == 0x28:
                R[n] = (R[n] << 16) & M32
            elif k == 0x29:
                R[n] >>= 16
            elif k == 0x20:
                T = (R[n] >> 31) & 1
                R[n] = (R[n] << 1) & M32
            elif k == 0x21:
                T = R[n] & 1
                R[n] = (R[n] >> 1) | (R[n] & 0x80000000)
            elif k == 0x10:
                R[n] = (R[n] - 1) & M32
                T = int(R[n] == 0)
            elif k == 0x11:
                T = int(s32(R[n]) >= 0)
            elif k == 0x15:
                T = int(s32(R[n]) > 0)
            elif k == 0x22:
                R[15] = (R[15] - 4) & M32
                st(R[15], pr, 4)
            elif k == 0x26:
                pr = ld(R[n], 4)
                R[n] = (R[n] + 4) & M32
            elif k == 0x2A:
                pr = R[n]
            elif k == 0x0B:
                return ('call', R[n], True)
            elif k == 0x2B:
                return ('jmp', R[n], True)
            elif k == 0x0E or k == 0x1E or k == 0x0A or k == 0x1A or k == 0x5A or k == 0x6A:
                pass          # ldc/lds to SR/GBR/MACH/MACL/FPUL: ignored for our purposes
            elif k == 0x13 or k == 0x03:
                pass
            else:
                raise StubError('op %04x' % op)
        elif hi == 0x0:
            k = op & 0xFF
            if lo == 0x4:
                st(R[0] + R[n], R[m], 1)
            elif lo == 0x5:
                st(R[0] + R[n], R[m], 2)
            elif lo == 0x6:
                st(R[0] + R[n], R[m], 4)
            elif lo == 0xC:
                R[n] = ld(R[0] + R[m], 1)
            elif lo == 0xD:
                R[n] = ld(R[0] + R[m], 2)
            elif lo == 0xE:
                R[n] = ld(R[0] + R[m], 4)
            elif lo == 0x7:
                macl = (R[n] * R[m]) & M32
            elif op == 0x000B:
                return ('ret', pr, True)
            elif op == 0x0009:
                pass
            elif k == 0x2A:
                R[n] = pr
            elif k == 0x29:
                R[n] = T
            elif k == 0x1A:
                R[n] = macl
            elif k == 0x0A:
                R[n] = mach
            elif k == 0x12:
                R[n] = gbr
            elif k == 0x02 or k == 0x82 or k == 0x32 or k == 0x42:
                R[n] = 0
            elif k == 0x08 or k == 0x28 or k == 0x18 or k == 0x38:
                pass          # clrt / clrmac / sett / ldtlb
            else:
                raise StubError('op %04x' % op)
        elif hi == 0x8:
            sub = n
            d = op & 0xFF
            if sub == 0x0:
                st(R[m] + d_(op), R[0], 1)
            elif sub == 0x1:
                st(R[m] + d_(op) * 2, R[0], 2)
            elif sub == 0x4:
                R[0] = ld(R[m] + d_(op), 1)
            elif sub == 0x5:
                R[0] = ld(R[m] + d_(op) * 2, 2)
            elif sub == 0x8:
                T = int(R[0] == (s8(d) & M32))
            elif sub == 0x9:
                return ('bt', pc + 4 + s8(d) * 2, False) if T else ('next',)
            elif sub == 0xB:
                return ('bf', pc + 4 + s8(d) * 2, False) if not T else ('next',)
            elif sub == 0xD:
                return ('bt', pc + 4 + s8(d) * 2, True) if T else ('next',)
            elif sub == 0xF:
                return ('bf', pc + 4 + s8(d) * 2, True) if not T else ('next',)
            else:
                raise StubError('op %04x' % op)
        elif hi == 0xA:
            return ('bra', pc + 4 + s12(op & 0xFFF) * 2, True)
        elif hi == 0xB:
            return ('bsr', pc + 4 + s12(op & 0xFFF) * 2, True)
        elif hi == 0xC:
            sub = n
            d = op & 0xFF
            if sub == 0x0:
                st(gbr + d, R[0], 1)
            elif sub == 0x1:
                st(gbr + d * 2, R[0], 2)
            elif sub == 0x2:
                st(gbr + d * 4, R[0], 4)
            elif sub == 0x4:
                R[0] = ld(gbr + d, 1)
            elif sub == 0x5:
                R[0] = ld(gbr + d * 2, 2)
            elif sub == 0x6:
                R[0] = ld(gbr + d * 4, 4)
            elif sub == 0x7:
                R[0] = ((pc + 4) & ~3) + d * 4
            elif sub == 0x8:
                T = int((R[0] & d) == 0)
            elif sub == 0x9:
                R[0] &= d
            elif sub == 0xA:
                R[0] ^= d
            elif sub == 0xB:
                R[0] |= d
            else:
                raise StubError('op %04x' % op)
        else:
            raise StubError('op %04x' % op)
        return ('next',)

    def d_(op):
        return op & 0xF

    while steps < max_steps:
        steps += 1
        r = exec1(pc, False)
        k = r[0]
        if k == 'next':
            pc += 2
            continue
        tgt = r[1] & M32
        delay = r[2]
        # execute delay slot
        if delay:
            r2 = exec1(pc + 2, True)
            if r2[0] != 'next':
                raise StubError('branch in delay slot at %#x' % (pc + 2))
        if k in ('call', 'bsr'):
            if follow and not (base <= tgt < img_hi):
                calls.append((tgt, R[4], R[5], R[6], R[7]))
                R[0] = R[4]
                pr = pc + 4
                pc = pc + 4
                continue
            if not (base <= tgt < img_hi):
                return dict(target=tgt, r4=R[4], r5=R[5], r6=R[6], r7=R[7], steps=steps, mem=mem, image_end=img_hi, reads=reads)
            pr_ret = pc + 4
            pr = pr_ret
            pc = tgt
        elif k == 'ret':
            if not (base <= tgt < img_hi):
                w = {}
                for a in sorted(mem.ov):
                    w[a & ~3] = mem.rn(a & ~3, 4)
                return dict(target=None, ret=True, r4=R[4], r5=R[5], r6=R[6], r7=R[7], r2=R[2], steps=steps,
                            mem=mem, image_end=img_hi, writes=w, reads=reads, calls=calls)
            pc = tgt
        elif k == 'jmp':
            if not (base <= tgt < img_hi):
                return dict(target=tgt, r4=R[4], r5=R[5], r6=R[6], r7=R[7], steps=steps, mem=mem, image_end=img_hi, tail=True, reads=reads)
            pc = tgt
        else:
            pc = tgt
    raise StubError('step limit')
