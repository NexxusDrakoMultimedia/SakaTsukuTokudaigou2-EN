"""Tiny SH-4 disassembler (subset used by the overlay stubs).  python shdis.py <overlay> <base-hex> <start> <end>"""
import struct
import sys


def s8(x):
    return x - 256 if x & 0x80 else x


def s12(x):
    return x - 4096 if x & 0x800 else x


def dis(op, pc, rd32=None, rd16=None):
    n = (op >> 8) & 15
    m = (op >> 4) & 15
    hi = op >> 12
    lo = op & 15
    d = op & 0xFF
    if hi == 0xE:
        return 'mov #%d,r%d' % (s8(d), n)
    if hi == 0x9:
        a = pc + 4 + d * 2
        return 'mov.w @(0x%x),r%d   ; [%x]=%s' % (a, n, a, hex(rd16(a)) if rd16 else '?')
    if hi == 0xD:
        a = ((pc + 4) & ~3) + d * 4
        return 'mov.l @(0x%x),r%d   ; [%x]=%s' % (a, n, a, hex(rd32(a)) if rd32 else '?')
    if hi == 0x7:
        return 'add #%d,r%d' % (s8(d), n)
    if hi == 1:
        return 'mov.l r%d,@(%d,r%d)' % (m, lo * 4, n)
    if hi == 5:
        return 'mov.l @(%d,r%d),r%d' % (lo * 4, m, n)
    if hi == 6:
        t = {0: 'mov.b @r%d,r%d', 1: 'mov.w @r%d,r%d', 2: 'mov.l @r%d,r%d', 3: 'mov r%d,r%d', 4: 'mov.b @r%d+,r%d',
             5: 'mov.w @r%d+,r%d', 6: 'mov.l @r%d+,r%d', 7: 'not r%d,r%d', 8: 'swap.b r%d,r%d', 9: 'swap.w r%d,r%d',
             0xA: 'negc r%d,r%d', 0xB: 'neg r%d,r%d', 0xC: 'extu.b r%d,r%d', 0xD: 'extu.w r%d,r%d', 0xE: 'exts.b r%d,r%d',
             0xF: 'exts.w r%d,r%d'}
        return t[lo] % (m, n)
    if hi == 2:
        t = {0: 'mov.b r%d,@r%d', 1: 'mov.w r%d,@r%d', 2: 'mov.l r%d,@r%d', 4: 'mov.b r%d,@-r%d', 5: 'mov.w r%d,@-r%d',
             6: 'mov.l r%d,@-r%d', 7: 'div0s r%d,r%d', 8: 'tst r%d,r%d', 9: 'and r%d,r%d', 0xA: 'xor r%d,r%d', 0xB: 'or r%d,r%d',
             0xC: 'cmp/str r%d,r%d', 0xD: 'xtrct r%d,r%d'}
        return (t.get(lo) or '.word') % (m, n) if lo in t else '.word %04x' % op
    if hi == 3:
        t = {0: 'cmp/eq', 2: 'cmp/hs', 3: 'cmp/ge', 4: 'div1', 6: 'cmp/hi', 7: 'cmp/gt', 8: 'sub', 0xA: 'subc', 0xC: 'add', 0xE: 'addc'}
        return '%s r%d,r%d' % (t.get(lo, '.word'), m, n)
    if hi == 4:
        t = {0x00: 'shll r%d', 0x01: 'shlr r%d', 0x04: 'rotl r%d', 0x05: 'rotr r%d', 0x08: 'shll2 r%d', 0x09: 'shlr2 r%d',
             0x18: 'shll8 r%d', 0x19: 'shlr8 r%d', 0x28: 'shll16 r%d', 0x29: 'shlr16 r%d', 0x10: 'dt r%d', 0x11: 'cmp/pz r%d',
             0x15: 'cmp/pl r%d', 0x0B: 'jsr @r%d', 0x2B: 'jmp @r%d', 0x22: 'sts.l pr,@-r%d', 0x26: 'lds.l @r%d+,pr',
             0x2A: 'lds r%d,pr', 0x20: 'shal r%d', 0x21: 'shar r%d'}
        if d in t:
            return t[d] % n
        return '.word %04x' % op
    if hi == 0:
        if op == 0x000B:
            return 'rts'
        if op == 9:
            return 'nop'
        t = {4: 'mov.b r%d,@(r0,r%d)', 5: 'mov.w r%d,@(r0,r%d)', 6: 'mov.l r%d,@(r0,r%d)', 0xC: 'mov.b @(r0,r%d),r%d',
             0xD: 'mov.w @(r0,r%d),r%d', 0xE: 'mov.l @(r0,r%d),r%d', 7: 'mul.l r%d,r%d'}
        if lo in t:
            return t[lo] % (m, n)
        if d == 0x2A:
            return 'sts pr,r%d' % n
        if d == 0x29:
            return 'movt r%d' % n
        return '.word %04x' % op
    if hi == 8:
        sub = n
        if sub in (0x9, 0xB, 0xD, 0xF):
            nm = {9: 'bt', 0xB: 'bf', 0xD: 'bt/s', 0xF: 'bf/s'}[sub]
            return '%s 0x%x' % (nm, pc + 4 + s8(d) * 2)
        if sub == 0x8:
            return 'cmp/eq #%d,r0' % s8(d)
        if sub == 0x0:
            return 'mov.b r0,@(%d,r%d)' % (op & 15, m)
        if sub == 0x1:
            return 'mov.w r0,@(%d,r%d)' % ((op & 15) * 2, m)
        if sub == 0x4:
            return 'mov.b @(%d,r%d),r0' % (op & 15, m)
        if sub == 0x5:
            return 'mov.w @(%d,r%d),r0' % ((op & 15) * 2, m)
        return '.word %04x' % op
    if hi == 0xA:
        return 'bra 0x%x' % (pc + 4 + s12(op & 0xFFF) * 2)
    if hi == 0xB:
        return 'bsr 0x%x' % (pc + 4 + s12(op & 0xFFF) * 2)
    if hi == 0xC:
        t = {0: 'mov.b r0,@(%d,gbr)', 1: 'mov.w r0,@(%d,gbr)', 2: 'mov.l r0,@(%d,gbr)', 4: 'mov.b @(%d,gbr),r0', 5: 'mov.w @(%d,gbr),r0',
             6: 'mov.l @(%d,gbr),r0', 8: 'tst #%d,r0', 9: 'and #%d,r0', 0xA: 'xor #%d,r0', 0xB: 'or #%d,r0'}
        if n in t:
            return t[n] % d
        if n == 7:
            return 'mova @(0x%x),r0' % (((pc + 4) & ~3) + d * 4)
    return '.word %04x' % op


def main(path, base, a, b):
    data = open(path, 'rb').read()

    def r32(x):
        o = x - base
        return struct.unpack_from('<I', data, o)[0] if 0 <= o <= len(data) - 4 else None

    def r16(x):
        o = x - base
        return struct.unpack_from('<h', data, o)[0] & 0xFFFF if 0 <= o <= len(data) - 2 else None
    pc = a
    while pc < b:
        op = struct.unpack_from('<H', data, pc - base)[0]
        print('%08x: %04x  %s' % (pc, op, dis(op, pc, r32, r16)))
        pc += 2


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16), int(sys.argv[4], 16))
