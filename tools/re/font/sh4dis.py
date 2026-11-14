"""Compact SH-4 (little endian) disassembler, enough for reading the game code.

    from sh4dis import Image
    img = Image(bytes, base)            # flat image mapped at base
    for line in img.listing(lo, hi): print(line)

mov.l/mov.w @(d,PC),Rn and mova are annotated with the literal value.  Delay slots are printed
as ordinary following instructions (marked with a leading '  ' indent when the previous one has a delay slot).
"""
import struct

DELAY = ('bra', 'bsr', 'braf', 'bsrf', 'jmp', 'jsr', 'rts', 'rte', 'bt/s', 'bf/s')


def s8(x):
    return x - 256 if x & 0x80 else x


def s12(x):
    return x - 4096 if x & 0x800 else x


class Image:
    def __init__(self, data, base):
        self.d = data
        self.base = base

    def u16(self, a):
        o = a - self.base
        if o < 0 or o + 2 > len(self.d):
            return None
        return struct.unpack_from('<H', self.d, o)[0]

    def u32(self, a):
        o = a - self.base
        if o < 0 or o + 4 > len(self.d):
            return None
        return struct.unpack_from('<I', self.d, o)[0]

    def dis(self, a):
        w = self.u16(a)
        if w is None:
            return '??'
        return dis(w, a, self)

    def listing(self, lo, hi):
        a = lo
        out = []
        while a < hi:
            w = self.u16(a)
            if w is None:
                break
            t = dis(w, a, self)
            out.append('%08x  %04x  %s' % (a, w, t))
            a += 2
        return out


