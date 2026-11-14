"""Proportional half-width font patch (docs/proportional-font.md).  Pure bytes in / bytes out; no emulator needed.

    python -I -X utf8 tools/fontpatch.py scan                 # find the hook sites in extracted/ (counts, variants)
    python -I -X utf8 tools/fontpatch.py table                # print the advance table derived from extracted/FONT.BIN
    python -I -X utf8 tools/fontpatch.py patch [--dump DIR] [--align-fix]   # run make_patches() on extracted/, print a summary
    python -I -X utf8 tools/fontpatch.py lua                  # (re)generate tools/emu/fonttest.lua
    python -I -X utf8 tools/fontcheck.py                      # static self-check + interpreter run (separate file)

What it does (all in place, no file grows, no `_end` change):
  * `1ST_READ.BIN` tail (file offset address-0x8c010000): a 104-byte advance/wrap routine (CAVE) and a 256-byte
    advance table (TABLE).  Nothing else in 1ST_READ is touched.
  * every overlay that statically links the tsString window library (97 FLOW_PRG overlays + HELP = 98 'A' copies, 6 'B'
    copies, 1 'C' copy): H1 replaces the 16 bytes that add the half-width advance (`A>>1`) by a call into the cave,
    H2 replaces the cell-count wrap test by a pixel-count test (also a call into the cave).
  * both FONT.BIN copies: the half-width glyphs 0x21-0x7E (except the digits) are shifted left so that their ink starts at
    column 0 (the advance is added AFTER drawing a 12 px tile at the pen position; the original art is centred).
The table is derived from the (shifted) glyph art: advance = strong ink extent + 1 + gap (docs/font-widths.md).
Optional `align_fix` (make_patches(..., align_fix=True), `--align-fix`; docs/layout-issues.md section 10): the game aligns text by cell counts
(12 px per character), so padded columns and right anchored cells go wrong with proportional advances.  A second registered cave
(`font.align`, 0x8c299700) snaps the pen back to the fixed-cell grid at the end of a run of blanks, and the shared player-card panel of
CAP_SLCT / ENDOPT / EVENT measures its cells in pixels (18 `shll2` -> nop, 8 strlen literals -> `pw3` per overlay; the 2 salary idioms keep their `shll2`).

Variants (docs/font-hook-notes.md, docs/font-patch-design.md; the byte templates below are PROVEN identical to every
copy found in extracted/ - `scan` refuses anything that does not match exactly):
  A  pen r10, units r11, advance byte win+0x3e  (98 files)    B  pen r11, units r10, all offsets 8 lower (6)    C  (1)
"""
import glob
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import patchengine as PE      # noqa: E402  (cave registry, overlap registry, site families: docs/patch-engine.md)
ROOT = os.path.dirname(HERE)
EXTRACTED = os.path.join(ROOT, 'extracted')
IMG_BASE = PE.IMG_BASE                       # 1ST_READ.BIN load address (file offset = address - IMG_BASE)

# ------------------------------------------------------------------------------------------------ placement
# PRIMARY: code + table side by side in the 1ST_READ.BIN "tail" after crt0's BSS end (docs/trans-bank.md s2.4).
# ALT 'gap1': the zero hole between .text and the jump table (constants only differ: the code is position independent).
# The addresses live in the cave registry (patchengine.REGISTRY), which also owns the money cave and the planned bank.
PLACEMENTS = {
    'tail': (PE.REGISTRY.addr('font.cave'), PE.REGISTRY.addr('font.table')),
    'gap1': (PE.REGISTRY.addr('font.gap1.cave'), PE.REGISTRY.addr('font.gap1.table')),
}
_PLACEMENT_CAVES = {'tail': ('font.cave', 'font.table'), 'gap1': ('font.gap1.cave', 'font.gap1.table')}
DEFAULT_PLACEMENT = 'tail'
CAVE_SIZE = 104
TABLE_SIZE = 256
RESERVE = 0x100                              # bytes reserved for the cave (zero-checked) before the table
assert PE.REGISTRY.size('font.cave') == RESERVE and PE.REGISTRY.size('font.table') == TABLE_SIZE

# 104 bytes of SH-4 code, source and decoded listing in docs/proportional-font.md s3 / tools/fontcheck.py CAVE_SRC.
# The last 4 bytes are the literal TABLE (0x8c299900 here), rewritten by cave_bytes().
_CAVE = bytes.fromhex(
    '01a03ee036e0ec0218e33032078b15d14c601c000820008b0ce00b00090000e327333e3221420b00236001a000e1f8e13ce01c30ec02'
    '0270ec03ff7237020770ec001a020820058b40e0184059200820008b38324ae01c30ed000834273429000b0009000099298c')
ENTRY_ADV_A, ENTRY_ADV_B, ENTRY_WRAP_A, ENTRY_WRAP_B = 0x00, 0x04, 0x2A, 0x2E      # offsets inside the cave

# ------------------------------------------------------------------------------------------------ hook templates
H1_OLD = {
    'A': bytes.fromhex('3ee0ec0200e327333e3221422c3a04a0'),
    'B': bytes.fromhex('36e0ec0200e327333e3221422c3b04a0'),
    'C': bytes.fromhex('3ee0ec0200e327333e3221422c3b04a0'),
}
H1_NEW = {   # 12 bytes + 4 byte literal (cave entry address)
    'A': bytes.fromhex('02d30b43c3640c3a07a0017b'),
    'B': bytes.fromhex('02d30b43c3640c3b07a0017a'),
    'C': bytes.fromhex('02d30b43c3640c3b07a0017a'),
}
H1_ENTRY = {'A': ENTRY_ADV_A, 'B': ENTRY_ADV_B, 'C': ENTRY_ADV_A}
H2_BACK = {'A': 0x15C, 'B': 0xDE, 'C': 0xDE}            # H2 site = H1 site - this
H2_OLD = {
    'A': bytes.fromhex(
        'b3643ce000e3ec0201744733ff723e3421442734068b3fe0ec024ae0ed0a2c3810a0d36b20340d8b45e0ec022822098b6f92cd63'
        '2823058b3fe0d36bec000c384ae0ed0a'),
    'B': bytes.fromhex('a36434e000e3ec0201744733ff723e3421442734178b37e0ec0242e0ed0b2c3821a0d36a'),
    'C': bytes.fromhex('a3643ce000e3ec0201744733ff723e3421442734178b3fe0ec024ae0ed0b2c3821a0d36a'),
}
H2_NEW = {   # prefix, then the 4 byte literal (cave wrap entry), then NOPs up to the old length
    'A': bytes.fromhex('c36506d30b43a36408201b893fe0ec022c384ae0ed0a15a0d36b0900'),
    'B': bytes.fromhex('c36505d30b43b36408202c8937e0ec022c3842e0ed0b26a0d36a'),
    'C': bytes.fromhex('c36505d30b43b36408202c893fe0ec022c384ae0ed0b26a0d36a'),
}
H2_ENTRY = {'A': ENTRY_WRAP_A, 'B': ENTRY_WRAP_B, 'C': ENTRY_WRAP_A}
H2_ALIGN = {'A': 0, 'B': 2, 'C': 2}                      # site % 4 required by the pc-relative literal
NOP = b'\x09\x00'
B_NAMES = ('COMM.BIN', 'CON_REP.BIN', 'NF_CON.BIN', 'PASS_PL.BIN', 'J1_REP.BIN', 'PL_CON.BIN')


class FontPatchError(PE.EngineError):
    pass


# the advance template of each variant as an exact site family (engine: rule 'none', 4-aligned, a misaligned match is ignored)
FAMILIES = {v: PE.Family('font.h1.' + v, H1_OLD[v], rule='none', align=4, misaligned='skip') for v in 'ABC'}

for _v in 'ABC':
    assert len(H1_OLD[_v]) == 16 and len(H1_NEW[_v]) + 4 == 16
    assert len(H2_NEW[_v]) + 4 <= len(H2_OLD[_v]) and (len(H2_OLD[_v]) - len(H2_NEW[_v])) % 2 == 0
assert len(_CAVE) == CAVE_SIZE


# ------------------------------------------------------------------------------------------------ cave / hooks
def placement(name_or_pair=DEFAULT_PLACEMENT):
    if isinstance(name_or_pair, str):
        return PLACEMENTS[name_or_pair]
    return tuple(name_or_pair)


