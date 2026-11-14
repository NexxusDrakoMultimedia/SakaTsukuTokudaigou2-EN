"""Tiny SH-4 (little endian, 16-bit instructions) assembler/disassembler for the handful of
instructions needed by the 1ST_READ.BIN patches (docs/trans-bank.md).  Not a general assembler.

Supported: nop, rts, sts.l PR,@-r15 / lds.l @r15+,PR, mov #imm8,Rn, mov.l @(disp,PC),Rn (literal
pool loads, disp computed from the wanted literal address), jsr @Rn, jmp @Rn, mov Rm,Rn.
Instruction words are little endian in the file; `asm(...)` returns bytes.

SH PC-relative rule (mov.l): EA = (A & ~3) + 4 + 4*disp, A = address of the instruction.
"""
import struct


def _w(x):
    return struct.pack('<H', x & 0xFFFF)


def nop():
    return _w(0x0009)


def rts():
    return _w(0x000B)


def sts_l_pr_push():          # sts.l PR,@-r15
    return _w(0x4F22)


def lds_l_pr_pop():           # lds.l @r15+,PR
    return _w(0x4F26)


def mov_imm(n, imm):          # mov #imm8,Rn  (sign extended)
    return _w(0xE000 | (n << 8) | (imm & 0xFF))


def mov_rr(m, n):             # mov Rm,Rn
    return _w(0x6003 | (n << 8) | (m << 4))


def jsr(n):                   # jsr @Rn
    return _w(0x400B | (n << 8))


def jmp(n):                   # jmp @Rn
    return _w(0x402B | (n << 8))


def mov_l_pc(n, addr_insn, addr_lit):
    """mov.l @(disp,PC),Rn at address addr_insn loading the longword at addr_lit."""
    if addr_lit & 3:
        raise ValueError('literal not 4-aligned')
    base = (addr_insn & ~3) + 4
    d = addr_lit - base
    if d < 0 or d % 4 or d // 4 > 255:
        raise ValueError('literal %#x out of range for insn at %#x' % (addr_lit, addr_insn))
    return _w(0xD000 | (n << 8) | (d // 4))


def dis(word, addr):
    """Disassemble one 16-bit word of the supported subset (text like Ghidra's)."""
    if word == 0x0009:
        return 'nop'
    if word == 0x000B:
        return 'rts'
    if word == 0x4F22:
        return 'sts.l PR,@-r15'
    if word == 0x4F26:
        return 'lds.l @r15+,PR'
    if word >> 12 == 0xE:
        v = word & 0xFF
        return 'mov #0x%x,r%d' % (v if v < 128 else v - 256, (word >> 8) & 15)
    if word >> 12 == 0xD:
        ea = (addr & ~3) + 4 + 4 * (word & 0xFF)
        return 'mov.l 0x%08x,r%d' % (ea, (word >> 8) & 15)
    if word & 0xF0FF == 0x400B:
        return 'jsr @r%d' % ((word >> 8) & 15)
    if word & 0xF0FF == 0x402B:
        return 'jmp @r%d' % ((word >> 8) & 15)
    if word & 0xF00F == 0x6003:
        return 'mov r%d,r%d' % ((word >> 4) & 15, (word >> 8) & 15)
    return '.word 0x%04x' % word


def listing(code, addr):
    out = []
    for i in range(0, len(code) - 1, 2):
        w = struct.unpack_from('<H', code, i)[0]
        out.append('%08x  %04x  %s' % (addr + i, w, dis(w, addr + i)))
    return out