def dis(w, a, img=None):
    n = (w >> 8) & 15
    m = (w >> 4) & 15
    d = w & 15
    op = w >> 12
    R = lambda x: 'r%d' % x
    if op == 0:
        t = {4: 'mov.b %s,@(r0,%s)', 5: 'mov.w %s,@(r0,%s)', 6: 'mov.l %s,@(r0,%s)', 7: 'mul.l %s,%s'}
        if d in t:
            return t[d] % (R(m), R(n))
        t = {0xC: 'mov.b @(r0,%s),%s', 0xD: 'mov.w @(r0,%s),%s', 0xE: 'mov.l @(r0,%s),%s'}
        if d in t:
            return t[d] % (R(m), R(n))
        if d == 0xF:
            return 'mac.l @%s+,@%s+' % (R(m), R(n))
        fixed = {0x0008: 'clrt', 0x0018: 'sett', 0x0028: 'clrmac', 0x0038: 'ldtlb', 0x0048: 'clrs', 0x0058: 'sets',
                 0x0009: 'nop', 0x0019: 'div0u', 0x000B: 'rts', 0x002B: 'rte', 0x001B: 'sleep',
                 0x00FB: 'ocbi?', 0x0AFB: 'x'}
        if w in fixed:
            return fixed[w]
        lo = w & 0xFF
        if lo == 0x29:
            return 'movt %s' % R(n)
        if lo == 0x02:
            return 'stc sr,%s' % R(n)
        if lo == 0x12:
            return 'stc gbr,%s' % R(n)
        if lo == 0x22:
            return 'stc vbr,%s' % R(n)
        if lo == 0x03:
            return 'bsrf %s' % R(n)
        if lo == 0x23:
            return 'braf %s' % R(n)
        if lo == 0x0A:
            return 'sts mach,%s' % R(n)
        if lo == 0x1A:
            return 'sts macl,%s' % R(n)
        if lo == 0x2A:
            return 'sts pr,%s' % R(n)
        if lo == 0x5A:
            return 'sts fpul,%s' % R(n)
        if lo == 0x6A:
            return 'sts fpscr,%s' % R(n)
        if lo == 0x83:
            return 'pref @%s' % R(n)
        if lo == 0x93:
            return 'ocbi @%s' % R(n)
        if lo == 0xA3:
            return 'ocbp @%s' % R(n)
        if lo == 0xB3:
            return 'ocbwb @%s' % R(n)
        if lo == 0xC3:
            return 'movca.l r0,@%s' % R(n)
        return '.word 0x%04x' % w
    if op == 1:
        return 'mov.l %s,@(%d,%s)' % (R(m), d * 4, R(n))
    if op == 2:
        t = {0: 'mov.b %s,@%s', 1: 'mov.w %s,@%s', 2: 'mov.l %s,@%s', 4: 'mov.b %s,@-%s', 5: 'mov.w %s,@-%s',
             6: 'mov.l %s,@-%s', 7: 'div0s %s,%s', 8: 'tst %s,%s', 9: 'and %s,%s', 10: 'xor %s,%s', 11: 'or %s,%s',
             12: 'cmp/str %s,%s', 13: 'xtrct %s,%s', 14: 'mulu.w %s,%s', 15: 'muls.w %s,%s'}
        if d in t:
            return t[d] % (R(m), R(n))
    if op == 3:
        t = {0: 'cmp/eq', 2: 'cmp/hs', 3: 'cmp/ge', 4: 'div1', 5: 'dmulu.l', 6: 'cmp/hi', 7: 'cmp/gt', 8: 'sub',
             10: 'subc', 11: 'subv', 12: 'add', 13: 'dmuls.l', 14: 'addc', 15: 'addv'}
        if d in t:
            return '%s %s,%s' % (t[d], R(m), R(n))
    if op == 4:
        lo = w & 0xFF
        t = {0x00: 'shll', 0x01: 'shlr', 0x04: 'rotl', 0x05: 'rotr', 0x08: 'shll2', 0x18: 'shll8', 0x28: 'shll16',
             0x09: 'shlr2', 0x19: 'shlr8', 0x29: 'shlr16', 0x10: 'dt', 0x11: 'cmp/pz', 0x15: 'cmp/pl',
             0x20: 'shal', 0x21: 'shar', 0x24: 'rotcl', 0x25: 'rotcr', 0x0B: 'jsr', 0x2B: 'jmp', 0x1B: 'tas.b'}
        if lo in t:
            x = t[lo]
            if lo in (0x0B, 0x2B):
                return '%s @%s' % (x, R(n))
            if lo == 0x1B:
                return 'tas.b @%s' % R(n)
            return '%s %s' % (x, R(n))
        s = {0x02: 'mach', 0x12: 'macl', 0x22: 'pr', 0x52: 'fpul', 0x62: 'fpscr'}
        if lo in s:
            return 'sts.l %s,@-%s' % (s[lo], R(n))
        s = {0x03: 'sr', 0x13: 'gbr', 0x23: 'vbr'}
        if lo in s:
            return 'stc.l %s,@-%s' % (s[lo], R(n))
        s = {0x06: 'mach', 0x16: 'macl', 0x26: 'pr', 0x56: 'fpul', 0x66: 'fpscr'}
        if lo in s:
            return 'lds.l @%s+,%s' % (R(n), s[lo])
        s = {0x07: 'sr', 0x17: 'gbr', 0x27: 'vbr'}
        if lo in s:
            return 'ldc.l @%s+,%s' % (R(n), s[lo])
        s = {0x0A: 'mach', 0x1A: 'macl', 0x2A: 'pr', 0x5A: 'fpul', 0x6A: 'fpscr'}
        if lo in s:
            return 'lds %s,%s' % (R(n), s[lo])
        s = {0x0E: 'sr', 0x1E: 'gbr', 0x2E: 'vbr'}
        if lo in s:
            return 'ldc %s,%s' % (R(n), s[lo])
        if d == 0xC:
            return 'shad %s,%s' % (R(m), R(n))
        if d == 0xD:
            return 'shld %s,%s' % (R(m), R(n))
        if d == 0xF:
            return 'mac.w @%s+,@%s+' % (R(m), R(n))
        return '.word 0x%04x' % w
    if op == 5:
        return 'mov.l @(%d,%s),%s' % (d * 4, R(m), R(n))
    if op == 6:
        t = {0: 'mov.b @%s,%s', 1: 'mov.w @%s,%s', 2: 'mov.l @%s,%s', 3: 'mov %s,%s', 4: 'mov.b @%s+,%s',
             5: 'mov.w @%s+,%s', 6: 'mov.l @%s+,%s', 7: 'not %s,%s', 8: 'swap.b %s,%s', 9: 'swap.w %s,%s',
             10: 'negc %s,%s', 11: 'neg %s,%s', 12: 'extu.b %s,%s', 13: 'extu.w %s,%s', 14: 'exts.b %s,%s',
             15: 'exts.w %s,%s'}
        return t[d] % (R(m), R(n))
    if op == 7:
        return 'add #%d,%s' % (s8(w & 0xFF), R(n))
    if op == 8:
        sub = n
        lo = w & 0xFF
        if sub == 0:
            return 'mov.b r0,@(%d,%s)' % (d, R(m))
        if sub == 1:
            return 'mov.w r0,@(%d,%s)' % (d * 2, R(m))
        if sub == 4:
            return 'mov.b @(%d,%s),r0' % (d, R(m))
        if sub == 5:
            return 'mov.w @(%d,%s),r0' % (d * 2, R(m))
        if sub == 8:
            return 'cmp/eq #%d,r0' % s8(lo)
        t = {9: 'bt', 11: 'bf', 13: 'bt/s', 15: 'bf/s'}
        if sub in t:
            return '%s 0x%08x' % (t[sub], (a + 4 + 2 * s8(lo)) & 0xFFFFFFFF)
        return '.word 0x%04x' % w
    if op == 9:
        ea = a + 4 + 2 * (w & 0xFF)
        v = img.u16(ea) if img else None
        return 'mov.w @(0x%x),%s    ; = 0x%s' % (ea, R(n), '%04x (%d)' % (v, v - 65536 if v & 0x8000 else v) if v is not None else '?')
    if op == 0xA:
        return 'bra 0x%08x' % ((a + 4 + 2 * s12(w & 0xFFF)) & 0xFFFFFFFF)
    if op == 0xB:
        return 'bsr 0x%08x' % ((a + 4 + 2 * s12(w & 0xFFF)) & 0xFFFFFFFF)
    if op == 0xC:
        lo = w & 0xFF
        sub = n
        i = lo
        t = {0: 'mov.b r0,@(%d,gbr)' % i, 1: 'mov.w r0,@(%d,gbr)' % (i * 2), 2: 'mov.l r0,@(%d,gbr)' % (i * 4),
             3: 'trapa #%d' % i, 4: 'mov.b @(%d,gbr),r0' % i, 5: 'mov.w @(%d,gbr),r0' % (i * 2),
             6: 'mov.l @(%d,gbr),r0' % (i * 4), 8: 'tst #0x%x,r0' % i, 9: 'and #0x%x,r0' % i, 10: 'xor #0x%x,r0' % i,
             11: 'or #0x%x,r0' % i, 12: 'tst.b #0x%x,@(r0,gbr)' % i, 13: 'and.b #0x%x,@(r0,gbr)' % i,
             14: 'xor.b #0x%x,@(r0,gbr)' % i, 15: 'or.b #0x%x,@(r0,gbr)' % i}
        if sub == 7:
            ea = ((a & ~3) + 4 + 4 * i)
            return 'mova @(0x%x),r0' % ea
        return t[sub]
    if op == 0xD:
        ea = (a & ~3) + 4 + 4 * (w & 0xFF)
        v = img.u32(ea) if img else None
        return 'mov.l @(0x%x),%s    ; = 0x%s' % (ea, R(n), '%08x' % v if v is not None else '?')
    if op == 0xE:
        return 'mov #%d,%s' % (s8(w & 0xFF), R(n))
    if op == 0xF:
        F = lambda x: 'fr%d' % x
        t = {0: 'fadd', 1: 'fsub', 2: 'fmul', 3: 'fdiv', 4: 'fcmp/eq', 5: 'fcmp/gt'}
        if d in t:
            return '%s %s,%s' % (t[d], F(m), F(n))
        if d == 6:
            return 'fmov.s @(r0,%s),%s' % (R(m), F(n))
        if d == 7:
            return 'fmov.s %s,@(r0,%s)' % (F(m), R(n))
        if d == 8:
            return 'fmov.s @%s,%s' % (R(m), F(n))
        if d == 9:
            return 'fmov.s @%s+,%s' % (R(m), F(n))
        if d == 10:
            return 'fmov.s %s,@%s' % (F(m), R(n))
        if d == 11:
            return 'fmov.s %s,@-%s' % (F(m), R(n))
        if d == 12:
            return 'fmov %s,%s' % (F(m), F(n))
        if d == 14:
            return 'fmac fr0,%s,%s' % (F(m), F(n))
        if d == 13:
            t = {0: 'fsts fpul,%s', 1: 'flds %s,fpul', 2: 'float fpul,%s', 3: 'ftrc %s,fpul', 4: 'fneg %s', 5: 'fabs %s',
                 6: 'fsqrt %s', 7: 'fsrra %s', 8: 'fldi0 %s', 9: 'fldi1 %s'}
            if m in t:
                return t[m] % F(n)
        return '.word 0x%04x' % w
    return '.word 0x%04x' % w


def load_overlay(name, rows=None):
    """Return Image for an overlay by file name using build/memmap/overlays.tsv"""
    import csv
    import os
    R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
    for r in csv.DictReader(open(R + r'\build\memmap\overlays.tsv'), delimiter='\t'):
        if r['overlay'].upper() == name.upper() and r['base']:
            return Image(open(os.path.join(R, 'extracted', r['dir'], r['overlay']), 'rb').read(), int(r['base'], 16))
    raise KeyError(name)


def load_ram(name):
    R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')) + '/build/emu/'
    return Image(open(R + name, 'rb').read(), 0x8C000000)


def load_1st():
    return Image(open(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')) + '/extracted/1ST_READ.BIN', 'rb').read(), 0x8C010000)


if __name__ == '__main__':
    import sys
    which = sys.argv[1]
    lo = int(sys.argv[2], 16)
    hi = int(sys.argv[3], 16)
    if which == '1st':
        img = load_1st()
    elif which.endswith('.bin') and which.startswith(('ram', 'live', 't1')):
        img = load_ram(which)
    else:
        img = load_overlay(which)
    print('\n'.join(img.listing(lo, hi)))