# --prop-scale (opt-in): windows whose advance A is not 24 (16 / 32 / 48 / 10 px classes) get the SAME table scaled by A/24,
# w = (tbl[c] * A + 12) / 24 with tbl 0 = 12, instead of the fixed A >> 1.  Identity for tbl = 12 (A = 16 -> 8, 32 -> 16),
# so digits and unlisted codes keep their original width in every window.  A <= 0 keeps the original rule.  Only ONE word of
# the default cave changes (the `bf adv_gen` at +0x0c now branches to the appended routine); every entry offset stays, so
# the overlay hooks are byte-identical with and without the option.  Division by 24: (x * 2731) >> 16 is exact for 0 <= x < 4000
# (x <= 24 * 127 + 12 = 3060 here; checked exhaustively by tools/test_patchengine.py).
CAVE_SCALE_SRC = """
adv_scale: cmp/pl r2                  ; r2 = window advance A (signed byte, != 24 here)
        bf    adv_gen                 ; A <= 0: original rule
        mov.l @(tblp2,pc),r1
        extu.b r4,r0
        mov.b @(r0,r1),r0             ; t = table[char]
        tst   r0,r0
        bf    sc_t
        mov   #12,r0                  ; 0 = 'no entry': 12 px at A = 24
sc_t:   mul.l r2,r0                   ; MACL = t * A
        sts   macl,r0
        add   #12,r0                  ; rounding
        mov.w @(inv,pc),r3            ; 2731 = ceil(65536 / 24)
        mul.l r3,r0
        sts   macl,r0
        shlr16 r0                     ; floor(x / 24)
        rts
        nop
inv:    .word 2731
        .align 4
tblp2:  .long TABLE
"""
ADV_BF_OFF, ADV_GEN_OFF = 0x0C, 0x1E          # offsets inside the cave: `bf adv_gen` and the label adv_gen
ADV_RET_OFF = 0x1A                             # `rts ; nop` that ends the table path (A == 24)
CAVE_SIZE_SCALE = 144                          # bytes of the cave with --prop-scale (the reserve is 256)


