"""English money formatter for the tsString `%m` token (docs/number-formats.md).  Pure bytes in / bytes out; no emulator.

    python -I -X utf8 tools/moneypatch.py scan                 # find the formatter copies in extracted/ (counts, variants)
    python -I -X utf8 tools/moneypatch.py listing              # print the assembled cave with addresses
    python -I -X utf8 tools/moneypatch.py patch [--dump DIR]   # run make_patches() on extracted/, print a summary
    python -I -X utf8 tools/moneycheck.py                      # static self-check + interpreter run (separate file)

Problem (PROVEN by tools/moneycheck.py, which executes the ORIGINAL bytes in tools/sh4sim.py): every overlay that links the
tsString library carries a copy of the money function  FUN_xxxx(dst, V, flag) -> length  (the `%m` expander and the game code
that builds `%s` money strings both call it).  V is an amount in units of 10,000 yen (万円).  It prints
    hi = V / 10000, lo = V % 10000
    hi>0, lo>0 :  [hi][億][lo][万円]     hi>0, lo=0 :  [hi][億][円]     hi=0, lo>0 :  [lo][万円]     hi=0, lo=0 :  [0円]
where [億] [万円] [円] [0円] are four Japanese strings that sit in the overlay's data pool and are copied with strncpy
(FIXED lengths 2, 4, 2, 3 bytes, no NUL, short strings are NUL padded) and a hi below 10 is written in FULL-WIDTH digits.
No English string can express this (the number and the unit pieces cannot be reordered, 億 = 10^8 has no decimal form
for `lo`), so the fix is code: this module replaces the first 12 bytes of every copy by a jump to a routine in the
1ST_READ.BIN tail that writes ASCII money text.

    V (10k yen)      prints            V (10k yen)      prints
    0                Y0                131500           Y1.315bn          (13億1500万円)
    15               Y150k             815000           Y8.15bn
    150              Y1.5M             100050           Y1000.5M          (not a multiple of 1M above 1bn: M, 2 decimals)
    6000             Y60M              flag != 0        Y1315000000       (exact yen, no separators)
    negative         -Y150M

What it does (all in place, no file grows, no `_end` change):
  * `1ST_READ.BIN` tail (file offset address - 0x8c010000): the formatter (CAVE, ~330 bytes of code + 40 bytes of table) at
    0x8c299a00.  The font patch owns 0x8c299800..0x8c2999ff; nothing else is touched.
  * every overlay copy of the money function (byte signature, `find_sites`): its first 12 bytes become
        mov.l @(1,pc),r0 ; jmp @r0 ; nop ; nop ; .long CAVE
    (the cave is entered with the original arguments r4 = dst, r5 = V, r6 = flag and returns to the original caller with
    r0 = number of bytes written; callee-saved registers and PR are preserved).
The four Japanese unit strings become dead data; they are therefore left in Japanese (translation records cleared) so that
a build WITHOUT this patch shows correct Japanese amounts instead of garbage.
"""
import glob
import hashlib
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sh4asm2                                    # noqa: E402
import patchengine as PE                          # noqa: E402  (cave registry, overlap registry, site families: docs/patch-engine.md)

EXTRACTED = os.path.join(ROOT, 'extracted')
STRLEN_ADDR, STRNCPY_ADDR = 0x8C014DE4, 0x8C013294       # 1ST_READ helpers in the expander's literal pool
IMG_BASE = PE.IMG_BASE                           # 1ST_READ.BIN load address (file offset = address - IMG_BASE)
CAVE_ADDR = PE.REGISTRY.addr('money.cave')       # 0x8c299a00; the cave registry owns the address (font 0x8c299800, bank 0x8c299c00)
RESERVE = PE.REGISTRY.size('money.cave')         # 0x200 bytes of 1ST_READ.BIN that must be zero and are claimed by this patch


class MoneyPatchError(PE.EngineError):
    pass