# --small-prop (opt-in, default off; docs/layout-issues.md s17): the 16 px windows of OPTION.BIN (the option / sound-test lists) and TRAINING.BIN (the
# Practice player-info panel) keep the fixed advance `A >> 1` = 8 px of the font cave's `A != 24` path while the proportional glyph ink sits at the LEFT of
# its tile, so 'i', 'l', 'r', 't' ... are followed by a gap ('Trai ni ng', 'H i roshi').  Only the advance hook of the overlays in SMALL_FILES enters a
# second entry `sm_adv` in the unused tail of the font cave (SMALL_OFF .. SMALL_OFF + 0x40 of the 256 byte reserve; every byte of the default cave and its
# entry offsets stay).  `sm_adv` reads A; A != 16 jumps (tail jump, PR / r4 / r14 untouched) to the UNCHANGED font cave entry, so every other window of those two
# overlays behaves exactly as before; A == 16 returns w = (2 t + 1) / 3 with t = the table advance (0 = unlisted = 12), i.e. (t * 16 + 12) / 24, the table
# scaled by the 2/3 sprite scale of the size class 2 window (quad 8 x 16 of the 12 col tile, docs/font-hook-notes.md s3.4).  The division is a 25 byte lookup
# table (t <= 24), so no multiply and no MACL.  t = 12 gives 8: digits, blanks and unlisted codes keep the original 8 px.  The wrap routine (H2) is untouched.
SMALL_FILES = ('FLOW_PRG/OPTION.BIN', 'FLOW_PRG/TRAINING.BIN')
SMALL_OFF = 0xA0                                  # offset of `sm_adv` inside the 256 byte font.cave reserve (the --prop-scale cave ends at 0x90)
SMALL_WINDOW_ADV = 16
SMALL_TAB = bytes((2 * t + 1) // 3 for t in range(25))      # w for table advance t = 0 .. 24 (index 0 is never read: 0 maps to 12 first)
SMALL_SRC = """
sm_adv: mov   #62,r0
        mov.b @(r0,r14),r2            ; window advance A
        mov   #16,r3
        cmp/eq r3,r2
        bf    CAVE                    ; not a 16 px window: the unchanged font cave from its entry (a tail jump: PR, r4, r14 untouched)
        mov.l @(tblp,pc),r1
        extu.b r4,r0
        mov.b @(r0,r1),r0             ; t = table[char]
        tst   r0,r0
        bf    sm_t
        mov   #12,r0                  ; 0 = unlisted: 12
sm_t:   mov.l @(smp,pc),r1
        mov.b @(r0,r1),r0             ; w = (2 t + 1) / 3
        rts
        nop
        .align 4
tblp:   .long TABLE
smp:    .long SMTAB
"""
SMALL_TAB_OFF = 40                                # offset of the lookup table behind the code and the two literals (checked by small_bytes)


def small_bytes(cave_table):
    """the `sm_adv` entry + literals + lookup table, assembled at cave + SMALL_OFF (a multiple of 4); returns bytes (< 0x100 - SMALL_OFF)"""
    import sh4asm2
    cave, table = cave_table
    at = cave + SMALL_OFF
    code = b''.join(x[1] for x in sh4asm2.Asm(at, {'CAVE': cave + ENTRY_ADV_A, 'TABLE': table, 'SMTAB': at + SMALL_TAB_OFF}).parse(SMALL_SRC).assemble())
    if len(code) != SMALL_TAB_OFF:
        raise FontPatchError('the small-prop routine is %d bytes, expected %d' % (len(code), SMALL_TAB_OFF))
    out = code + SMALL_TAB
    out += bytes(-len(out) % 4)
    if SMALL_OFF + len(out) > RESERVE:
        raise FontPatchError('the small-prop routine does not fit the 256 byte font cave reserve')
    return out


def small_entry(cave_table):
    """the address the hooks of the SMALL_FILES overlays call"""
    return cave_table[0] + SMALL_OFF


def cave_bytes(cave_table, scale=False, small=False):
    """the 104 code bytes with the table literal rewritten; scale=True: the 144 byte --prop-scale cave; small=True: the `sm_adv` entry (--small-prop)
    is appended at SMALL_OFF (zero padded in between).
    The align fix (stage 8h) does NOT touch this cave any more: it used to turn the `rts ; nop` of the table path (+0x1a) into
    `bra at_snap`, which put the snap in front of EVERY proportional draw of every overlay; now only the overlays in ALIGN_SNAP_FILES
    get a hook literal that points at the align cave, the font cave is byte-identical with and without --align-fix."""
    cave, table = cave_table
    base = _CAVE[:-4] + struct.pack('<I', table)
    if scale:
        import sh4asm2
        tail_at = cave + CAVE_SIZE
        bf = sh4asm2.Asm(cave + ADV_BF_OFF, {'adv_scale': tail_at}).parse('bf adv_scale').assemble()
        if base[ADV_BF_OFF:ADV_BF_OFF + 2] != bytes.fromhex('078b'):
            raise FontPatchError('the cave word at +0x0c is not `bf adv_gen`')
        tail = b''.join(x[1] for x in sh4asm2.Asm(tail_at, {'TABLE': table, 'adv_gen': cave + ADV_GEN_OFF}).parse(CAVE_SCALE_SRC).assemble())
        base = base[:ADV_BF_OFF] + bf[0][1] + base[ADV_BF_OFF + 2:] + tail
        assert len(base) == CAVE_SIZE_SCALE, len(base)
    if small:
        if cave % 4:
            raise FontPatchError('the small-prop routine needs a 4-aligned cave')
        base = base + bytes(SMALL_OFF - len(base)) + small_bytes(cave_table)
    return base


def hook_h1(variant, cave_table, entry=None):
    """the 16 byte advance hook; `entry` (default: the font cave advance entry) is the address the literal points at: the overlays in
    ALIGN_SNAP_FILES get the align cave's `at_snap` here (a variant A hook only)"""
    cave, _ = cave_table
    return H1_NEW[variant] + struct.pack('<I', cave + H1_ENTRY[variant] if entry is None else entry)


def hook_h2(variant, cave_table):
    cave, _ = cave_table
    n = len(H2_OLD[variant])
    body = H2_NEW[variant] + struct.pack('<I', cave + H2_ENTRY[variant])
    return body + NOP * ((n - len(body)) // 2)


# ------------------------------------------------------------------------------------------------ --align-fix
# Root cause (docs/layout-issues.md section 10, found by reading the overlays): the game aligns text by CELL COUNTS, the proportional
# font changed the pixels per cell.  Two mechanisms are fixed here:
#   1. COLUMNS BY BLANK PADDING.  A row such as the shirt-number list of PLNUMSET is one string: name, blanks up to byte 14, the number.
#      With 12 px per blank and a proportional name the number lands at name_width + blanks, i.e. a different x per name.  Rule in the
#      cave (`at_snap`): the LAST blank of a run of two or more blanks that is followed by a glyph advances the pen to the pixel the
#      original fixed-cell layout would have used, x0 + 12 * (units + 1) (units = cells so far, the layout's own r11); never less
#      than 4 px.  A single blank between words is untouched.
#      ISOLATION (stage 8h, after the first full playtest hung at the manager's first message with the stage 8b wiring): `at_snap` is the
#      hook entry ONLY of the overlays in ALIGN_SNAP_FILES (PLNUMSET: the shirt-number column, the only screen it was proven on).  Every
#      other overlay keeps the font cave entry, and the font cave itself is byte-identical with and without --align-fix, so those overlays
#      execute exactly the instructions of an align-off build.  Inside `at_snap` every glyph other than a blank in a window with A == 24 is
#      handed to the unchanged font cave (`bf CAVE`, a tail jump), and the blank path validates its frame assumption (index < count and
#      codes[index] really is the blank being laid out) and looks ahead at most 63 codes, so a frame that is not the proven one gets
#      the plain table advance.
#   2. RIGHT ANCHORED CELLS.  The player-card panel of CAP_SLCT / ENDOPT / EVENT places each of its 11 cells at x = anchor - 12 * strlen(text)
#      (idiom `mov r2,r1 ; shll r2 ; add r1,r2 ; ... ; shll2 r2 ; sub r2,r1`).  The proportional text of 'Tokyo' is 65 px, the game
#      assumes 60, so it ends 5 px past the anchor and the panel edge cuts the last letter.  Fix: the strlen that produces the length
#      (8 literal pools per overlay) becomes `pw3`, which returns ceil(pixel width / 3), and the `shll2` of the idiom (x 4) becomes a
#      NOP, so x = anchor - 3 * ceil(P / 3): the text ends at the anchor (at most 2 px short).  Full-width glyphs are 24 px = 8 units,
#      which is exactly what the old 12 * 2 bytes gave.
# Both live in the registered cave `font.align` (0x8c299700, 256 bytes, tail placement only) and need variant A hooks (the default).
ALIGN_SRC = """
at_snap: extu.b r4,r1                 ; hook entry of the overlays in ALIGN_SNAP_FILES; r4 = code, low byte 0 <=> the blank 0x8000
        tst   r1,r1
        bf    CAVE                    ; any other glyph: the UNCHANGED advance routine of the font cave (r4 and the frame untouched)
        mov   #62,r0
        mov.b @(r0,r14),r2            ; window advance A
        mov   #24,r3
        cmp/eq r3,r2
        bf    CAVE                    ; A != 24: the unchanged routine
        mov.l @(4,r15),r1             ; i = index of this code in the layout loop (frame slot of variant A)
        mov.l @(48,r14),r3            ; r3 = code array (window +0x30)
        shll  r1
        mov   r3,r2
        add   r1,r2                   ; r2 = &codes[i]
        mov   #34,r0
        mov.w @(r0,r14),r1            ; n = code count (window +0x22)
        shll  r1
        add   r3,r1                   ; r1 = &codes[n]
        mov.w @(c2020,pc),r5          ; r5 = 0x2020, the blank code
        cmp/hs r3,r2
        bf    CAVE                    ; &codes[i] below the array (garbage index, 2 * i wrapped round): not the proven frame (s8hk)
        cmp/hs r1,r2
        bt    CAVE                    ; i >= n: this is not the frame the snap was proven for: the plain table advance
        mov.w @r2,r0
        cmp/eq r5,r0
        bf    CAVE                    ; codes[i] is not the blank being laid out: not the proven frame, the plain table advance
        mov   r2,r0
        add   #126,r0                 ; look ahead 63 codes at most (a column is never wider)
        cmp/hi r0,r1
        bf    at_c1
        mov   r0,r1
at_c1:  cmp/hi r3,r2
        bf    at_next                 ; i == 0: no previous code
        mov   r2,r3
        add   #-2,r3
        mov.w @r3,r3                  ; codes[i-1]
        cmp/eq r5,r3
        bt    at_look                 ; previous code is a blank: inside a run
at_next: mov   r2,r3
        add   #2,r3
        cmp/hs r1,r3
        bt    CAVE                    ; last code
        mov.w @r3,r3                  ; codes[i+1]
        cmp/eq r5,r3
        bf    CAVE                    ; neither neighbour is a blank: a single word space, the plain table advance
at_look: add   #2,r2                  ; r2 = &codes[j]
        cmp/hs r1,r2
        bt    CAVE                    ; only blanks / controls to the end (or to the look-ahead limit): nothing to align
        mov.w @r2,r3
        cmp/eq r5,r3
        bt    at_look                 ; still inside the run
        mov   r3,r0
        shlr8 r0
        tst   #32,r0                  ; bit 0x2000 of the code clear: a glyph follows the run
        bt    at_do
        extu.b r3,r0
        cmp/eq #10,r0
        bf    at_look                 ; colour / style control: look past it
        bra   CAVE                    ; newline: the run ends the row, nothing to align
        nop
at_do:  mov   #74,r0
        mov.w @(r0,r14),r1            ; x0 (window +0x4a)
        mov   r11,r2
        add   #1,r2                   ; units after this blank
        mov   r2,r3
        shll2 r2
        shll  r2                      ; 8u
        shll2 r3                      ; 4u
        add   r3,r2                   ; 12u (A == 24 here: one cell = 12 px)
        add   r2,r1                   ; the pixel the fixed-cell layout reaches after this blank
        sub   r10,r1                  ; minus the pen = the advance that gets there
        mov   #4,r0                   ; a pad blank may shrink to 4 px to absorb a proportional overshoot
        cmp/gt r0,r1
        bf    at_ret
        mov   r1,r0
at_ret: rts
        nop
c2020:  .word 0x2020
        .align 4
pw3:    mov.l r1,@-r15                ; strlen replacement for the panel: r4 = text, r0 = ceil(pixel width / 3), r1 r2 preserved
        mov.l r2,@-r15
        mov.l @(tblp3,pc),r5
        mov   #0,r2
w_next: mov.b @r4+,r0
        extu.b r0,r0
        tst   r0,r0
        bt    w_done
        mov   r0,r1
        tst   #128,r0
        bf    w_hi                    ; byte >= 0x80
        mov   #32,r3
        cmp/hs r3,r0
        bf    w_next                  ; control byte: no width
        cmp/eq r3,r0
        bf    w_idx
        mov   #0,r0                   ; the blank is table index 0
w_idx:  mov.b @(r0,r5),r0             ; table[c]
        tst   r0,r0
        bf    w_add
        mov   #12,r0                  ; 0 = no entry = 12 px
w_add:  add   r0,r2
        bra   w_next
        nop
w_hi:   add   #96,r0
        shlr2 r0
        shlr2 r0
        shlr2 r0                      ; (b + 0x60) >> 6 == 4 <=> 0xA0..0xDF, single byte katakana
        cmp/eq #4,r0
        bf    w_lead
        bra   w_idx
        mov   r1,r0
w_lead: mov   #24,r0                  ; two byte glyph: 24 px, skip the trail byte
        add   r0,r2
        mov.b @r4,r0
        tst   r0,r0
        bt    w_next
        bra   w_next
        add   #1,r4
w_done: add   #2,r2
        mov.w @(inv3,pc),r3
        mul.l r3,r2
        sts   macl,r0
        shlr16 r0
        mov.l @r15+,r2
        rts
        mov.l @r15+,r1
inv3:   .word 21846                   ; ceil(65536 / 3); (x * 21846) >> 16 == x / 3 exactly for x < 32768
        .align 4
tblp3:  .long TABLE
"""
ALIGN_RESERVE = 0x100                          # registry claim 'font.align'
ALIGN_FILES = ('FLOW_PRG/CAP_SLCT.BIN', 'FLOW_PRG/ENDOPT.BIN', 'FLOW_PRG/EVENT.BIN')          # the player-card panel (pw3 + 18 nops)
ALIGN_SNAP_FILES = ('FLOW_PRG/PLNUMSET.BIN',)                                                # overlays whose hook enters `at_snap` (blank-run columns)
ALIGN_MODES = ('default', 'snap-all', 'snap-only', 'panel-only')
ALIGN_MODE_ENV = 'SAKA_ALIGN_MODE'        # bisect switch for the build (library and command line): one of ALIGN_MODES, unset = default
STRLEN_ADDR = 0x8C014DE4                       # libc strlen of 1ST_READ.BIN
# the shared player-card panel, identical in the three overlays: offsets relative to the first idiom hit (docs/layout-issues.md s10.3)
PANEL_SITES_REL = (8, 44, 84, 118, 160, 200, 244, 290, 330, 372, 418, 512, 548, 588, 622, 714, 750, 790, 824, 868)   # the `shll2` words
PANEL_POOLS_REL = (-3142, -2450, -2058, -1790, -1454, -1230, -914, -626)                                           # strlen literals
PANEL_LOADS_REL = (-3430, -3372, -3190, -3040, -2910, -2856, -2794, -2712, -2610, -2560, -2494, -2376, -2016, -1554, -1368, -1196,
                   -1022, -868)                                                                                     # every load of those literals


# the SALARY cell (card + 104) is the one idiom whose setter does not return `strlen`: CAP_SLCT 0x9510 hands back the money function's
# return value, a CHARACTER count (the hooked money function writes ASCII, 1 byte = 12 px per character = the original `12 * len`), so its
# `shll2` (x 4) must stay.  Found by signature: `mov #104,r0 ; mov.w @(r0,r14),r2 ; mov #74,r0 ; mov r2,r1 ; shll r2 ; add r1,r2 ;
# mov r12,r1 ; shll2 r2` (2 per overlay: state 1 and state 2 of the placement function; docs/layout-issues.md s10.3a)
SALARY_SIG = bytes.fromhex('68e0ed024ae0236100421c32c3610842')
SALARY_SHLL2 = 14            # offset of the `shll2` inside the signature
SHLL2_R2 = bytes.fromhex('0842')


def align_assembly(align_addr, table, cave=None):
    """(bytes, symbols) of the align cave assembled at `align_addr`; `cave` = font cave address (default: the registered tail cave)"""
    import sh4asm2
    a = sh4asm2.Asm(align_addr, {'TABLE': table, 'CAVE': PLACEMENTS['tail'][0] if cave is None else cave}).parse(ALIGN_SRC)
    out = a.assemble()
    code = b''.join(x[1] for x in out)
    return code, a.sym


def align_bytes(align_addr, table, cave=None):
    code, _ = align_assembly(align_addr, table, cave)
    if len(code) > ALIGN_RESERVE:
        raise FontPatchError('the align cave (%d bytes) does not fit its %d byte reserve' % (len(code), ALIGN_RESERVE))
    return code


def align_symbols(align_addr, table, cave=None):
    return align_assembly(align_addr, table, cave)[1]


def align_mode(mode=None):
    """resolve the align mode: explicit argument, else the environment variable SAKA_ALIGN_MODE, else 'default'.
    default    snap in ALIGN_SNAP_FILES (PLNUMSET) + the player-card panel (CAP_SLCT / ENDOPT / EVENT)
    snap-only  snap in ALIGN_SNAP_FILES, no panel edits            panel-only  panel edits, no snap anywhere
    snap-all   snap in EVERY hooked overlay + panel (the stage 8b wiring, kept for experiments)"""
    m = mode if mode not in (None, True) else os.environ.get(ALIGN_MODE_ENV) or 'default'
    if m not in ALIGN_MODES:
        raise FontPatchError('unknown align mode %r (one of %s)' % (m, ', '.join(ALIGN_MODES)))
    return m


def _words(d):
    return struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])