# ------------------------------------------------------------------------------------------------ assembler (extra ops)
class Asm(sh4asm2.Asm):
    """sh4asm2 plus the few forms the money routine needs.  Every word is cross-checked against capstone by moneycheck.py."""

    def _enc(self, line, a):
        m = re.match(r'^(\S+)\s*(.*)$', line)
        op, args = m.group(1).lower(), m.group(2).strip()
        ops = [x.strip() for x in args.split(',')] if args else []

        def r(s):
            return sh4asm2._r(s)

        def f4(hi, n, mm, lo):
            return (hi << 12) | (n << 8) | (mm << 4) | lo
        if op == 'sts.l' and ops == ['pr', '@-r15']:
            return 0x4F22, 'sts.l pr,@-r15'
        if op == 'lds.l' and ops == ['@r15+', 'pr']:
            return 0x4F26, 'lds.l @r15+,pr'
        if op in ('mov.b', 'mov.l') and len(ops) == 2:
            sz = 0 if op == 'mov.b' else 2
            s, d = ops
            mm = re.match(r'^@-(r\d+)$', d.lower())
            if mm and s.lower().startswith('r'):                 # mov.x Rm,@-Rn
                return f4(2, r(mm.group(1)), r(s), 4 + sz), '%s r%d,@-r%d' % (op, r(s), r(mm.group(1)))
            mm = re.match(r'^@(r\d+)\+$', s.lower())
            if mm:                                               # mov.x @Rm+,Rn
                return f4(6, r(d), r(mm.group(1)), 4 + sz), '%s @r%d+,r%d' % (op, r(mm.group(1)), r(d))
            mm = re.match(r'^@(r\d+)$', d.lower())
            if mm and s.lower().startswith('r') and not s.startswith('@'):   # mov.x Rm,@Rn
                return f4(2, r(mm.group(1)), r(s), sz), '%s r%d,@r%d' % (op, r(s), r(mm.group(1)))
        if op == 'mova':
            tgt = self._val(ops[0])
            base = (a & ~3) + 4
            if tgt % 4 or tgt < base or (tgt - base) // 4 > 255:
                raise ValueError('mova target %#x unusable from %#x' % (tgt, a))
            if r(ops[1]) != 0:
                raise ValueError('mova needs r0')
            return 0xC700 | ((tgt - base) // 4), 'mova 0x%08x,r0' % tgt
        if op == 'cmp/eq' and ops and ops[0].startswith('#'):
            v = sh4asm2._imm(ops[0])
            if r(ops[1]) != 0 or not -128 <= v <= 127:
                raise ValueError('cmp/eq #imm needs r0 and imm8')
            return 0x8800 | (v & 0xFF), 'cmp/eq #%d,r0' % v
        return super()._enc(line, a)


def assemble(src, origin, symbols=None):
    a = Asm(origin, symbols).parse(src)
    out = a.assemble()
    return b''.join(x[1] for x in out), out, a.sym


# ------------------------------------------------------------------------------------------------ the routine
# in:  r4 = dst, r5 = V (int32, units of 10,000 yen), r6 = flag.   out: r0 = bytes written (no NUL).
# Uses r0-r3 as scratch (leaf subroutines), r7-r13 and PR are saved/restored.  16 byte digit buffer on the stack.
_WEST_SRC = """
money:  sts.l pr,@-r15
        mov.l r8,@-r15
        mov.l r9,@-r15
        mov.l r10,@-r15
        mov.l r11,@-r15
        mov.l r12,@-r15
        mov.l r13,@-r15
        add   #-16,r15
        mov   r4,r8                   ; r8 = start of output
        mov   r4,r9                   ; r9 = output pointer
        mov   r6,r13                  ; r13 = flag
        mov   r15,r11                 ; r11 = digit buffer (ASCII digits of |V|, no leading zeros)
        cmp/pz r5
        bt    m_pos
        mov   #45,r0                  ; '-'
        mov.b r0,@r9
        add   #1,r9
        neg   r5,r5
m_pos:  mov   #89,r0                  ; 'Y'
        mov.b r0,@r9
        add   #1,r9
        mova  m_pow,r0
        mov   r0,r12                  ; r12 -> 10^9 .. 10^0
        mov   #10,r7
        mov   #0,r10                  ; r10 = L = number of digits stored
m_dig:  mov.l @r12+,r2
        mov   #0,r3
m_sub:  cmp/hs r2,r5                  ; unsigned: |V| >= power ?
        bf    m_dn
        sub   r2,r5
        bra   m_sub
        add   #1,r3                   ; delay slot
m_dn:   tst   r3,r3
        bf    m_em
        tst   r10,r10
        bt    m_skp                   ; leading zero: skip
m_em:   mov   r11,r1
        add   r10,r1
        mov   #48,r0
        add   r3,r0
        mov.b r0,@r1
        add   #1,r10
m_skp:  dt    r7
        bf    m_dig
        tst   r10,r10
        bf    m_nz
        bsr   m_putc                  ; V == 0 : "Y0"
        mov   #48,r0
        bra   m_fin
        nop
m_nz:   tst   r13,r13
        bt    m_nf
        mov   #0,r1                   ; flag: exact yen = digits + "0000"
        bsr   m_rng
        mov   r10,r2
        mov   #4,r7
m_z4:   bsr   m_putc
        mov   #48,r0
        dt    r7
        bf    m_z4
        bra   m_fin
        nop
m_nf:   mov   #3,r1
        cmp/ge r1,r10                 ; L >= 3 (V >= 100) ?
        bt    m_big
        mov   #0,r1                   ; V < 100: digits + "0k"
        bsr   m_rng
        mov   r10,r2
        bsr   m_putc
        mov   #48,r0
        bsr   m_putc
        mov   #107,r0                 ; 'k'
        bra   m_fin
        nop
m_big:  mov   #6,r1
        cmp/ge r1,r10                 ; L >= 6 (V >= 100000 = 1bn) ?
        bf    m_mm
        mov   r11,r1
        add   r10,r1
        add   #-2,r1
        mov.b @r1+,r2                 ; last two digits both '0' ?  ('0'|'0' = 0x30, any other digit sets more bits)
        mov.b @r1,r3
        or    r3,r2
        mov   r2,r0
        cmp/eq #48,r0
        bf    m_mm
        mov   #0,r1                   ; billions: int [0,L-5) '.' frac [L-5,L-2) trimmed, "bn"
        mov   r10,r2
        bsr   m_rng
        add   #-5,r2
        mov   r10,r1
        add   #-5,r1
        mov   r10,r2
        bsr   m_frac
        add   #-2,r2
        bsr   m_putc
        mov   #98,r0                  ; 'b'
        bsr   m_putc
        mov   #110,r0                 ; 'n'
        bra   m_fin
        nop
m_mm:   mov   #0,r1                   ; millions: int [0,L-2) '.' frac [L-2,L) trimmed, "M"
        mov   r10,r2
        bsr   m_rng
        add   #-2,r2
        mov   r10,r1
        add   #-2,r1
        bsr   m_frac
        mov   r10,r2
        bsr   m_putc
        mov   #77,r0                  ; 'M'
m_fin:  mov   r9,r0
        sub   r8,r0
        add   #16,r15
        mov.l @r15+,r13
        mov.l @r15+,r12
        mov.l @r15+,r11
        mov.l @r15+,r10
        mov.l @r15+,r9
        mov.l @r15+,r8
        lds.l @r15+,pr
        rts
        nop
; putc: store r0 at the output pointer.  (leaf)
m_putc: mov.b r0,@r9
        rts
        add   #1,r9
; rng: copy digit buffer [r1, r2) to the output.  (leaf)
m_rng:  cmp/ge r2,r1
        bt    m_r9
        mov   r11,r3
        add   r1,r3
        mov.b @r3,r0
        mov.b r0,@r9
        add   #1,r9
        bra   m_rng
        add   #1,r1
m_r9:   rts
        nop
; frac: digit buffer [r1, r2) with trailing zeros dropped; if anything is left, '.' and the digits.
m_frac: sts.l pr,@-r15
m_f1:   cmp/gt r1,r2
        bf    m_f9
        mov   r11,r3
        add   r2,r3
        add   #-1,r3
        mov.b @r3,r0
        cmp/eq #48,r0
        bf    m_f2
        bra   m_f1
        add   #-1,r2
m_f2:   bsr   m_putc
        mov   #46,r0                  ; '.'
        bsr   m_rng
        nop
m_f9:   lds.l @r15+,pr
        rts
        nop
"""

_TAIL_SRC = """
; dec: the `%D` expander.  in: r4 = dst, r5 = V (int32), r6 = 0, r7 = pad string (both unused).  out: r0 = bytes written.
; The original prints FULL-WIDTH digits (FUN_xxxx at the `D` branch of the expander); this prints ASCII like `%d`.
m_dec:  mov.l r8,@-r15
        mov   r4,r8                   ; r8 = dst
        mov   r4,r1                   ; r1 = output pointer
        cmp/pz r5
        bt    d_pos
        mov   #45,r0                  ; '-'
        mov.b r0,@r1
        add   #1,r1
        neg   r5,r5
d_pos:  mov   r1,r4                   ; r4 = position of the first digit
        mova  m_pow,r0
        mov   r0,r6                   ; r6 -> 10^9 ..
        mov   #9,r7                   ; the nine powers 10^9 .. 10^1; the last digit is what remains
d_dig:  mov.l @r6+,r2
        mov   #0,r3
d_sub:  cmp/hs r2,r5
        bf    d_dn
        sub   r2,r5
        bra   d_sub
        add   #1,r3
d_dn:   tst   r3,r3
        bf    d_em
        cmp/eq r4,r1
        bt    d_skp                   ; nothing written yet and digit 0: leading zero
d_em:   mov   #48,r0
        add   r3,r0
        mov.b r0,@r1
        add   #1,r1
d_skp:  dt    r7
        bf    d_dig
        mov   #48,r0
        add   r5,r0
        mov.b r0,@r1
        add   #1,r1
        mov   r1,r0
        sub   r8,r0
        mov.l @r15+,r8
        rts
        nop
        .align 4
m_pow:  .long 1000000000
        .long 100000000
        .long 10000000
        .long 1000000
        .long 100000
        .long 10000
        .long 1000
        .long 100
        .long 10
        .long 1
"""

COMPACT_FLAG = 77                 # r6 = 77 ('M' flag): jp style prints an amount with an oku AND a man part as '13 oku 1500m' (docs/number-formats.md s4.8)
STYLES = ('jp', 'western')        # `style` of make_patches / cave_bytes / reference: jp = '13 oku 1500 man' (default), western = 'Y1.315bn'
DEFAULT_STYLE = 'jp'

# ---- jp style: V = |V| in units of 10,000 yen (man).  The decimal digits of |V| (no leading zeros, L of them) are produced once
# (powers of ten, no division); then  oku = digits [0, L-4)  and  man = digits [L-4, L) without leading zeros  -> the text is
#     [oku " oku"] [" "] [man " man"]      or   "0 Yen" for V = 0       (negative: a leading '-')
# and the flag argument is ignored (the game never passes one).  Worst case "-214748 oku 3648 man" = 20 bytes (V = INT_MIN).
_JP_SRC = """
money:  sts.l pr,@-r15
        mov.l r8,@-r15
        mov.l r9,@-r15
        mov.l r10,@-r15
        mov.l r11,@-r15
        mov.l r12,@-r15
        mov.l r13,@-r15
        add   #-16,r15
        mov   r4,r8                   ; r8 = start of output
        mov   r4,r9                   ; r9 = output pointer
        mov   r15,r11                 ; r11 = digit buffer (ASCII digits of |V|, no leading zeros)
        cmp/pz r5
        bt    m_pos
        mov   #45,r0                  ; '-'
        mov.b r0,@r9
        add   #1,r9
        neg   r5,r5
m_pos:  mova  m_pow,r0
        mov   r0,r12                  ; r12 -> 10^9 .. 10^0
        mov   #10,r7
        mov   #0,r10                  ; r10 = L = number of digits stored
m_dig:  mov.l @r12+,r2
        mov   #0,r3
m_sub:  cmp/hs r2,r5                  ; unsigned: |V| >= power ?
        bf    m_dn
        sub   r2,r5
        bra   m_sub
        add   #1,r3                   ; delay slot
m_dn:   tst   r3,r3
        bf    m_em
        tst   r10,r10
        bt    m_skp                   ; leading zero: skip
m_em:   mov   r11,r1
        add   r10,r1
        mov   #48,r0
        add   r3,r0
        mov.b r0,@r1
        add   #1,r10
m_skp:  dt    r7
        bf    m_dig
        mov   #0,r13                  ; r13 = index of the first man digit
        tst   r10,r10
        bf    m_nz
        bsr   m_putc                  ; V == 0 : "0 Yen"
        mov   #48,r0
        mova  s_oku,r0
        add   #8,r0
        bsr   m_p4
        mov   r0,r1
        bra   m_fin
        nop
m_nz:   mov   #4,r1
        cmp/gt r1,r10                 ; L > 4 (V >= 10000, i.e. an oku part) ?
        bf    m_man
        mov   r10,r13
        add   #-4,r13                 ; man digits start at L-4
        mov   #0,r1
        mov   r13,r2
        bsr   m_rng                   ; the oku digits [0, L-4)
        nop
        mova  s_oku,r0
        bsr   m_p4                    ; " oku"
        mov   r0,r1
m_man:  cmp/ge r10,r13                ; all man digits consumed: no man part
        bt    m_fin
        mov   r11,r3
        add   r13,r3
        mov.b @r3,r0
        cmp/eq #48,r0
        bt    m_z                     ; leading zero of the man part
        mov   #4,r1
        cmp/gt r1,r10
        bf    m_ns                    ; no oku part: no separator
        bsr   m_putc
        mov   #32,r0                  ; ' '
m_ns:   mov   r13,r1
        bsr   m_rng
        mov   r10,r2
        mov   #77,r1                  ; flag 77 (COMPACT_FLAG) and an oku part: "13 oku 1500m", the unit " man" shrinks to "m"
        cmp/eq r1,r6
        bf    m_fm
        mov   #4,r1
        cmp/gt r1,r10
        bf    m_fm
        bsr   m_putc
        mov   #109,r0                 ; 'm' (lower case, like " man")
        bra   m_fin
        nop
m_fm:   mova  s_oku,r0
        add   #4,r0
        bsr   m_p4                    ; " man"
        mov   r0,r1
m_fin:  mov   r9,r0
        sub   r8,r0
        add   #16,r15
        mov.l @r15+,r13
        mov.l @r15+,r12
        mov.l @r15+,r11
        mov.l @r15+,r10
        mov.l @r15+,r9
        mov.l @r15+,r8
        lds.l @r15+,pr
        rts
        nop
m_z:    bra   m_man
        add   #1,r13
; putc: store r0 at the output pointer.  (leaf)
m_putc: mov.b r0,@r9
        rts
        add   #1,r9
; rng: copy digit buffer [r1, r2) to the output.  (leaf)
m_rng:  cmp/ge r2,r1
        bt    m_r9
        mov   r11,r3
        add   r1,r3
        mov.b @r3,r0
        mov.b r0,@r9
        add   #1,r9
        bra   m_rng
        add   #1,r1
m_r9:   rts
        nop
; p4: copy the 4 bytes at r1 to the output.  (leaf)
m_p4:   mov   #4,r2
m_p41:  mov.b @r1+,r0
        mov.b r0,@r9
        add   #1,r9
        dt    r2
        bf    m_p41
        rts
        nop
        .align 4
s_oku:  .long 0x756B6F20              ; " oku"   (lower case since mn6: the capital O reads as a zero in the half-width font)
        .long 0x6E616D20              ; " man"
        .long 0x6E655920              ; " Yen"
"""


def _src(style):
    if style == 'jp':
        return _JP_SRC + _TAIL_SRC
    if style == 'western':
        return _WEST_SRC + _TAIL_SRC
    raise MoneyPatchError('unknown money style %r (one of %s)' % (style, ', '.join(STYLES)))


CAVE_SRC = _src(DEFAULT_STYLE)


def cave_assembly(addr=CAVE_ADDR, style=DEFAULT_STYLE):
    return assemble(_src(style), addr)


def cave_bytes(addr=CAVE_ADDR, style=DEFAULT_STYLE):
    b, _, _ = cave_assembly(addr, style)
    if len(b) > RESERVE:
        raise MoneyPatchError('cave is %d bytes, reserve is %d' % (len(b), RESERVE))
    return b


def reference(v, flag=0, style=DEFAULT_STYLE):
    """the specification, in Python (V = signed 32 bit amount in units of 10,000 yen).
    jp:      '0 Yen' | '1 oku' | '6000 man' | '13 oku 1500 man' | '-50 man'   (flag ignored except COMPACT_FLAG: '13 oku 1500m', see below)
    western: 'Y0' | 'Y150k' | 'Y1.5M' | 'Y1.315bn'   (flag != 0: exact yen, 'Y1315000000')"""
    if style == 'jp':
        v &= 0xFFFFFFFF
        neg = v >= 0x80000000
        mag = (-v) & 0xFFFFFFFF if neg else v
        if mag == 0:
            return '0 Yen'
        oku, man = divmod(mag, 10000)
        compact = flag == COMPACT_FLAG and oku and man        # compact form: only an amount with BOTH parts changes
        parts = ([str(oku) + ' oku'] if oku else []) + ([str(man) + ('m' if compact else ' man')] if man else [])
        return ('-' if neg else '') + ' '.join(parts)
    if style != 'western':
        raise MoneyPatchError('unknown money style %r' % (style,))
    return _reference_western(v, flag)


def _reference_western(v, flag=0):
    v &= 0xFFFFFFFF
    neg = v >= 0x80000000
    mag = (-v) & 0xFFFFFFFF if neg else v
    out = ('-' if neg else '') + 'Y'
    d = str(mag)
    if mag == 0:
        return out + '0'
    if flag:
        return out + d + '0000'
    n = len(d)
    if n <= 2:
        return out + d + '0k'
    if n >= 6 and d[-2:] == '00':
        fr = d[n - 5:n - 2].rstrip('0')
        return out + d[:n - 5] + ('.' + fr if fr else '') + 'bn'
    fr = d[n - 2:].rstrip('0')
    return out + d[:n - 2] + ('.' + fr if fr else '') + 'M'


# ------------------------------------------------------------------------------------------------ the number library (mn6)
# 9 overlays (CHALMODE DRSHRANK DRSISEKI DRSJAPAN DRSLIST DRSSRANK GETREP PL_EDIT SELNAT) carry a shared number library that does NOT use the
# money function: it splits V (10,000 yen) itself, prints hi (space padded, `itoa(dst, hi, 4, ' ')`) and lo (zero padded to 4) into two small
# stack strings and creates a text object with a stack-argument printf  `real(fmt, a1, a2)`  (the same code in all 9 overlays, r0 = object):
#       hi > 0   `%s億%s万円` (negative: `@R/%s億%s万円@`, @R/ = red)          hi == 0, lo != 0   `%s万円` / `@R/%s万円@`      V == 0   `%s円` / `0円`
# printf cannot undo the 4 digit padding or drop a zero lo, so the English formats cannot read '1 oku 300 man' (the finances screen printed
# 'Y 390000000').  The fix is a wrapper installed through the literal-pool word of `real` (every call of the library functions goes through
# it): a 16 byte stub in the dead body of the overlay money function copy (+12) loads r1 = real, r0 = LIB and jumps.  LIB looks at the
# format: the text behind the LAST `%s` must be ' man' or ' Yen' (anything else = pass through to `real` with the stack untouched).  Then
#       text = prefix (up to the first '%') + money(V) + suffix (behind the 4 characters of ' man' / ' Yen')      V = digits(a1) [digits(a2)]
# with V = a1 * 10^4 + a2 (a2 is the 4 digit lo) and money() = the jp formatter of the same cave ('3 oku 9000 man', '58 man', '0 Yen').
# The middle of a two-argument format is never printed: the English formats are '%s %s man', '@R/%s %s man@', '%s man', '@R/%s man@', '%s Yen'.
# Finally real('%s', text) is called.  jp style only.
LIB_PLACEMENT = 'tail'
if 'money.lib' not in PE.REGISTRY.caves:
    PE.REGISTRY.claim('money.lib', 0x8C299400, 0x200, 'money', LIB_PLACEMENT,
                      note='number-library wrapper (mn6): free zero run below the font cave, 0x8c299400..0x8c299800 (docs/number-formats.md s5)')
LIB_ADDR = PE.REGISTRY.addr('money.lib')
LIB_RESERVE = PE.REGISTRY.size('money.lib')
LIB_STUB_REL = 12                                   # the stub lives at money function + 12 (behind the 12 byte hook), 16 bytes
LIB_SRC = """
lib:    mov.l @r15,r2                 ; fmt = stack argument 1 (the library call has no register arguments)
        mov   #0,r3                   ; r3 = address behind the last "%s" (0 = none)
l_s:    mov.b @r2+,r0
        tst   r0,r0
        bt    l_e
        cmp/eq #37,r0                 ; '%'
        bf    l_s
        mov.b @r2,r0
        cmp/eq #115,r0                ; 's'
        bf    l_s
        add   #1,r2
        bra   l_s
        mov   r2,r3
l_e:    tst   r3,r3
        bt    l_pass
        mov.b @r3+,r0
        cmp/eq #32,r0                 ; ' '
        bf    l_pass
        mov.b @r3+,r0
        cmp/eq #109,r0                ; 'm' of " man"
        bt    l_u
        cmp/eq #89,r0                 ; 'Y' of " Yen"
        bf    l_pass
l_u:    mov.b @r3,r0
        cmp/eq #97,r0                 ; 'a'
        bt    l_ok
        cmp/eq #101,r0                ; 'e'
        bt    l_ok
l_pass: jmp   @r1                     ; not a money format: the real function, stack and PR untouched
        nop
l_ok:   sts.l pr,@-r15
        mov.l r8,@-r15
        mov.l r9,@-r15
        mov.l r10,@-r15
        mov.l r11,@-r15
        mov.l r12,@-r15
        mov.l r13,@-r15
        mov   r15,r8
        add   #28,r8                  ; r8 -> the arguments (fmt, a1, a2)
        add   #-48,r15                ; text buffer
        mov   r1,r13                  ; the real function
        mov   r3,r10
        add   #2,r10                  ; r10 = suffix = behind " man" / " Yen"
        mov   r15,r12
        mov   r15,r9                  ; r9 = write pointer
        mov.l @r8,r2
l_p:    mov.b @r2,r0                  ; prefix: up to the first '%'
        cmp/eq #37,r0
        bt    l_pe
        tst   r0,r0
        bt    l_pe
        mov.b r0,@r9
        add   #1,r9
        bra   l_p
        add   #1,r2
l_pe:   mov   #0,r11                  ; r11 = V
        mov   r8,r4
        add   #4,r4
        mov.l @r4,r4
        bsr   l_num                   ; V = digits of a1
        nop
        mov   r10,r0
        add   #-6,r0                  ; start of the last "%s"
        cmp/eq r2,r0                  ; the first '%' ?  then there is one amount argument
        bt    l_1
        mov   r8,r4
        add   #8,r4
        mov.l @r4,r4
        bsr   l_num                   ; V = V * 10^(digits of a2) + a2  (a2 = the 4 digit lo)
        nop
l_1:    mov   r9,r4
        mov   r11,r5
        mov   #0,r6
        mov.l @(l_mon,pc),r0
        jsr   @r0                     ; the jp money formatter of the same cave
        nop
        add   r0,r9
l_sf:   mov.b @r10+,r0                ; suffix + NUL
        mov.b r0,@r9
        tst   r0,r0
        bf/s  l_sf
        add   #1,r9
        mova  l_pct,r0
        mov.l r12,@-r15
        jsr   @r13                    ; real("%s", text)
        mov.l r0,@-r15
        add   #8,r15
        add   #48,r15
        mov.l @r15+,r13
        mov.l @r15+,r12
        mov.l @r15+,r11
        mov.l @r15+,r10
        mov.l @r15+,r9
        mov.l @r15+,r8
        lds.l @r15+,pr
        rts
        nop
; num: r11 = r11 * 10 + digit for every digit of the string r4 (leading spaces skipped).  (leaf)
l_num:  mov.b @r4+,r0
        cmp/eq #32,r0
        bt    l_num
l_nd:   add   #-48,r0
        extu.b r0,r0
        mov   #10,r1
        cmp/hs r1,r0
        bt    l_nx
        mov   r11,r2
        shll2 r2
        add   r11,r2
        shll  r2
        add   r0,r2
        mov   r2,r11
        bra   l_nd
        mov.b @r4+,r0
l_nx:   rts
        nop
        .align 4
l_mon:  .long MONEY
l_pct:  .long 0x00007325              ; "%s"
l_zero: .long 0x65592030              ; "0 Yen" (GETREP's no-argument zero `0円` has only 4 bytes: its literal-pool word points here)
        .long 0x0000006E
"""


def lib_assembly(addr=LIB_ADDR, money_addr=CAVE_ADDR):
    return assemble(LIB_SRC, addr, {'MONEY': money_addr})


def lib_bytes(addr=LIB_ADDR, money_addr=CAVE_ADDR):
    b, _, _ = lib_assembly(addr, money_addr)
    if len(b) > LIB_RESERVE:
        raise MoneyPatchError('number library wrapper is %d bytes, reserve is %d' % (len(b), LIB_RESERVE))
    return b


def lib_stub(real, lib_addr=LIB_ADDR):
    """16 bytes at (money function + 12): mov.l @(1,pc),r1 / mov.l @(2,pc),r0 / jmp @r0 / nop / .long real / .long lib"""
    return struct.pack('<HHHHII', 0xD101, 0xD002, 0x402B, 0x0009, real, lib_addr)


def lib_reference(fmt, a1, a2=None):
    """what the wrapper makes of real(fmt, a1, a2): the text handed to real('%s', text), or None = pass through.  a1, a2 are the argument STRINGS
    (a1 space padded, a2 four digits).  The English formats are '%s %s man', '@R/%s %s man@', '%s man', '@R/%s man@', '%s Yen'."""
    i = fmt.rfind('%s')
    if i < 0 or fmt[i + 2:i + 3] != ' ' or fmt[i + 3:i + 4] not in ('m', 'Y') or fmt[i + 4:i + 5] not in ('a', 'e'):
        return None
    first = fmt.index('%')

    def digits(s, v):
        for ch in s.lstrip(' '):
            if not ch.isdigit():
                break
            v = v * 10 + int(ch)
        return v
    v = digits(a1, 0)
    if i != first:
        v = digits(a2, v)
    return fmt[:first] + reference(v, 0, 'jp') + fmt[i + 6:]


# ------------------------------------------------------------------------------------------------ the numeric formats (mn6)
# The other western money formats print integers through libc `sprintf` (0x8c014d80, dst in r4, format and arguments on the stack) or, in G_INCOME, through
# the text-object printf of the library; their English formats keep the Japanese `%d` tokens and name the unit after each one:
#       ABROAD FIRE PLNUMSET SELNAT  `%2d oku %02d00m` (oku, hundreds of man)  `%6d00 man` (hundreds of man), fields of 12 characters in a 13 byte stride
#       INVEST                      `%d cho%04d oku%02d00m`  `    %4d oku %02d00m`  `          %4d man`  (right aligned in 18 characters)
#       G_INCOME                    `%d Yen` (an amount in plain yen, right aligned by the code from a digit count)
# `libn` (cave `money.libn`) reads that format like a tiny grammar (n_core): every `%` must be `%[0-9]*d`, followed by zeros ("00" = x100), spaces and a unit letter
# c / o / m / y; the value in man is sum(arg * 10^zeros * unit) (cho 10^8, oku 10^4, man 1, yen 1/10^4), anything else is passed through to the real function with the
# stack untouched.  The text is the jp money text (the compact form "13 oku 1500m" when the full form is wider than the field W), right aligned in W, or, for a yen
# amount below one man, "N Yen".  Entries: n_sp (libc sprintf, W from the stub), n_al (the library printf of G_INCOME), n_gd (G_INCOME's digit counter: returns the
# number of characters of the text), n_gm (GAME's own money text function `FUN(dst, V)`: money + NUL).
LIBN_PLACEMENT = 'tail'
if 'money.libn' not in PE.REGISTRY.caves:
    # the free zero run below the font cave (0x8c299400..0x8c299800) is full (money.lib, font.align): carve 0x400 bytes from the START of the still
    # unused planned translation bank (0x8c299c00); the bank must take its start from REGISTRY['bank'] (docs/patch-engine.md s2), which now is 0x8c29a000
    _bank = PE.REGISTRY.caves.get('bank')
    if _bank is not None and _bank.planned and _bank.addr == 0x8C299C00:
        _bank.addr += 0x400
        _bank.size -= 0x400
    PE.REGISTRY.claim('money.libn', 0x8C299C00, 0x400, 'money', LIBN_PLACEMENT,
                      note='numeric-format wrapper (mn6, 644 B): carved from the planned bank start; docs/number-formats.md s5')
LIBN_ADDR = PE.REGISTRY.addr('money.libn')
LIBN_RESERVE = PE.REGISTRY.size('money.libn')
LIBN_STUB_REL = 32                                   # the libn stub lives at money function + 32 (behind the 12 byte hook and the 16 byte lib stub), 24 bytes
DIV_ADDR = 0x8C012BF8                                # 1ST_READ helper: r0 = r1 / r0 (signed), clobbers r0, r1 only
LIBN_SRC = """
; ---- entry n_sp: libc sprintf(dst = r4, fmt/args on the stack).  r1 = the real sprintf, r2 = the field width W (0 = none), both from the stub.
n_sp:   sts.l pr,@-r15
        mov.l r8,@-r15
        mov.l r9,@-r15
        mov.l r10,@-r15
        mov.l r11,@-r15
        mov.l r12,@-r15
        mov.l r13,@-r15
        mov   r1,r13                  ; real
        mov   r2,r12                  ; W
        mov   r15,r9
        add   #28,r9                  ; r9 -> [fmt][a1][a2]..
        add   #-52,r15
        mov.l r4,@r15                 ; dst
        mov   r15,r10
        add   #4,r10                  ; text buffer (48 bytes)
        bsr   n_core
        nop
        cmp/pz r0
        bf    n_ps
        mov   r0,r7                   ; L
        mov.l @r15,r4                 ; dst
        mov   r12,r1
        sub   r7,r1                   ; pad = W - L
        cmp/pl r1
        bf    n_c1
        mov   #32,r2
n_pl:   mov.b r2,@r4
        add   #1,r4
        dt    r1
        bf    n_pl
n_c1:   mov   r7,r1
n_cp:   mov.b @r10+,r0
        mov.b r0,@r4
        add   #1,r4
        dt    r1
        bf    n_cp
        mov   #0,r0
        mov.b r0,@r4
        mov.l @r15,r0
        mov   r4,r1
        sub   r0,r1
        mov   r1,r0                   ; length written (sprintf's result)
        add   #52,r15
        mov.l @r15+,r13
        mov.l @r15+,r12
        mov.l @r15+,r11
        mov.l @r15+,r10
        mov.l @r15+,r9
        mov.l @r15+,r8
        lds.l @r15+,pr
        rts
        nop
n_ps:   mov.l @r15,r4                 ; not a money format: the original r4, the real function, stack untouched
        add   #52,r15
n_pt:   mov   r13,r0
        mov.l @r15+,r13
        mov.l @r15+,r12
        mov.l @r15+,r11
        mov.l @r15+,r10
        mov.l @r15+,r9
        mov.l @r15+,r8
        lds.l @r15+,pr
        jmp   @r0
        nop
; ---- entry n_al: the library's text-object printf real(fmt, args) (G_INCOME `%d円`).  r1 = real.
n_al:   sts.l pr,@-r15
        mov.l r8,@-r15
        mov.l r9,@-r15
        mov.l r10,@-r15
        mov.l r11,@-r15
        mov.l r12,@-r15
        mov.l r13,@-r15
        mov   r1,r13
        mov   #0,r12
        mov   r15,r9
        add   #28,r9
        add   #-48,r15
        mov   r15,r10
        bsr   n_core
        nop
        cmp/pz r0
        bf    n_pa
        mov   r10,r1
        add   r0,r1
        mov   #0,r2
        mov.b r2,@r1                  ; NUL
        mova  n_pct,r0
        mov.l r10,@-r15
        jsr   @r13                    ; real("%s", text)
        mov.l r0,@-r15
        add   #8,r15
        add   #48,r15
        mov.l @r15+,r13
        mov.l @r15+,r12
        mov.l @r15+,r11
        mov.l @r15+,r10
        mov.l @r15+,r9
        mov.l @r15+,r8
        lds.l @r15+,pr
        rts
        nop
n_pa:   add   #48,r15
        bra   n_pt
        nop
; ---- entry n_gd(r4 = yen): the number of characters of the text of this yen amount (replaces the digit counter of the G_INCOME yen row, which
;      right-aligns the object by 12 px per missing digit).  Preserves everything but r0-r7.
n_gd:   sts.l pr,@-r15
        mov.l r8,@-r15
        mov.l r9,@-r15
        mov.l r10,@-r15
        mov.l r11,@-r15
        mov.l r12,@-r15
        mov   #0,r12
        add   #-56,r15
        mov   r15,r9
        mova  n_fy,r0
        mov.l r0,@r9
        mov   r9,r1
        add   #4,r1
        mov.l r4,@r1
        mov   r15,r10
        add   #8,r10
        bsr   n_core
        nop
        add   #-2,r0                  ; the Japanese text ends with a 2 byte unit (円) right of the digits: the English text is 24 px further right
        add   #56,r15
        mov.l @r15+,r12
        mov.l @r15+,r11
        mov.l @r15+,r10
        mov.l @r15+,r9
        mov.l @r15+,r8
        lds.l @r15+,pr
        rts
        nop
; ---- entry n_gm: GAME.BIN's own money text function FUN(dst = r4, V = r5 in man): the jp text + NUL
n_gm:   sts.l pr,@-r15
        mov.l r8,@-r15
        mov   r4,r8
        mov   #0,r6
        mov.l @(n_mny,pc),r0
        jsr   @r0
        nop
        add   r0,r8
        mov   #0,r0
        mov.b r0,@r8
        mov.l @r15+,r8
        lds.l @r15+,pr
        rts
        nop
; ---- n_core: r9 -> [fmt][a1][a2]..; r10 = destination of the text (no NUL); r12 = field width W (compact form when the full form is wider than W).
;      out r0 = length, or -1 = not a money format (only r0-r2, r8, r11 touched then).  Keeps r9, r10, r12, r13.
;      A money format = every `%` is `%[0-9]*d`, directly followed by zeros ("00" = x100), spaces and a unit letter c / o / m / y (cho, oku, man, yen;
;      lower or upper case y): value in man = sum(arg * 10^zeros * unit) with cho = 10^8, oku = 10^4, man = 1, yen = 1/10^4 (floor).
n_core: sts.l pr,@-r15
        mov.l @r9,r8
        mov   #0,r11                  ; number of %d
n_v:    mov.b @r8+,r0
        tst   r0,r0
        bt    n_ve
        cmp/eq #37,r0
        bf    n_v
n_w:    mov.b @r8+,r0
        mov   r0,r1
        add   #-48,r0
        extu.b r0,r0
        mov   #10,r2
        cmp/hs r2,r0
        bf    n_w                     ; a digit of the width
        mov   r1,r0
        cmp/eq #100,r0                ; 'd'
        bf    n_no
        add   #1,r11
n_z1:   mov.b @r8,r0
        cmp/eq #48,r0
        bf    n_s1
        add   #1,r8
        bra   n_z1
        nop
n_s1:   mov.b @r8,r0
        cmp/eq #32,r0
        bf    n_u1
        add   #1,r8
        bra   n_s1
        nop
n_u1:   cmp/eq #99,r0                 ; 'c'
        bt    n_v
        cmp/eq #111,r0                ; 'o'
        bt    n_v
        cmp/eq #109,r0                ; 'm'
        bt    n_v
        cmp/eq #121,r0                ; 'y'
        bt    n_v
        cmp/eq #89,r0                 ; 'Y'
        bt    n_v
n_no:   mov   #-1,r0
        bra   n_ret
        nop
n_ve:   tst   r11,r11
        bt    n_no
        mov.l @r9,r8
        mov   r9,r7
        add   #4,r7                   ; r7 = argument cursor
        mov   #0,r11                  ; V (man)
        mov   #0,r6                   ; a yen unit was seen
        mov   #0,r3                   ; the yen remainder
n_c:    mov.b @r8+,r0
        tst   r0,r0
        bt    n_gen
        cmp/eq #37,r0
        bf    n_c
n_w2:   mov.b @r8+,r0
        cmp/eq #100,r0
        bf    n_w2
        mov.l @r7+,r5                 ; the argument
        mov   #1,r4                   ; 10^zeros
n_z2:   mov.b @r8,r0
        cmp/eq #48,r0
        bf    n_s2
        add   #1,r8
        mov   r4,r0
        shll2 r0
        add   r4,r0
        shll  r0
        mov   r0,r4
        bra   n_z2
        nop
n_s2:   mov.b @r8,r0
        cmp/eq #32,r0
        bf    n_u2
        add   #1,r8
        bra   n_s2
        nop
n_u2:   mul.l r4,r5
        sts   macl,r5
        cmp/eq #121,r0
        bt    n_y
        cmp/eq #89,r0
        bt    n_y
        cmp/eq #99,r0
        bt    n_cho
        cmp/eq #111,r0
        bt    n_oku
n_ad:   add   r5,r11
        bra   n_c
        nop
n_cho:  mov.l @(n_1e8,pc),r2
        mul.l r2,r5
        sts   macl,r5
        bra   n_ad
        nop
n_oku:  mov.l @(n_10k,pc),r2
        mul.l r2,r5
        sts   macl,r5
        bra   n_ad
        nop
n_y:    mov   r5,r1                   ; yen: man = yen / 10000 (floor), the rest stays yen
        mov.l @(n_10k,pc),r0
        mov.l @(n_div,pc),r2
        jsr   @r2                     ; r0 = r1 / r0 (clobbers r0, r1)
        nop
        mov.l @(n_10k,pc),r2
        mul.l r0,r2
        sts   macl,r2
        sub   r2,r5
        mov   r5,r3                   ; the remainder in yen
        mov   r0,r5                   ; the man part
        mov   #1,r6
        bra   n_ad
        nop
n_gen:  tst   r6,r6
        bt    n_mon
        tst   r11,r11
        bf    n_mon
        mov   r10,r4                  ; a yen amount below one man: "N Yen"
        mov   r3,r5
        mov   #0,r6
        mov.l @(n_dec,pc),r0
        jsr   @r0                     ; m_dec(dst, N) = N in decimal
        nop
        mov   r10,r1
        add   r0,r1
        mova  n_yen,r0
        mov   r0,r2
        mov   #4,r7
n_yl:   mov.b @r2+,r0
        mov.b r0,@r1
        add   #1,r1
        dt    r7
        bf    n_yl
        mov   r1,r0
        sub   r10,r0
        bra   n_ret
        nop
n_mon:  mov   r10,r4
        mov   r11,r5
        mov   #0,r6
        mov.l @(n_mny,pc),r0
        jsr   @r0                     ; the jp money formatter: "13 oku 1500 man"
        nop
        tst   r12,r12
        bt    n_ret
        mov   r12,r1
        cmp/gt r1,r0                  ; wider than the field ?
        bf    n_ret
        mov   r10,r4
        mov   r11,r5
        mov   #77,r6                  ; COMPACT_FLAG: "13 oku 1500m"
        mov.l @(n_mny,pc),r0
        jsr   @r0
        nop
n_ret:  lds.l @r15+,pr
        rts
        nop
        .align 4
n_1e8:  .long 100000000
n_10k:  .long 10000
n_div:  .long DIV
n_dec:  .long MDEC
n_mny:  .long MONEY
n_pct:  .long 0x00007325              ; "%s"
n_fy:   .long 0x59206425              ; "%d Yen" (the format of the digit counter replacement)
        .long 0x00006E65
n_yen:  .long 0x6E655920              ; " Yen"
"""
LIBN_ENTRIES = ('n_sp', 'n_al', 'n_gd', 'n_gm')


def libn_assembly(addr=LIBN_ADDR, money_addr=CAVE_ADDR, style='jp'):
    sym = cave_symbols(money_addr, style)
    return assemble(LIBN_SRC, addr, {'MONEY': money_addr, 'MDEC': sym['m_dec'], 'DIV': DIV_ADDR})


def libn_bytes(addr=LIBN_ADDR, money_addr=CAVE_ADDR):
    b, _, _ = libn_assembly(addr, money_addr)
    if len(b) > LIBN_RESERVE:
        raise MoneyPatchError('numeric wrapper is %d bytes, reserve is %d' % (len(b), LIBN_RESERVE))
    return b


def libn_stub(real, width, entry):
    """24 bytes at (money function + 32): mov.l @(2,pc),r1 / mov.l @(3,pc),r2 / mov.l @(3,pc),r0 / jmp @r0 / nop / nop / .long real / .long W / .long entry"""
    return struct.pack('<HHHHHHIII', 0xD102, 0xD203, 0xD003, 0x402B, 0x0009, 0x0009, real, width, entry)


def libn_reference(fmt, args, width=0):
    """what n_core makes of fmt + integer arguments: the text, or None = pass through.  Mirrors the assembly (grammar above)."""
    i, n, narg, v, yen_seen, rem = 0, len(fmt), 0, 0, False, 0
    # phase 1: validate
    j = 0
    count = 0
    while j < n:
        if fmt[j] != '%':
            j += 1
            continue
        j += 1
        while j < n and fmt[j].isdigit():
            j += 1
        if j >= n or fmt[j] != 'd':
            return None
        j += 1
        count += 1
        while j < n and fmt[j] == '0':
            j += 1
        while j < n and fmt[j] == ' ':
            j += 1
        if j >= n or fmt[j] not in 'comyY':
            return None
    if not count:
        return None
    # phase 2: value in man
    j = 0
    while j < n:
        if fmt[j] != '%':
            j += 1
            continue
        while fmt[j] != 'd':
            j += 1
        j += 1
        a = args[narg]
        narg += 1
        mult = 1
        while fmt[j] == '0':
            mult *= 10
            j += 1
        while fmt[j] == ' ':
            j += 1
        a *= mult
        u = fmt[j]
        if u in 'yY':
            q = abs(a) // 10000 * (-1 if a < 0 else 1)
            rem = a - q * 10000
            a, yen_seen = q, True
        elif u == 'c':
            a *= 100000000
        elif u == 'o':
            a *= 10000
        v += a
    v &= 0xFFFFFFFF
    sv = v - (1 << 32) if v >= (1 << 31) else v
    if yen_seen and sv == 0:
        return '%d Yen' % rem
    t = reference(sv, 0, 'jp')
    if width and len(t) > width:
        t = reference(sv, COMPACT_FLAG, 'jp')
    return t


def libn_apply(fmt, args, width=0):
    """n_sp's result: the right aligned text, or None"""
    t = libn_reference(fmt, args, width)
    return None if t is None else t.rjust(width)


# the numeric sites: file -> dict(pools=[(file offset of the literal-pool word, its value)], width, entry)
LIBN_SITES = {
    'FLOW_PRG/ABROAD.BIN': dict(pools=[(0x7E4C, 0x8C014D80)], width=12, entry='n_sp'),
    'FLOW_PRG/FIRE.BIN': dict(pools=[(0x6BE0, 0x8C014D80)], width=12, entry='n_sp'),
    'FLOW_PRG/PLNUMSET.BIN': dict(pools=[(0x9874, 0x8C014D80)], width=12, entry='n_sp'),
    'FLOW_PRG/SELNAT.BIN': dict(pools=[(0xDDFC, 0x8C014D80)], width=12, entry='n_sp'),
    'FLOW_PRG/INVEST.BIN': dict(pools=[(0x1CE0, 0x8C014D80)], width=18, entry='n_sp'),
    'FLOW_PRG/G_INCOME.BIN': dict(pools=[(0x1A54, 0x8C4D43DC)], width=0, entry='n_al', counter=(0x1A58, 0x8C4D0152)),
}
# GAME.BIN: its own money text function  FUN(dst, V)  (0x8c3c7b74): the 12 byte hook jumps to n_gm
LIBN_GAME = {'FLOW_PRG/GAME.BIN': dict(off=0xF7B74, head=bytes.fromhex('224f'), sig='')}


def libn_edits(es, d, name, sites, addr=LIBN_ADDR, money_addr=CAVE_ADDR):
    """stub + pool words (+ G_INCOME digit counter) / GAME hook for one overlay"""
    sym = libn_assembly(addr, money_addr)[2]
    if name in LIBN_SITES:
        spec = LIBN_SITES[name]
        if not sites:
            raise MoneyPatchError('%s: numeric formats: no money function to host the stub' % name)
        x = sites[0]
        if x.get('base') is None:
            raise MoneyPatchError('%s: numeric formats: no load address' % name)
        stub_va = x['base'] + x['off'] + LIBN_STUB_REL
        lo = x['off'] + LIBN_STUB_REL
        real = spec['pools'][0][1]
        es.add('money.libnstub', name, lo, libn_stub(real, spec['width'], sym[spec['entry']]), expect=d[lo:lo + 24])
        for off, val in spec['pools']:
            cur = struct.unpack_from('<I', d, off)[0]
            if cur != val:
                raise MoneyPatchError('%s: numeric pool word at %#x is %#x, expected %#x' % (name, off, cur, val))
            es.add('money.libn', name, off, struct.pack('<I', stub_va), expect=struct.pack('<I', val))
        if 'counter' in spec:
            off, val = spec['counter']
            cur = struct.unpack_from('<I', d, off)[0]
            if cur != val:
                raise MoneyPatchError('%s: digit-counter pool word at %#x is %#x, expected %#x' % (name, off, cur, val))
            es.add('money.libn', name, off, struct.pack('<I', sym['n_gd']), expect=struct.pack('<I', val))
    if name in LIBN_GAME:
        spec = LIBN_GAME[name]
        off = spec['off']
        if d[off:off + 2] != spec['head'] or off % 4:
            raise MoneyPatchError('%s: GAME money text function not at %#x' % (name, off))
        es.add('money.libngame', name, off, hook_bytes(sym['n_gm']), expect=d[off:off + HOOK_LEN])


# ------------------------------------------------------------------------------------------------ sites
FN_LEN = 206                     # length of the original function (both variants)
PROLOGUE = bytes.fromhex('e62fd62fc62fb62f224ff87f')      # mov.l r14,@-r15; r13; r12; r11; sts.l pr,@-r15; add #-8,r15
HOOK_LEN = 12
# masked SHA-1 (first 10 hex digits) of the original body: pc-relative loads and bsr displacements are zeroed
SIGS = {'c1886aaeed': 'B', '1b2a19ee69': 'A'}
# the 24 byte masked head shared by both variants (prologue, mov.w @(d,pc),r14, mov r4,r14, two pool loads, mov.l r5,@-r15, ...)
HEAD = bytes.fromhex('e62fd62fc62fb62f224ff87f6e90436e39d338dc522fe11f')
FAMILY = PE.Family('money.fn', HEAD, rule='pc+bsr', variants=SIGS, body_len=FN_LEN, align=4)


def _mask(b):
    return PE.mask_bytes(b, 'pc+bsr')


def find_sites(d, name=''):
    """[{off, variant}] of every money function in image `d`; anything that begins like it but does not match a known
    signature raises (a damaged or unknown copy must not be patched blindly)."""
    try:
        return [dict(off=x.off, variant=x.variant) for x in FAMILY.find(d, name)]
    except PE.EngineError as e:
        raise MoneyPatchError(str(e))


def hook_bytes(addr=CAVE_ADDR):
    """mov.l @(1,pc),r0 / jmp @r0 / nop / nop / .long cave   (site must be 4-aligned: the literal is at site+8)"""
    return PE.hook12(addr)


def cave_symbols(addr=CAVE_ADDR, style=DEFAULT_STYLE):
    return cave_assembly(addr, style)[2]


def find_d_literal(d, off):
    """(file offset, load address) of the literal-pool word the `D` branch of the expander loads: the address of the FULL-WIDTH digit
    function.  Located through the expander's literal pool (... 0x8c014de4 strlen, 0x8c013294 strncpy, pad string,
    FULL-WIDTH function, '#' function ...) and cross-checked against the `bsr` of the money function at +0x30 (hi < 10
    is printed with the same function), which pins the load address.  At most one pool may match (None = no expander)."""
    w = struct.unpack_from('<H', d, off + 0x30)[0]
    if (w >> 12) != 0xB:
        raise MoneyPatchError('money function at %#x: no bsr at +0x30' % off)
    disp = w & 0xFFF
    if disp & 0x800:
        disp -= 0x1000
    found = []
    for k in range(8, len(d) - 20, 4):
        if struct.unpack_from('<II', d, k) != (STRLEN_ADDR, STRNCPY_ADDR):
            continue
        money = struct.unpack_from('<I', d, k - 4)[0]
        base = money - off
        if base & 0xFFFF or not 0x8C000000 <= base < 0x8D000000:
            continue
        fw = struct.unpack_from('<I', d, k + 12)[0]
        if fw == base + off + 0x30 + 4 + disp * 2:
            found.append((k + 12, base))
    if len(found) > 1:
        raise MoneyPatchError('money function at %#x: %d candidate `%%D` literals' % (off, len(found)))
    return found[0] if found else None          # (file offset of the literal, load address) / None: no expander (LOGO OFFICE TITLE)


# ------------------------------------------------------------------------------------------------ compact output (flag 'M')
# (1) the scout info panel (SCDRF.BIN, SEARCH.BIN; two call sites each) formats the money text into a FIXED 12 byte field of a window string:
#         len = money(buf, V, 0);  strncpy(str + 37 + (12 - len), buf, len)       (tail = 10 instructions, see _match_tail)
#     the Japanese text of a salary is at most 12 bytes ('13億1500万円'), the English '1 oku 300 man' is 13: 12 - len = -1 writes the first
#     character one byte BEFORE the field and the window shows ' oku 300 man' (the playtest: 'oku 300 man' with the leading '1 ' lost).  The fix
#     is the compact form, selected by the flag the caller passes: `mov #0,r6` becomes `mov #77,r6` ('1 oku 300m', 10 bytes; 12 for '13 oku 1500m').
# (2) a per format string selector for the tsString expander: `%M` = `%m` with flag 77 (compact).  The expander (98 identical copies) gets its
#     token chain rewritten: D and d are tested first, then r6 = the character, folded to lower case, then the m test, then the s test whose
#     fall-through is the `%s` code.
MOV_0_R6 = 0xE600
MOV_COMPACT_R6 = 0xE600 | COMPACT_FLAG


def _hw(d, o):
    return d[o] | d[o + 1] << 8


def _match_tail(d, o):
    """the 10 instructions after the money call of the panel: mov #12,r4 / mov r14,r3 / mov.l @(d,pc),r2 / mov r0,rB / mov.l @(d,pc),r5 /
    add #37,r3 / sub rB,r4 / mov r0,r6 / jsr @r2 / add r3,r4   (rB = r11 or r12)"""
    w = [_hw(d, o + 2 * i) for i in range(10)]
    rb = (w[3] >> 8) & 15
    return (w[0] == 0xE40C and w[1] == 0x63E3 and (w[2] & 0xFF00) == 0xD200 and (w[3] & 0xF0FF) == 0x6003 and rb in (11, 12)
            and (w[4] & 0xFF00) == 0xD500 and w[5] == 0x7325 and w[6] == 0x3408 | (rb << 4) and w[7] == 0x6603 and w[8] == 0x420B
            and w[9] == 0x343C)


def panel_sites(d, money_va):
    """[file offsets of the `mov #0,r6` halfword] of the call sites of the 12 byte info panel field in image `d`.  `money_va` = the address of the ORIGINAL
    money function copy of this overlay: the site is the last `mov #0,r6` (at most 6 instructions) before the tail, and a `jsr @rX` between them
    must call it (rX loaded from a literal pool word equal to money_va)."""
    out = []
    for o in range(0, len(d) - 20, 2):
        if not _match_tail(d, o):
            continue
        site = None
        for k in range(o - 2, max(0, o - 14), -2):
            if _hw(d, k) == MOV_0_R6:
                site = k
                break
        if site is None:
            continue
        ok = False
        for k in range(site - 6, o, 2):
            w = _hw(d, k)
            if (w & 0xF0FF) == 0x400B:               # jsr @rX
                rx = (w >> 8) & 15
                for j in range(max(0, k - 24), k, 2):
                    v = _hw(d, j)
                    if (v >> 12) == 0xD and ((v >> 8) & 15) == rx:
                        lit = ((j + 4) & ~3) + (v & 0xFF) * 4
                        if struct.unpack_from('<I', d, lit)[0] == money_va:
                            ok = True
        if ok:
            out.append(site)
    return out


EXP_DLIT_REL = 0x1B0          # the `%D` literal of the expander minus the function start
EXP_CHAIN_REL = 0x46          # the token chain (10 halfwords), relative to the function start
EXP_R6_REL = 0x120            # the `mov #0,r6` of the `%m` branch


def _bt(frm, to):
    return 0x8900 | (((to - (frm + 4)) // 2) & 0xFF)


def _bf(frm, to):
    return 0x8B00 | (((to - (frm + 4)) // 2) & 0xFF)


def _bra(frm, to):
    return 0xA000 | (((to - (frm + 4)) // 2) & 0xFFF)


def _chain_words(new):
    """the 10 halfwords of the token chain; addresses relative to the function start (MEETING: 0xf128 + x)"""
    a = EXP_CHAIN_REL
    br_s, br_d_up, br_d, br_m, dflt = 0x182 - 0x128, 0x1BC - 0x128, 0x1F4 - 0x128, 0x224 - 0x128, 0x258 - 0x128
    if not new:
        # cmp/eq #115 / bt s / cmp/eq #68 / bt D / cmp/eq #100 / bt d / cmp/eq #109 / bt m / bra default / nop
        ws = [0x8873, _bt(a + 2, br_s), 0x8844, _bt(a + 6, br_d_up), 0x8864, _bt(a + 10, br_d), 0x886D, _bt(a + 14, br_m),
              _bra(a + 16, dflt), 0x0009]
    else:
        # cmp/eq #68 / bt D / cmp/eq #100 / bt d / mov r0,r6 / or #32,r0 / cmp/eq #109 / bt m / cmp/eq #115 / bf default (falls into `%s`)
        ws = [0x8844, _bt(a + 2, br_d_up), 0x8864, _bt(a + 6, br_d), 0x6603, 0xCB20, 0x886D, _bt(a + 14, br_m), 0x8873, _bf(a + 18, dflt)]
    return b''.join(struct.pack('<H', w) for w in ws)


def expander_edits(es, d, dlit, name=''):
    """`%M` for the expander whose `%D` literal is at file offset `dlit`: chain rewrite + the `mov #0,r6` of the `m` branch becomes a nop (r6 keeps the
    character: 109 for `%m`, 77 for `%M`).  Every word is checked against the original bytes (EditSet expect)."""
    start = dlit - EXP_DLIT_REL
    if d[start:start + 4] != bytes.fromhex('e62fd62f'):
        raise MoneyPatchError('%s: expander prefix not at %#x' % (name, start))
    es.add('money.token', name, start + EXP_CHAIN_REL, _chain_words(True), expect=_chain_words(False))
    es.add('money.token', name, start + EXP_R6_REL, struct.pack('<H', 0x0009), expect=struct.pack('<H', MOV_0_R6))


# the library overlays: file -> [(file offset of the literal-pool word holding `real`, value)] (mn6_libscan.py; every pool word is used only by the
# money library functions or by callers whose formats pass through unchanged).  `real` is the same code in all of them (mn6_realcmp.py).
LIB_SITES = {
    'FLOW_PRG/CHALMODE.BIN': [(0x78AC, 0x8C4D3CD4)],
    'FLOW_PRG/DRSHRANK.BIN': [(0x8B74, 0x8C4D63A4)],
    'FLOW_PRG/DRSISEKI.BIN': [(0x464C, 0x8C4D3740)],
    'FLOW_PRG/DRSJAPAN.BIN': [(0x3ADC, 0x8C4D2BD0)],
    'FLOW_PRG/DRSLIST.BIN': [(0xAE8C, 0x8C4D9418)],
    'FLOW_PRG/DRSSRANK.BIN': [(0x9C94, 0x8C4D74C4)],
    'FLOW_PRG/GETREP.BIN': [(0x94C0, 0x8C2E1130), (0x14468, 0x8C2E1130)],
    'FLOW_PRG/PL_EDIT.BIN': [(0x1175C, 0x8C4DE424)],
    'FLOW_PRG/SELNAT.BIN': [(0xB59C, 0x8C2D9B28)],
}


# the no-argument zero of the library function F1 (`0円`, 4 bytes in place): file offset of the literal-pool word, value (the Japanese string)
LIB_ZERO = {'FLOW_PRG/GETREP.BIN': (0x94D0, 0x8C2F7D0C)}


def lib_edits(es, d, name, sites):
    """stub (in the dead body of the money function copy) + the literal-pool words of `real`"""
    if not sites or sites[0].get('base') is None:
        raise MoneyPatchError('%s: number library: no money function / load address to host the stub' % name)
    x = sites[0]
    stub_va = x['base'] + x['off'] + LIB_STUB_REL
    real = LIB_SITES[name][0][1]
    lo = x['off'] + LIB_STUB_REL
    es.add('money.libstub', name, lo, lib_stub(real), expect=d[lo:lo + 16])
    for off, val in LIB_SITES[name]:
        if struct.unpack_from('<I', d, off)[0] != val:
            raise MoneyPatchError('%s: number library pool word at %#x is %#x, expected %#x' % (name, off, struct.unpack_from('<I', d, off)[0], val))
        es.add('money.lib', name, off, struct.pack('<I', stub_va), expect=struct.pack('<I', val))
    if name in LIB_ZERO:
        off, val = LIB_ZERO[name]
        cur = struct.unpack_from('<I', d, off)[0]
        # a pointer to a string: the text stage may have relocated the string (repack), so only "a pointer into this image" is checked
        if not (x['base'] <= cur < x['base'] + len(d)):
            raise MoneyPatchError('%s: zero-amount literal at %#x is %#x, not a pointer into the image (original %#x)' % (name, off, cur, val))
        es.add('money.lib', name, off, struct.pack('<I', lib_assembly()[2]['l_zero']), expect=struct.pack('<I', cur))


def overlay_edits(es, d, name='', addr=CAVE_ADDR, variants='A', decimal_d=True, style=DEFAULT_STYLE, compact_token=False, panel_compact=True,
                  lib=True, libn=True):
    """add the hook (+ `%D` literal, + compact selectors) edits of one overlay image to the EditSet `es`; returns the sites.
    compact_token (jp only): `%M` in the expander.  panel_compact (jp only): the 12 byte scout info panel field passes the compact flag.
    lib (jp only, default cave address only): the number-library wrapper of LIB_SITES overlays (stub + literal-pool word)."""
    sites = [x for x in find_sites(d, name) if x['variant'] in variants]
    hk = hook_bytes(addr)
    dec = cave_symbols(addr, style)['m_dec']
    for x in sites:
        es.add('money.hook', name, x['off'], hk, expect=d[x['off']:x['off'] + HOOK_LEN])
        r = find_d_literal(d, x['off'])
        x['dlit'], x['base'] = r if r else (None, None)
        if decimal_d and r:
            es.add('money.dlit', name, x['dlit'], struct.pack('<I', dec), expect=d[x['dlit']:x['dlit'] + 4])
        x['panel'] = []
        if style == 'jp' and r:
            if panel_compact:
                x['panel'] = panel_sites(d, r[1] + x['off'])
                for o in x['panel']:
                    es.add('money.compact', name, o, struct.pack('<H', MOV_COMPACT_R6), expect=struct.pack('<H', MOV_0_R6))
            if compact_token:
                expander_edits(es, d, r[0], name)
    if lib and style == 'jp' and addr == CAVE_ADDR and name in LIB_SITES:
        lib_edits(es, d, name, sites)
    if libn and style == 'jp' and addr == CAVE_ADDR and (name in LIBN_SITES or name in LIBN_GAME):
        libn_edits(es, d, name, sites)
    return sites


def patch_overlay(d, name='', addr=CAVE_ADDR, variants='A', decimal_d=True, style=DEFAULT_STYLE, compact_token=False, panel_compact=True,
                  lib=True, libn=True):
    """returns (new bytes, sites).  Same length.  An already hooked copy has no signature left (-> not found, not hooked twice).
    decimal_d: also point the `%D` branch of the expander at the ASCII routine (m_dec)."""
    es = PE.EditSet()
    sites = overlay_edits(es, d, name, addr, variants, decimal_d, style, compact_token, panel_compact, lib, libn)
    if not sites:
        return bytes(d), []
    try:
        out = es.apply({name: d})[name]
    except PE.EngineError as e:
        raise MoneyPatchError('%s: %s' % (name, e))
    assert len(out) == len(d)
    return out, sites


def patch_1st_read(k, addr=CAVE_ADDR, style=DEFAULT_STYLE, lib=True, libn=True):
    """write the cave (and, jp style at the default address, the number-library wrapper) into the zero reserve of 1ST_READ.BIN; refuses unless the
    whole reserve is zero."""
    cave = cave_bytes(addr, style)
    if addr != CAVE_ADDR:
        try:
            PE.REGISTRY.check_free(addr, RESERVE, 'money', ignore=('money.cave',))
        except PE.EngineError as e:
            raise MoneyPatchError(str(e))
    es = PE.EditSet({PE.IMG_NAME: IMG_BASE})
    es.add('money.cave', PE.IMG_NAME, addr - IMG_BASE, cave + bytes(RESERVE - len(cave)), expect=PE.ZERO)
    if lib and style == 'jp' and addr == CAVE_ADDR:
        es.add('money.lib', PE.IMG_NAME, LIB_ADDR - IMG_BASE, lib_bytes(LIB_ADDR, addr) + bytes(LIB_RESERVE - len(lib_bytes(LIB_ADDR, addr))), expect=PE.ZERO)
    if libn and style == 'jp' and addr == CAVE_ADDR:
        ln = libn_bytes(LIBN_ADDR, addr)
        es.add('money.libn', PE.IMG_NAME, LIBN_ADDR - IMG_BASE, ln + bytes(LIBN_RESERVE - len(ln)), expect=PE.ZERO)
    try:
        return es.apply({PE.IMG_NAME: k})[PE.IMG_NAME]
    except PE.EngineError as e:
        raise MoneyPatchError(str(e))


# ------------------------------------------------------------------------------------------------ TV station card (TV_EVENT)
# PROVEN by reading FLOW_PRG/TV_EVENT.BIN (load 0x8c2d0000): the "capital" line of the TV station card is NOT drawn through the
# tsString `%m` expander but by a private function at 0x8c2d0ed0  draw_money(V, x, y)  (single caller 0x8c2d109a, V = table
# 0x8c2d9a54[level] in 10,000-yen units: 325000 650000 2270000 4410000 8340000 9450000).  It splits V = hi * 10000 + lo and
# draws two separate text objects, "%s億" (hi) at x-72 and "%s万円" (lo, 4 zero padded digits) at x, so the English pieces
# "%s00M" + "Y%s0000" printed 3200M50000000.  Pieces cannot be reordered or divided, so the function is replaced by a
# 64-byte routine that formats V with the (hooked) money function of the same overlay (-> cave -> "Y3.25bn") and draws ONE text
# object (format = the "%s人" record, English "%s") at (x, y).  The old big-value path (0xf2c..0xf9b) becomes dead; its first word
# holds the literal of the money function.  The literal pool 0xf14..0xf2b is shared with two other functions and is not touched.
NOP_WORD = bytes((9, 0))                 # little-endian nop
TV_CARD = dict(rel='FLOW_PRG/TV_EVENT.BIN', base=0x8C2D0000, fn=0x0ED0, fn_end=0x0F14, tail=0x0F2C, tail_end=0x0F9C,
               lit_text=0x0F1C, lit_fmt=0x0F24)
TV_CARD_SIG = '5d515369f7'            # sha1[:10] of the original bytes 0xed0..0xf13 + 0xf2c..0xf9b (no pool, no pc-relative targets)
TV_CARD_SRC_WESTERN = """
        mov.l r14,@-r15
        mov.l r13,@-r15
        sts.l pr,@-r15
        add   #-16,r15
        mov   r5,r13                  ; x
        mov   r4,r5                   ; V (10,000 yen)
        mov   r15,r4                  ; dst = 16-byte buffer on the stack
        mov   r6,r14                  ; y
        mov.l @(L_money,pc),r3
        jsr   @r3
        mov   #0,r6                   ; flag 0 = abbreviated money text
        mov   r15,r1
        add   r0,r1
        mov   #0,r2
        mov.b r2,@r1                  ; NUL
        mov.l @(L_fmt,pc),r3          ; the "%s" record
        mov.l @(L_text,pc),r2         ; text-object constructor (fmt, args...)
        mov   r15,r1
        mov.l r1,@-r15
        jsr   @r2
        mov.l r3,@-r15
        add   #8,r15
        mov   r0,r4
        mov   #74,r0
        mov.w r13,@(r0,r4)
        mov   #76,r0
        mov.w r14,@(r0,r4)
        add   #16,r15
        lds.l @r15+,pr
        mov.l @r15+,r13
        rts
        mov.l @r15+,r14
"""


# jp style (mn6): the capital is ONE text object in the compact form ("32 oku 5000m", flag 77) that starts at x = 456 of 640.  The plate of the card
# ends near x = 616 and its "Capital" capsule near 448, i.e. 168 px are available; the full form "32 oku 5000 man" is 183 px (too wide, it ran over the
# capsule at x = 440 and past the plate), the compact form is 147 px (456 .. 603); "945 oku" is 87 px.  The Japanese card drew the "億" piece at x - 72 and
# the "万円" piece at x (x = 512); the stack buffer is 32 bytes (an int32 needs up to 20 + NUL).
TV_CARD_X_JP = 456
TV_CARD_SRC_JP = (TV_CARD_SRC_WESTERN.replace('add   #-16,r15', 'add   #-32,r15').replace('add   #16,r15', 'add   #32,r15')
                  .replace('mov   r5,r13                  ; x', 'mov   r5,r13                  ; x\n        add   #%d,r13                ; x = %d' % (TV_CARD_X_JP - 512, TV_CARD_X_JP))
                  .replace('mov   #0,r6                   ; flag 0 = abbreviated money text', 'mov   #77,r6                  ; flag 77 = compact form'))
TV_CARD_SRC = TV_CARD_SRC_JP


def _tv_src(style):
    if style == 'jp':
        return TV_CARD_SRC_JP
    if style == 'western':
        return TV_CARD_SRC_WESTERN
    raise MoneyPatchError('unknown money style %r' % (style,))


def tv_card_sig(d):
    t = TV_CARD
    return hashlib.sha1(d[t['fn']:t['fn_end']] + d[t['tail']:t['tail_end']]).hexdigest()[:10]


def tv_card_bytes(money_addr, style=DEFAULT_STYLE):
    """(code at fn, filler for tail) for a money function at load address `money_addr`."""
    t = TV_CARD
    sym = dict(L_money=t['base'] + t['tail'], L_fmt=t['base'] + t['lit_fmt'], L_text=t['base'] + t['lit_text'])
    code, items, _ = assemble(_tv_src(style), t['base'] + t['fn'], sym)
    if len(code) > t['fn_end'] - t['fn']:
        raise MoneyPatchError('TV card routine too long (%d bytes)' % len(code))
    code += NOP_WORD * ((t['fn_end'] - t['fn'] - len(code)) // 2)
    tail = struct.pack('<I', money_addr) + NOP_WORD * ((t['tail_end'] - t['tail'] - 4) // 2)
    return code, tail, items


def patch_tv_card(d, money_off, name='FLOW_PRG/TV_EVENT.BIN', style=DEFAULT_STYLE):
    """d = TV_EVENT.BIN bytes (money function already hooked or not); money_off = file offset of its money function."""
    t = TV_CARD
    if tv_card_sig(d) != TV_CARD_SIG:
        raise MoneyPatchError('%s: TV card capital function at %#x does not match the known bytes (%s)' % (name, t['fn'], tv_card_sig(d)))
    if struct.unpack_from('<I', d, t['lit_text'])[0] != 0x8C2D4930:
        raise MoneyPatchError('%s: TV card text-object constructor literal changed' % name)
    code, tail, _ = tv_card_bytes(t['base'] + money_off, style)
    b = bytearray(d)
    b[t['fn']:t['fn_end']] = code
    b[t['tail']:t['tail_end']] = tail
    assert len(b) == len(d)
    return bytes(b)



def overlay_paths(root=EXTRACTED):
    r = sorted('FLOW_PRG/' + os.path.basename(p) for p in glob.glob(os.path.join(root, 'FLOW_PRG', '*.BIN')))
    return r + ['ATFIRST/HELP.BIN', 'ATFIRST/TITLE.BIN']


EXPECTED_SITES = {'A': 102, 'B': 6}   # copies of the money function in extracted/ (B = the six overlays linked against another
                                      # 1ST_READ build, docs/font-hook-notes.md s5: INFERRED dead; hooked only with variants='AB')


def make_patches(read, current=None, addr=CAVE_ADDR, paths=None, expect=None, variants='A', decimal_d=True, tv_card=True, style=DEFAULT_STYLE,
                 compact_token=False, panel_compact=True, lib=True, libn=True):
    """The whole feature as a function.  `read(rel)` returns the ORIGINAL bytes of an extracted file; `current`
    {iso path: bytes} are files already patched by earlier stages (the sites are found by signature in the current bytes).
    compact_token: `%M` in the expander of every overlay (jp style only; default OFF: no translation record uses it, section 4.8 of docs/number-formats.md).
    panel_compact: the scout info panel (SCDRF / SEARCH, 4 call sites) asks for the compact form (jp style only; default ON).
    Returns ({iso path: bytes} for every file that changes, report dict)."""
    current = current or {}

    def cur(rel):
        return current.get('/' + rel) or read(rel)
    out = {}
    rep = dict(sites={'A': 0, 'B': 0}, files=[], cave=addr, size=len(cave_bytes(addr, style)), style=style,
               panel_sites=0, token_overlays=0)
    out['/1ST_READ.BIN'] = patch_1st_read(cur('1ST_READ.BIN'), addr, style, lib, libn)
    for rel in (paths if paths is not None else overlay_paths()):
        d = cur(rel)
        nd, sites = patch_overlay(d, rel, addr, variants, decimal_d, style, compact_token, panel_compact, lib, libn)
        if sites and rel == TV_CARD['rel'] and tv_card:
            nd = patch_tv_card(nd, sites[0]['off'], rel, style)
            rep.setdefault('tv_card', rel)
        if sites:
            out['/' + rel] = nd
            rep['files'].append((rel, sites[0]['variant'], len(sites)))
            for s in sites:
                rep['sites'][s['variant']] += 1
                rep['panel_sites'] += len(s.get('panel') or [])
            if compact_token and style == 'jp' and sites[0].get('dlit') is not None:
                rep['token_overlays'] += 1
    if expect is not None:
        for v, n in expect.items():
            if v in variants and rep['sites'][v] != n:
                raise MoneyPatchError('expected %d variant-%s money functions, patched %d' % (n, v, rep['sites'][v]))
    return out, rep


def piece_addrs(d, off, base):
    """addresses of the four unit strings [億][万円][円][0円] of the function at file offset `off` of an image loaded at `base`:
    the literals of its four `mov.l @(d,pc),r5` (in order of appearance)."""
    out = []
    for a in range(off, off + FN_LEN, 2):
        w = struct.unpack_from('<H', d, a)[0]
        if (w >> 8) == 0xD5:
            ea = ((base + a + 4) & ~3) + (w & 0xFF) * 4
            out.append(struct.unpack_from('<I', d, ea - base)[0])
    return out


def piece_ids(variants='A'):
    """{record id: unit} of the four unit strings of every money function (translation record ids, 'SOURCE#hexoffset')."""
    import textdb
    ids = {}
    for rel in overlay_paths():
        d = read_extracted(rel)
        sites = [s for s in find_sites(d, rel) if s['variant'] in variants]
        if not sites:
            continue
        for s in sites:
            r = find_d_literal(d, s['off'])
            base = r[1] if r else textdb.load_image(rel).base     # the literal pool pins the true load address
            pcs = piece_addrs(d, s['off'], base)
            if len(pcs) != 4:
                raise MoneyPatchError('%s: %d unit-string literals' % (rel, len(pcs)))
            for unit, a in zip(('oku', 'man-yen', 'yen', 'zero-yen'), pcs):
                ids['%s#%x' % (rel, a - base)] = unit
    return ids


def read_extracted(rel):
    with open(os.path.join(EXTRACTED, *rel.split('/')), 'rb') as f:
        return f.read()


# ------------------------------------------------------------------------------------------------ CLI
def cmd_scan():
    tot = {'A': 0, 'B': 0}
    for rel in overlay_paths():
        for s in find_sites(read_extracted(rel), rel):
            tot[s['variant']] += 1
            print('%-28s off %#08x variant %s' % (rel, s['off'], s['variant']))
    print('sites: %s (expected %s)' % (tot, EXPECTED_SITES))
    return 0 if tot == EXPECTED_SITES else 1


def cmd_listing():
    b, items, sym = cave_assembly()
    for addr, w, text in items:
        print('%08x  %-10s %s' % (addr, w.hex(), text))
    print('%d bytes (reserve %d)' % (len(b), RESERVE))
    return 0


def cmd_patch(argv):
    dump = None
    if '--dump' in argv:
        dump = argv[argv.index('--dump') + 1]
    out, rep = make_patches(read_extracted, expect=EXPECTED_SITES, variants='AB' if '--all' in argv else 'A')
    print('cave %#x, %d bytes; %d overlays hooked, sites %s' % (rep['cave'], rep['size'], len(rep['files']), rep['sites']))
    if dump:
        for iso, data in out.items():
            p = os.path.join(dump, *iso.strip('/').split('/'))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as f:
                f.write(data)
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] not in ('scan', 'listing', 'patch'):
        print(__doc__)
        return 2
    return {'scan': lambda: cmd_scan(), 'listing': lambda: cmd_listing(), 'patch': lambda: cmd_patch(argv)}[argv[1]]()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