def panel_scan(d, name=''):
    """the shared player-card panel of one overlay: ([offset of each idiom's `shll2`], [file offsets of the strlen literal pools]).
    Raises FontPatchError when the image does not hold exactly the known panel (changed, patched twice, or another build)."""
    ws = _words(d)
    sites = []
    for i in range(4, len(ws) - 12):
        w = ws[i]
        if w >> 12 != 6 or (w & 15) != 3:                 # mov rm,rn   (rn = temp copy, rm = the length)
            continue
        b, a = (w >> 8) & 15, (w >> 4) & 15
        win = ws[i + 1:i + 9]
        if not ((0x4000 | a << 8) in win and (0x4008 | a << 8) in win and (0x300C | a << 8 | b << 4) in win):
            continue
        if not any(ws[j] & 0xF00F == 0x000D and (ws[j] >> 8) & 15 == a for j in range(i - 4, i)):      # mov.w @(r0,rO),rL before
            continue
        if not any(ws[j] & 0xF00F == 0x0005 and (ws[j] >> 4) & 15 == b for j in range(i + 4, i + 12)):  # mov.w rT,@(r0,rW) after
            continue
        k = [j for j in range(i + 1, i + 9) if ws[j] == 0x4008 | a << 8][0]
        sites.append((i * 2, k * 2))
    if not sites:
        raise FontPatchError('%s: no right-anchored panel idiom found' % name)
    best = max(sites, key=lambda s0: sum(1 for s in sites if 0 <= s[0] - s0[0] < 0x800))
    sites = [s for s in sites if 0 <= s[0] - best[0] < 0x800]
    first = min(s[0] for s in sites)
    rel = tuple(s[1] - first for s in sites)
    if rel != PANEL_SITES_REL:
        raise FontPatchError('%s: the panel idioms (%d found) do not match the known panel (%d expected; already patched or another image)'
                             % (name, len(rel), len(PANEL_SITES_REL)))
    pools = set()
    for i in range(len(ws)):
        w = ws[i]
        if w >> 12 == 0xD:                                  # mov.l @(d,pc),rn
            at = i * 2
            lit = ((at + 4) & ~3) + (w & 0xFF) * 4
            if first - 0x1000 <= at < first and lit + 4 <= len(d) and struct.unpack_from('<I', d, lit)[0] == STRLEN_ADDR:
                pools.add(lit)
    prel = tuple(sorted(p - first for p in pools))
    if prel != PANEL_POOLS_REL:
        raise FontPatchError('%s: the strlen pools of the panel do not match the known panel: %s' % (name, prel))
    # every load of those literals anywhere in the image must be one of the 18 panel loads (a literal is shared by all loads that reach it)
    loads = []
    for i in range(len(ws)):
        w = ws[i]
        if w >> 12 == 0xD:
            at = i * 2
            if ((at + 4) & ~3) + (w & 0xFF) * 4 in pools:
                loads.append(at - first)
    if tuple(sorted(loads)) != PANEL_LOADS_REL:
        raise FontPatchError('%s: the strlen literals of the panel are also loaded elsewhere (or not by the expected calls): %s' % (name, sorted(loads)))
    return [s[1] for s in sites], sorted(pools)


def panel_edits(es, d, name, pw3_addr):
    """add the panel edits of one overlay image (18 `shll2` -> nop, 8 strlen literals -> pw3) to the EditSet.
    The 2 salary idioms (card + 104, a character count, not a pw3) keep their `shll2`.  Returns (nops, pool literals)."""
    shl, pools = panel_scan(d, name)
    sal = salary_sites(d, name)
    if not set(sal) <= set(shl):
        raise FontPatchError('%s: the salary idioms %s are not among the panel idioms' % (name, [hex(o) for o in sal]))
    nops = [o for o in shl if o not in sal]
    for o in nops:
        es.add('font.panel.nop', name, o, NOP, expect=d[o:o + 2])
    for o in pools:
        es.add('font.panel.len', name, o, struct.pack('<I', pw3_addr), expect=struct.pack('<I', STRLEN_ADDR))
    return len(nops), len(pools)


def salary_sites(d, name=''):
    """[file offset of the `shll2` of each salary idiom] of one panel overlay (exactly 2: state 1 and 2 of the placement function)"""
    out = []
    at = d.find(SALARY_SIG)
    while at >= 0:
        if at % 2 == 0:
            out.append(at + SALARY_SHLL2)
        at = d.find(SALARY_SIG, at + 1)
    if len(out) != 2 or any(d[o:o + 2] != SHLL2_R2 for o in out):
        raise FontPatchError('%s: expected 2 salary idioms (mov #104,r0 ... shll2 r2), found %d' % (name, len(out)))
    return out


# ------------------------------------------------------------------------------------------------ scanning
def find_sites(d, name=''):
    """[{variant, h1, h2}] file offsets of the layout function's hook sites inside one overlay image.  An image
    without the half-width advance signature gives []; a partial or inconsistent match raises FontPatchError."""
    sites = []
    for v in 'ABC':
        for st in FAMILIES[v].find(d, name):
            off = st.off
            h2 = off - H2_BACK[v]
            sites.append(dict(variant=v, h1=off, h2=h2 if h2 >= 0 and d[h2:h2 + len(H2_OLD[v])] == H2_OLD[v] else None))
    # variant A and C differ only in the pen register byte; B only in the offset byte: the exact templates are disjoint,
    # so one site cannot match twice, but a file must contain at most one layout function
    if len(sites) > 1:
        raise FontPatchError('%s: %d layout functions found' % (name, len(sites)))
    for s in sites:
        if s['h2'] is None:
            raise FontPatchError('%s: advance site found at %#x but the wrap block does not match the template' % (name, s['h1']))
        if (s['h2'] % 4) != H2_ALIGN[s['variant']]:
            raise FontPatchError('%s: wrap site %#x has the wrong alignment for its pc-relative literal' % (name, s['h2']))
    return sites


def overlay_edits(es, d, name, variants='A', wrap=True, cave_table=None, snap=False, small=False):
    """add the hook edits of one overlay image to the EditSet `es`; returns the sites.
    snap=True: the advance hook enters the align cave's `at_snap` (variant A only) instead of the font cave
    small=True: the advance hook enters the font cave's `sm_adv` (--small-prop, variant A only: 16 px windows get the scaled table advance)"""
    ct = placement(cave_table or DEFAULT_PLACEMENT)
    sites = [x for x in find_sites(d, name) if x['variant'] in variants]
    if snap and small:
        raise FontPatchError('%s: the blank-run snap and the small-prop entry exclude each other' % name)
    for x in sites:
        v = x['variant']
        if snap and v != 'A':
            raise FontPatchError('%s: the blank-run snap needs a variant A hook' % name)
        if small and v != 'A':
            raise FontPatchError('%s: the small-prop entry needs a variant A hook' % name)
        entry = align_address() if snap else (small_entry(ct) if small else None)
        es.add('font.h1', name, x['h1'], hook_h1(v, ct, entry), expect=H1_OLD[v])
        if wrap:
            es.add('font.h2', name, x['h2'], hook_h2(v, ct), expect=H2_OLD[v])
    return sites


def patch_overlay(d, name='', variants='A', wrap=True, cave_table=None, snap=False, small=False):
    """patch one overlay image (bytes).  Returns (new bytes, sites).  The image is returned unchanged with [] when it has
    no layout function or when its variant is not in `variants`.  The result has the same length."""
    es = PE.EditSet()
    sites = overlay_edits(es, d, name, variants, wrap, cave_table, snap, small)
    if not sites:
        return bytes(d), []
    try:
        out = es.apply({name: d})[name]
    except PE.EngineError as e:
        raise FontPatchError('%s: %s' % (name, e))
    assert len(out) == len(d)
    return out, sites


def check_placement(ct):
    """a (cave, table) pair must be a registered placement or must not collide with any registered cave"""
    if tuple(ct) in [tuple(v) for v in PLACEMENTS.values()]:
        return
    try:
        PE.REGISTRY.check_free(ct[0], RESERVE, 'font')
        PE.REGISTRY.check_free(ct[1], TABLE_SIZE, 'font')
    except PE.EngineError as e:
        raise FontPatchError(str(e))


def align_address():
    """address of the registered `font.align` cave (tail placement only)"""
    return PE.REGISTRY.addr('font.align')


# ------------------------------------------------------------------------------------------------ --lin-center
# The LINEAR text writer FUN_8c15e9c6 of 1ST_READ.BIN (GAME.BIN match intro 'Stadium' / 'KICK OFF', the in-match OPTIONS rows, ENDING,
# DMCLBEDT, OPTION ...: every string that is NOT drawn by the tsString window library, so it never sees the proportional hook) copies one
# 6 byte row of a 12 x 24 half-width glyph per loop pass into a fixed 12 px cell.  The proportional font moved every glyph's ink to the
# LEFT of its tile, so 'i', 'l', 'I', '!' ... sit at the left edge of a 12 px cell with a 7 px gap behind them (docs/layout-issues.md s16).
# `font.lin` (0x8c299600, 192 byte claim) replaces the 6 byte copy of the loop body: it reads the glyph's advance from the font table
# (the same table the proportional layout uses, at run time, so it works with every table: the default proportional one and the
# Roboto Condensed Medium one of --open-font) and, for a narrow glyph, shifts the 6 byte row right by k pixels (4 k bits, paper = nibble 15
# shifted in on the left):
#       k = (14 - adv) >> 1   for adv <= 9           k = (13 - adv) >> 1   for adv >= 10           (adv = 0 = unlisted: k = 0; adv >= 13: k = 0)
# i.e. the ink block is centred in the 12 px tile.  A zero advance (unlisted code) and every glyph with k = 0 are copied unchanged.
# Hook: the 42 bytes of the loop body (file 0x14ea22 .. 0x14ea4c: `mov r4,r2 ; add #8,r2 ; pref @r2` and six `mov.b @r4+,r2 ; mov.b r2,@r14 ;
# add #1,r14`) become `mov.l lit,r1 ; jsr @r1 ; nop ; bra done ; nop ; .long cave ; nop ...`; `add r6,r14` at 0x14ea4c stays.  The writer saved PR
# itself (sts.l pr,@-r15), so the jsr costs nothing; the cave keeps r4-r6, r13, r14, r15 and PR and clobbers r0-r3 and r7 (dead there: the
# loop reloads r2 / r3 itself and the epilogue only restores r13, r14, PR).
LIN_SITE = 0x8C15EA22 - IMG_BASE             # first word of the loop body
LIN_OLD = bytes.fromhex('436208728302' + '4462202e017e' * 6)                      # the 21 words the hook replaces
LIN_BEFORE = bytes.fromhex('3c36')           # add r3,r6  (the word in front of the body; part of the signature)
LIN_AFTER = bytes.fromhex('6c3e5825e78fff75')                                     # add r6,r14 ; tst r5,r5 ; bf/s body ; add #-1,r5
LIN_RESERVE = 0xC0                           # registry claim 'font.lin' (the cave is exactly 192 bytes; 0x8c2996c0.. belongs to `font.cell`)


def _lin_words():
    """the SH-4 instructions the assembler lacks, as raw words: shld, swap.b, mov.b Rm,@Rn"""
    def shld(m, n):
        return '.word 0x%04x' % (0x400D | (n << 8) | (m << 4))

    def swb(m, n):
        return '.word 0x%04x' % (0x6008 | (n << 8) | (m << 4))

    def stb(m, n):
        return '.word 0x%04x' % (0x2000 | (n << 8) | (m << 4))
    return shld, swb, stb


LIN_SRC = """
lin_row: mov.l @(tblp,pc),r1          ; r4 = source row (6 bytes), r14 = dest, r13 = glyph index (r5 r6 r13 r14 r15 PR kept)
        extu.w r13,r0
        mov   #96,r2
        cmp/ge r2,r0
        bt    lr_hi
        bra   lr_have
        add   #32,r0                  ; index < 96: byte = index + 32
lr_hi:  add   #64,r0                  ; index >= 96: byte = index + 64
lr_have: mov.b @(r0,r1),r0            ; advance from the font table (0 = unlisted)
        tst   r0,r0
        bt    lr_copy
        mov   #14,r2
        sub   r0,r2                   ; 14 - adv
        mov   #9,r3
        cmp/gt r3,r0
        bf    lr_nf
        add   #-1,r2                  ; adv >= 10: 13 - adv
lr_nf:  cmp/pl r2
        bf    lr_copy                 ; <= 0: wide glyph, unchanged
        shar  r2                      ; k = floor(.. / 2) pixels of left margin
        tst   r2,r2
        bt    lr_copy
        shll2 r2                      ; s = 4 k bits (4 .. 20)
        mov.w @r4+,r1
        {swb11}
        extu.w r1,r1
        mov.w @r4+,r3
        {swb33}
        extu.w r3,r3
        shll16 r1
        or    r3,r1                   ; hi = b0 b1 b2 b3 (big endian, high nibble = left pixel)
        mov.w @r4+,r7
        {swb77}
        extu.w r7,r7
        shll16 r7                     ; lo = b4 b5 << 16
        neg   r2,r3
        {sh37}                        ; lo >>>= s
        mov   #32,r3
        sub   r2,r3                   ; 32 - s
        mov   r1,r0
        {sh30}                        ; hi << (32 - s)
        or    r0,r7                   ; new lo
        mov   #-1,r0
        {sh30}                        ; 0xffffffff << (32 - s) : the s new left bits are paper (nibble 15)
        neg   r2,r3
        {sh31}                        ; hi >>>= s
        or    r0,r1                   ; new hi
        mov   r1,r0
        shlr16 r0
        shlr8 r0
        {st0}
        add   #1,r14
        mov   r1,r0
        shlr16 r0
        {st0}
        add   #1,r14
        mov   r1,r0
        shlr8 r0
        {st0}
        add   #1,r14
        {st1}
        add   #1,r14
        mov   r7,r0
        shlr16 r0
        shlr8 r0
        {st0}
        add   #1,r14
        mov   r7,r0
        shlr16 r0
        {st0}
        add   #1,r14
        rts
        nop
lr_copy:
{copy6}        rts
        nop
        .align 4
tblp:   .long TABLE
"""
LIN_HOOK_SRC = """
        mov.l @(lit,pc),r1
        jsr   @r1
        nop
        bra   done
        nop
lit:    .long CAVE
"""


def lin_source():
    shld, swb, stb = _lin_words()
    copy6 = ''.join('        mov.b @r4+,r2\n        %s\n        add #1,r14\n' % stb(2, 14) for _ in range(6))
    return LIN_SRC.format(swb11=swb(1, 1), swb33=swb(3, 3), swb77=swb(7, 7), sh37=shld(3, 7), sh30=shld(3, 0), sh31=shld(3, 1),
                          st0=stb(0, 14), st1=stb(1, 14), copy6=copy6)


def lin_address():
    """address of the registered `font.lin` cave (tail placement only)"""
    return PE.REGISTRY.addr('font.lin')


def lin_cave_bytes(table_addr):
    """the cave code assembled at its registered address, with the advance table literal `table_addr`"""
    import sh4asm2
    code = b''.join(x[1] for x in sh4asm2.Asm(lin_address(), {'TABLE': table_addr}).parse(lin_source()).assemble())
    if len(code) > LIN_RESERVE:
        raise FontPatchError('the lin-center cave (%d bytes) does not fit its %d byte reserve' % (len(code), LIN_RESERVE))
    return code


def lin_hook_bytes():
    """the 42 byte replacement of the loop body: jsr to the cave, then `bra` to the unchanged `add r6,r14`, NOP padding"""
    import sh4asm2
    site = LIN_SITE + IMG_BASE
    done = site + len(LIN_OLD)
    head = b''.join(x[1] for x in sh4asm2.Asm(site, {'CAVE': lin_address(), 'done': done}).parse(LIN_HOOK_SRC).assemble())
    if len(head) > len(LIN_OLD):
        raise FontPatchError('the lin-center hook (%d bytes) is longer than the loop body (%d bytes)' % (len(head), len(LIN_OLD)))
    return head + NOP * ((len(LIN_OLD) - len(head)) // 2)


def lin_find_site(k):
    """file offset of the loop body in 1ST_READ.BIN `k`, found by its exact bytes with the neighbouring words (add r3,r6 .. add r6,r14 ; tst r5,r5 ;
    bf/s ; add #-1,r5): exactly one place or FontPatchError (a patched, truncated or foreign image is refused)"""
    sig = LIN_BEFORE + LIN_OLD + LIN_AFTER
    hits = []
    i = k.find(sig)
    while i >= 0:
        hits.append(i + len(LIN_BEFORE))
        i = k.find(sig, i + 1)
    if len(hits) != 1:
        if not hits and k[LIN_SITE:LIN_SITE + len(LIN_OLD)] == lin_hook_bytes():
            raise FontPatchError('--lin-center: the linear text writer is already patched (hook found at %#x)' % (LIN_SITE + IMG_BASE))
        raise FontPatchError('--lin-center: the linear text writer loop of 1ST_READ.BIN was found %d times (expected exactly 1): foreign or damaged image' % len(hits))
    if hits[0] != LIN_SITE:
        raise FontPatchError('--lin-center: the loop body is at %#x, expected %#x: foreign image (the hook is built for %#x)' % (
            hits[0] + IMG_BASE, LIN_SITE + IMG_BASE, LIN_SITE + IMG_BASE))
    return hits[0]


def lin_k(adv):
    """the left margin in pixels the cave applies to a glyph of table advance `adv` (python reference of the cave arithmetic)"""
    if adv == 0:
        return 0
    return max(0, ((14 - adv) if adv <= 9 else (13 - adv)) >> 1)


def lin_edits(es, k, table_addr):
    """add the hook (signature checked) and the cave (zero checked) to the EditSet `es`"""
    site = lin_find_site(k)
    cave = lin_cave_bytes(table_addr)
    es.add('font.lin.hook', PE.IMG_NAME, site, lin_hook_bytes(), expect=LIN_OLD)
    es.add('font.lin', PE.IMG_NAME, lin_address() - IMG_BASE, cave + bytes(PE.REGISTRY.size('font.lin') - len(cave)), expect=PE.ZERO)


# ------------------------------------------------------------------------------------------------ --cell-prop
# The commentary subtitle (BCAST text) is drawn by the line engine 0x8c3202b0 of FLOW_PRG/GAME.BIN (base 0x8c2d0000), which writes a CONSTANT 12 px advance
# for every half-width character (`mov #12,r0 ; mov.b r0,@(1,r2)` at 0x8c32049e) and for every blank (`mov #12,r0` at 0x8c3204f2) into the 82 byte line record;
# the display loop 0x8c31fdc0 uses that byte as the sprite width, the UV width (x8) and the pen step.  The advance table at 0x8c299900 is never read there
# (the tsString hook, --align-fix and --lin-center all miss this path), so 'i', 'l', 't', 'f' ... are followed by 5-7 px of paper ('Fi r st hal f').
# `font.cell` (0x8c2996c0, the 64 spare bytes behind the 192 byte lin cave, 28 used) is the one routine `cell_adv(r4 = glyph code word) -> r0 = advance`:
# advance = table[code & 0xff] clamped to 12 (the 12 px sprite cell cannot show more), 0 (= unlisted) -> 12.  layoutpatch.patch_cell_prop rewrites the
# half-width block of the engine to call it (jsr from the overlay into the resident 1ST_READ tail, like the tsString hook) and the blank block to write the
# table's blank advance and to skip a blank at column 0 (the space that a wrap leaves at the start of the next line).
CELL_RESERVE = 0x40                          # registry claim 'font.cell'

CELL_SRC = """
cell_adv: extu.b r4,r0                ; r4 = compiled glyph (0x8000 | byte): the table is indexed by the byte
        mov.l @(tblp,pc),r1
        mov.b @(r0,r1),r0             ; advance (0 = unlisted)
        mov   #12,r1
        cmp/gt r1,r0
        bf    ca_ok
        mov   r1,r0                   ; > 12: clamp (the engine cell is 12 px wide)
ca_ok:  tst   r0,r0
        bf    ca_done
        mov   #12,r0                  ; 0: unlisted = 12
ca_done: rts
        nop
        .align 4
tblp:   .long TABLE
"""


def cell_address():
    """address of the registered `font.cell` cave (tail placement only)"""
    return PE.REGISTRY.addr('font.cell')


def cell_cave_bytes(table_addr):
    """the cell_adv code assembled at its registered address, with the advance table literal `table_addr` (28 bytes)"""
    import sh4asm2
    code = b''.join(x[1] for x in sh4asm2.Asm(cell_address(), {'TABLE': table_addr}).parse(CELL_SRC).assemble())
    if len(code) > CELL_RESERVE:
        raise FontPatchError('the cell-prop cave (%d bytes) does not fit its %d byte reserve' % (len(code), CELL_RESERVE))
    return code


def cell_space_adv(table):
    """the advance the commentary engine gives a blank: the table's blank entry (index 0, see proportional_font), 1..12, 0 = unlisted = 12"""
    s = table[0]
    return min(s, 12) if s else 12


def cell_edits(es, table_addr):
    """add the cave (zero checked: the 64 byte reserve is never used by another stage) to the EditSet `es`"""
    cave = cell_cave_bytes(table_addr)
    es.add('font.cell', PE.IMG_NAME, cell_address() - IMG_BASE, cave + bytes(PE.REGISTRY.size('font.cell') - len(cave)), expect=PE.ZERO)


def patch_1st_read(k, table_bytes, cave_table=None, scale=False, align=False, lin=False, small=False, cell=False):
    """write cave + table into the zero reserve of 1ST_READ.BIN; refuses unless both areas are all zero.
    scale=True: the --prop-scale cave (CAVE_SIZE_SCALE bytes, tail placement only: the gap1 reserve is 128 bytes).
    align=True: the --align-fix cave (`font.align`, ALIGN_SRC) is written too (tail placement only); the font cave itself is NOT changed.
    lin=True: the --lin-center hook (loop body of the linear text writer, signature checked) and cave `font.lin` (tail placement only).
    small=True: the --small-prop entry `sm_adv` is written into the unused tail of the font cave reserve (tail placement only).
    cell=True: the --cell-prop routine `cell_adv` (`font.cell`, CELL_SRC) is written (tail placement only); the GAME.BIN side is layoutpatch.patch_cell_prop."""
    cave, table = ct = placement(cave_table or DEFAULT_PLACEMENT)
    if small and tuple(ct) != tuple(PLACEMENTS['tail']):
        raise FontPatchError('--small-prop needs the tail placement (the gap1 reserve is 128 bytes)')
    if len(table_bytes) != TABLE_SIZE or max(table_bytes) > 24:
        raise FontPatchError('table must be %d bytes with values <= 24' % TABLE_SIZE)
    check_placement(ct)
    if (cave + CAVE_SIZE > table) and table > cave:
        raise FontPatchError('cave and table overlap')
    aaddr = None
    if lin and tuple(ct) != tuple(PLACEMENTS['tail']):
        raise FontPatchError('--lin-center needs the tail placement (the gap1 reserve has no room for the lin-center cave)')
    if cell and tuple(ct) != tuple(PLACEMENTS['tail']):
        raise FontPatchError('--cell-prop needs the tail placement (the gap1 reserve has no room for the cell cave)')
    if align:
        if tuple(ct) != tuple(PLACEMENTS['tail']):
            raise FontPatchError('--align-fix needs the tail placement (the gap1 reserve has no room for the align cave)')
        aaddr = align_address()
    code = cave_bytes(ct, scale, small)
    reserve = min(RESERVE, table - cave) if table > cave else RESERVE
    if len(code) > reserve:
        raise FontPatchError('cave of %d bytes does not fit its %d byte reserve' % (len(code), reserve))
    es = PE.EditSet({PE.IMG_NAME: IMG_BASE})
    es.add('font.cave', PE.IMG_NAME, cave - IMG_BASE, code + bytes(reserve - len(code)), expect=PE.ZERO)
    es.add('font.table', PE.IMG_NAME, table - IMG_BASE, bytes(table_bytes), expect=PE.ZERO)
    if align:
        acode = align_bytes(aaddr, table, cave)
        es.add('font.align', PE.IMG_NAME, aaddr - IMG_BASE, acode + bytes(PE.REGISTRY.size('font.align') - len(acode)), expect=PE.ZERO)
    if lin:
        lin_edits(es, k, table)
    if cell:
        cell_edits(es, table)
    try:
        return es.apply({PE.IMG_NAME: k})[PE.IMG_NAME]
    except PE.EngineError as e:
        raise FontPatchError(str(e))


# ------------------------------------------------------------------------------------------------ font: glyph art and table
HALF_W, HALF_H, HALF_ROW = 12, 24, 6
STRONG = 4                     # coverage (15 - nibble) that counts as "strong ink"; 1..3 = anti-aliasing fringe
DIGITS = tuple(range(0x30, 0x3A))
SPACE_ADV = 12   # skeptic D1: padded numeric fields (%2d, %4d ...) use pad spaces; they must keep the original 12 px pitch


def _cov(g):
    """per column coverage (max over rows of 15 - nibble) of a 144 byte 12x24 4bpp glyph (even column = high nibble)"""
    c = [0] * HALF_W
    for r in range(HALF_H):
        for col in range(HALF_W):
            b = g[r * HALF_ROW + (col >> 1)]
            c[col] = max(c[col], 15 - ((b >> 4) if col % 2 == 0 else (b & 15)))
    return c


def shift_glyph_left(g, n):
    """shift a 12x24 glyph left by n columns, paper (nibble 15) enters on the right.  Lossless for n <= leading blank columns."""
    out = bytearray(len(g))
    for r in range(HALF_H):
        nib = []
        for col in range(HALF_W):
            b = g[r * HALF_ROW + (col >> 1)]
            nib.append((b >> 4) if col % 2 == 0 else (b & 15))
        nib = nib[n:] + [15] * n
        for col in range(0, HALF_W, 2):
            out[r * HALF_ROW + (col >> 1)] = (nib[col] << 4) | nib[col + 1]
    return bytes(out)


def glyph_metrics(g):
    """(left blank columns, strong-ink right column) or None for a blank glyph"""
    c = _cov(g)
    if max(c) == 0:
        return None
    ink = [i for i in range(HALF_W) if c[i] >= 1]
    strong = [i for i in range(HALF_W) if c[i] >= STRONG] or ink
    return ink[0], strong[-1]


def advance_of(g):
    """advance in pixels of a LEFT ALIGNED glyph (hybrid rule H of docs/font-widths.md, reproduces tools/re/font/widths.json
    for all 159 non-blank glyphs): strong ink right column + 1 + gap, gap 1 when that extent is >= 8 px else 2."""
    m = glyph_metrics(g)
    if m is None:
        return SPACE_ADV
    left, sr = m
    ext = sr - left + 1
    return ext + (1 if ext >= 8 else 2)


def proportional_font(font_bytes, original_half=None, overrides=None, space=SPACE_ADV, open_font=None):
    """-> (new FONT.BIN bytes, 256-byte advance table).
    Shifts the half-width glyphs 0x21-0x7E (except the digits, which stay centred and 12 px wide so that numeric columns
    keep their pitch) and every katakana slot 0xA1-0xDF whose art differs from `original_half[i]` (= slots that the
    translators redrew for Latin use) to column 0 and derives the table from the result.  Table index 0 holds the SPACE
    advance (the string compiler's blank cell 0x2020 reaches the cave as 0x8000); indices without a rule hold 0 = "use 12".
    `overrides` {byte: px} (1..24) is applied last.
    `open_font` (opt-in, tools/openfont.py, docs/open-font.md): (glyphs {byte: 144 bytes}, 256-byte table) of the Roboto Condensed
    set.  The 94 slots 0x21-0x7E (digits included) get that art, which is already left aligned and grid fitted, so they are not
    shifted; the table (space, digits 12, advances) comes from the data file; katakana slots redrawn by the translators and
    `overrides` are handled as before."""
    import font as F
    f = F.Font(font_bytes)
    if open_font is not None:
        import openfont
        openfont.apply_glyphs(f, open_font[0])
    half = f.half()
    table = bytearray(TABLE_SIZE)
    targets = [b for b in range(0x21, 0x7F) if b not in DIGITS and open_font is None]
    if original_half is not None:
        targets += [b for b in range(0xA1, 0xE0) if half[F.half_index(b)] != original_half[F.half_index(b)]]
    for b in targets:
        i = F.half_index(b)
        g = half[i]
        m = glyph_metrics(g)
        if m is None:
            continue
        g2 = shift_glyph_left(g, m[0]) if m[0] else g
        if g2 != g:
            f.set_half(i, g2)
        table[b] = advance_of(g2)
    if open_font is not None:
        for b in range(0x21, 0x7F):
            table[b] = open_font[1][b]
        space = open_font[1][0x20]
    for b in DIGITS:
        table[b] = 12
    table[0x20] = table[0x00] = space
    for b, px in (overrides or {}).items():
        if not 1 <= px <= 24:
            raise FontPatchError('advance override for %#x must be 1..24' % b)
        table[b] = px
    return f.build(), bytes(table)


def parse_overrides(obj):
    """{"0x41": 12, "A": 12} -> {0x41: 12}"""
    out = {}
    for k, v in (obj or {}).items():
        b = int(k, 0) if (len(k) > 1 and k[0] == '0' and k[1] in 'xX') else ord(k)
        if not 0 <= b < 256 or not isinstance(v, int):
            raise FontPatchError('bad advance override %r: %r' % (k, v))
        out[b] = v
    return out


# ------------------------------------------------------------------------------------------------ build API
def overlay_paths(root=EXTRACTED):
    """relative paths of every overlay image that can carry the tsString library"""
    r = sorted('FLOW_PRG/' + os.path.basename(p) for p in glob.glob(os.path.join(root, 'FLOW_PRG', '*.BIN')))
    return r + ['ATFIRST/HELP.BIN']


def make_patches(read, current=None, variants='A', wrap=True, place=DEFAULT_PLACEMENT, overrides=None,
                 expect=None, paths=None, glyphs=True, font_copies=('FONT.BIN', 'ATFIRST/FONT.BIN'), prop_scale=False,
                 align_fix=False, open_font=None, lin_center=False, small_prop=False, small_files=None, cell_prop=False):
    """The whole feature as a function.  `read(rel)` returns the ORIGINAL bytes of an extracted file ('FLOW_PRG/MEETING.BIN');
    `current` {iso path: bytes} are files already patched by earlier pipeline stages (they are composed upon: the hooks
    are found by signature in the current bytes).  Returns ({iso path: bytes} for every file that changes, report dict).
    iso paths carry a leading '/'.  `expect` {variant: count} makes a differing count a hard error (guards a damaged image).
    `prop_scale` (opt-in, default off): windows with an advance other than 24 use the table scaled by A/24 (see CAVE_SCALE_SRC).
    `align_fix` (default off here, recommended ON in the build): the cell-count alignment fixes of ALIGN_SRC (blank-run columns in the
    overlays of ALIGN_SNAP_FILES, the right-anchored player-card panel of CAP_SLCT / ENDOPT / EVENT); needs variants == 'A' and the tail
    placement.  True = align_mode() (environment SAKA_ALIGN_MODE, default 'default'); a string selects the mode (ALIGN_MODES).
    `lin_center` (default off here, ON in the build): the linear-text glyph centring hook of 1ST_READ.BIN (LIN_SRC, docs/layout-issues.md s16);
    needs glyphs=True and the tail placement, touches 1ST_READ.BIN only (hook 42 bytes + cave `font.lin`).
    `small_prop` (default off): the advance hook of the overlays in `small_files` (default SMALL_FILES: OPTION, TRAINING) enters `sm_adv`, 16 px windows
    get the table scaled by 2/3 (SMALL_SRC); needs glyphs=True, variants == 'A' and the tail placement; 1ST_READ.BIN differs only in the unused tail of
    the font cave reserve, every other window of those overlays and every other overlay is byte-identical.
    `cell_prop` (default off here, ON in the build): the `cell_adv` routine of the GAME.BIN commentary line engine (CELL_SRC) in `font.cell`; needs glyphs=True
    and the tail placement, touches 1ST_READ.BIN only (28 bytes in the spare 64 behind the lin cave); the report carries rep['cell'] (address) and rep['cell_space']
    (the blank advance for layoutpatch.patch_cell_prop).  The overlay edit itself is layoutpatch.patch_cell_prop (build_patch.apply_prop_font)."""
    current = current or {}
    if open_font is not None and not glyphs:
        raise FontPatchError('open_font needs glyphs=True (the control table keeps the original glyphs)')
    if small_prop and (not glyphs or place != DEFAULT_PLACEMENT or variants != 'A'):
        raise FontPatchError("small_prop needs glyphs=True (a proportional table), variants='A' and the tail placement")
    smalls = tuple(small_files if small_files is not None else SMALL_FILES)
    if lin_center and (not glyphs or place != DEFAULT_PLACEMENT):
        raise FontPatchError('lin_center needs glyphs=True (a proportional table) and the tail placement')
    if cell_prop and (not glyphs or place != DEFAULT_PLACEMENT):
        raise FontPatchError('cell_prop needs glyphs=True (a proportional table) and the tail placement')
    if align_fix and (variants != 'A' or place != DEFAULT_PLACEMENT or not wrap):
        raise FontPatchError("align_fix needs variants='A', the tail placement and the wrap hook")
    amode = align_mode(align_fix) if align_fix else None
    do_snap = amode in ('default', 'snap-all', 'snap-only')
    do_panel = amode in ('default', 'snap-all', 'panel-only')

    def cur(rel):
        return current.get('/' + rel) or read(rel)
    ct = placement(place)
    out, rep = {}, dict(sites={'A': 0, 'B': 0, 'C': 0}, files=[], cave=ct[0], table_addr=ct[1], variants=variants, wrap=wrap, prop_scale=bool(prop_scale),
                        align_fix=bool(align_fix), panel=[], align_mode=amode, snap=[], lin_center=bool(lin_center), small=[], cell_prop=bool(cell_prop))
    # font first: the table is derived from the root (loaded) copy
    font_orig = read('FONT.BIN')
    import font as F
    orig_half = F.Font(font_orig).half()
    if glyphs:
        new_root, table = proportional_font(cur('FONT.BIN'), orig_half, overrides, open_font=open_font)
        for copy in font_copies:
            data = cur(copy)
            nd, _ = proportional_font(data, orig_half, overrides, open_font=open_font)
            if nd != data:
                out['/' + copy] = nd
        rep['table'] = table
    else:
        table = bytes([12]) * TABLE_SIZE               # every character 12 px: bit-identical to the original game
        rep['table'] = table
    k = patch_1st_read(cur('1ST_READ.BIN'), table, ct, scale=prop_scale, align=align_fix, lin=lin_center, small=small_prop, cell=cell_prop)
    out['/1ST_READ.BIN'] = k
    if lin_center:
        rep['lin'] = lin_address()
    if cell_prop:
        rep['cell'] = cell_address()
        rep['cell_space'] = cell_space_adv(table)
    if align_fix:
        rep['align'] = align_address()
        pw3 = align_symbols(align_address(), ct[1], ct[0])['pw3']
        rep['pw3'] = pw3
    for rel in (paths if paths is not None else overlay_paths()):
        d = cur(rel)
        snap = bool(align_fix and do_snap and (amode == 'snap-all' or rel in ALIGN_SNAP_FILES))
        small = bool(small_prop and rel in smalls)
        nd, sites = patch_overlay(d, rel, variants, wrap, ct, snap, small)
        if small and sites:
            rep['small'].append(rel)
        if snap and sites:
            rep['snap'].append(rel)
        if align_fix and do_panel and rel in ALIGN_FILES:
            es = PE.EditSet()
            n_nop, n_pool = panel_edits(es, nd, rel, pw3)
            try:
                nd = es.apply({rel: nd})[rel]
            except PE.EngineError as e:
                raise FontPatchError('%s: %s' % (rel, e))
            rep['panel'].append((rel, n_nop, n_pool))
        if sites:
            out['/' + rel] = nd
            rep['files'].append((rel, sites[0]['variant']))
            for s in sites:
                rep['sites'][s['variant']] += 1
    if expect is not None:
        for v, n in expect.items():
            if rep['sites'][v] != n:
                raise FontPatchError('expected %d variant-%s overlays, patched %d' % (n, v, rep['sites'][v]))
    return out, rep


EXPECTED_SITES = {'A': 98, 'B': 0, 'C': 0}            # with variants='A'; 'ABC' gives 98 / 6 / 1


def read_extracted(rel):
    with open(os.path.join(EXTRACTED, *rel.split('/')), 'rb') as f:
        return f.read()


# ------------------------------------------------------------------------------------------------ live bridge script
def lua_source():
    """text of tools/emu/fonttest.lua (self-contained: embeds cave, table, shifted glyphs and the hook templates)."""
    import font as F
    font = read_extracted('FONT.BIN')
    orig = F.Font(font)
    new, table = proportional_font(font, orig.half())
    nf = F.Font(new)
    ct = placement(DEFAULT_PLACEMENT)
    base = 0x8CD5C000 + nf.hdr[3]                      # RAM address of the half-width block (FONT.BIN is loaded at 0x8cd5c000)
    glyphs = []
    for b in range(0x21, 0x7F):
        i = F.half_index(b)
        if nf.half()[i] != orig.half()[i]:
            glyphs.append((b, nf.half()[i].hex(), orig.half()[i].hex()))
    L = []
    w = L.append
    w(open(os.path.join(HERE, 'emu', 'fonttest.lua.in'), encoding='utf8').read())
    data = []
    data.append('local CAVE, TABLE = 0x%08X, 0x%08X' % ct)
    data.append('local CAVE_HEX = "%s"' % cave_bytes(ct).hex())
    data.append('local TABLE_HEX = "%s"' % table.hex())
    data.append('local FIXED_HEX = "%s"' % (bytes([12]) * 256).hex())
    data.append('local HALF_BASE = 0x%08X   -- RAM address of the 160 half-width glyphs (%d bytes each)' % (base, F.HALF_BYTES))
    data.append('local HALF_IDX = {%s}' % ', '.join('[%d]=%d' % (b, F.half_index(b)) for b, _, _ in glyphs))
    data.append('local GLYPH_NEW = {\n%s\n}' % '\n'.join('  [%d]="%s",' % (b, n) for b, n, _ in glyphs))
    data.append('local GLYPH_OLD = {\n%s\n}' % '\n'.join('  [%d]="%s",' % (b, o) for b, _, o in glyphs))
    tmpl = []
    for v in 'ABC':
        tmpl.append('  %s = {h1_old="%s", h1_new="%s", h2_old="%s", h2_new="%s", h2_back=%d}' % (
            v, H1_OLD[v].hex(), hook_h1(v, ct).hex(), H2_OLD[v].hex(), hook_h2(v, ct).hex(), H2_BACK[v]))
    data.append('local VARIANTS = {\n%s\n}' % ',\n'.join(tmpl))
    return L[0].replace('--@@DATA@@', '\n'.join(data))


# ------------------------------------------------------------------------------------------------ CLI
def cmd_scan():
    from collections import Counter
    cnt, fl = Counter(), []
    for rel in overlay_paths():
        d = read_extracted(rel)
        for s in find_sites(d, rel):
            cnt[s['variant']] += 1
            fl.append((rel, s['variant'], s['h1'], s['h2']))
    print('sites', sum(cnt.values()), dict(cnt))
    for rel, v, h1, h2 in fl:
        print('%-28s %s h1@%#x h2@%#x' % (rel, v, h1, h2))


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ''
    sys.path.insert(0, HERE)
    if cmd == 'scan':
        cmd_scan()
    elif cmd == 'table':
        import font as F
        new, table = proportional_font(read_extracted('FONT.BIN'), F.Font(read_extracted('FONT.BIN')).half())
        print(' '.join('%02x:%d' % (b, table[b]) for b in range(0x00, 0x80) if table[b]))
        a = [table[b] for b in range(0x21, 0x7F)]
        print('mean ASCII advance %.2f px (fixed font: 12)' % (sum(a) / len(a)))
    elif cmd == 'patch':
        out, rep = make_patches(read_extracted, variants='ABC' if '--all' in argv else 'A', align_fix='--align-fix' in argv)
        print('patched files:', len(out), 'sites', rep['sites'], 'cave %#x table %#x' % (rep['cave'], rep['table_addr']))
        if rep['align_fix']:
            print('align fix: cave %#x, pw3 %#x, panel overlays %s' % (rep['align'], rep['pw3'], rep['panel']))
        if '--dump' in argv:
            dd = argv[argv.index('--dump') + 1]
            for iso, data in out.items():
                p = os.path.join(dd, *iso.strip('/').split('/'))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'wb').write(data)
    elif cmd == 'lua':
        p = os.path.join(HERE, 'emu', 'fonttest.lua')
        open(p, 'w', encoding='utf8', newline='\n').write(lua_source())
        print('wrote', p)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    sys.exit(main(sys.argv))
