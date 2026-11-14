"""Layout fixes that need a code change in an overlay (docs/layout-issues.md).  Pure stdlib, deterministic, same-size patches.

HOMETOWN.BIN "list label spacer" (FUN at 0x8c2d2a50, file offset 0x2a50)
------------------------------------------------------------------------
The Hometown screen builds one text object per region (12), prefecture (50), kana tab (52) and town (1,270) through this
routine.  It treats the string as a Japanese word and justifies it:

    strlen == 4  (2 full-width chars)   ->  ' ' + c1 + 0x8140 (full-width blank, 24 px) + c2
    strlen == 6  (3 full-width chars)   ->  ' ' + c1 + ' ' + c2 + ' ' + c3  (half-width blanks between the 2-byte pairs)
    anything else                        ->  ' ' + string

An ASCII string of 4 or 6 bytes is cut into 2-byte pairs: 'Tohoku' -> ' To ho ku', 'Kansai' -> ' Ka ns ai', 'Kyushu' ->
' Ky us hu', 'Nara' -> ' Na<24 px gap>ra'.  The fix turns the two length tests (`cmp/eq #4,r0` at 0x2ab4 and `cmp/eq #6,r0`
at 0x2ade) into `cmp/eq #-1,r0`, which strlen can never satisfy, so every string takes the plain ' ' + string path.  The only
side effect: a string that is still Japanese in those lists loses its (purely cosmetic) justification.

Club / hometown name composition "separator + no truncation" (20 overlays)
-----------------------------------------------------------------------------------------------------------
The game builds club names from pieces with no separator, at display time, from (municipality index, prefecture index, pool word,
mode).  The library routine is linked into 20 overlays (HOMETOWN, EVENT, SCHE0/1, BPMATCH, the save / load screens ...):

  town_short(idx, buf)  (file 0x10648 in HOMETOWN)   sprintf(buf, "%s", townptr[idx]); n = strlen(buf); if (n >= 2) buf[n-2] = 0
  pref_short(idx, buf)  (0x106b0)                    the same on the prefecture table; strips 4 for idx 14 / 48 (...諸島), 0 for idx 0
                                                     (北海道), else 2   (the Japanese 市 / 町 / 村 / 郡 / 県 / 府 / 都 are one 2-byte kanji)
  club_name(town, pref, pool, mode, out)  (0x1072a)  sprintf(out, "%s%s", short, pool[word]) (modes 0 / 2) or (pool[word], short) (1 / 3)

For English text that is wrong twice: it cuts the last two LETTERS ('Kagoshima' -> 'Kagoshi', 'Yokohama' -> 'Yokoh') and it glues
the pieces ('KagoshiMythos', 'ShadowsYokoh').  HOMETOWN.BIN also has an inline copy of the 4-candidate builder (rival / own club
choice popup) that uses the same two helpers and its own '%s%s' literal (file 0x467e0).  The patch (same size everywhere):

  1. town_short:  `add #-2,r5` (0x75fe at +2 of the signature) -> `add #0,r5`          no truncation of the municipality name
  2. pref_short:  the generic `add #-2,r4` (0x74fe) -> `add #0,r4`; the `add #-4,r4` of idx 14 / 48 stays ('Izu Is.' -> 'Izu',
                  'Amami Is.' -> 'Amami', which is exactly the Japanese rule: strip the 諸島)
  3. the composer's format "%s%s" (8-byte slot, only 5 bytes used, the literal is referenced exactly once) -> "%s %s", so the
     club reads 'Yokohama Shadows' / 'Shadows Yokohama'; the inline copy in HOMETOWN (0x467e0) likewise.

  4. (guard, default on, `guard=False` / build flag `--club-guard off` restores the old behaviour)  the composer itself (232 bytes at
     signature + 0x90, byte-identical in the 20 overlays, verified by SHA-256) is REPLACED IN PLACE by a bounded composer of
     224 bytes that never writes more than 13 characters + NUL into the caller's club-name buffer (14 bytes, `#sname#` at
     struct offset 0x103a, see docs/layout-issues.md section 9):  `town + ' ' + word` is kept when it fits; otherwise the TOWN part
     is cut to the room left (12 - len(word), at least 4) and ends in '.' (`dot=True`); the club word is only cut when it is longer
     than 8 characters (no real word is).  It reuses the composer's own literal pool slots (strlen, pool table) and the two helpers
     town_short / pref_short through bsr, so no cave and no new literal is needed.  HOMETOWN never calls its composer copy (it has an
     inline popup builder with four sprintf("%s %s") calls through one literal), so there the dead copy is replaced by a 230 byte
     sprintf-compatible join entry and that literal is retargeted to it: the popup preview equals the final name.

Everything is located by byte signature (the 20 overlays are identical there), the load base is derived from the format literal
and must be 64 KiB aligned, and a second application or a changed image raises LayoutPatchError.
The English text side (full municipality names in both the pointer table and the 126-byte records, message formats
'%s %s') is in translation/*.jsonl.

Public API: patch_hometown(bytes) -> bytes (raises LayoutPatchError if the expected bytes are not found),
make_patches(read_extracted, current, guard=True, dot=True, room=12) -> {iso path: bytes} for build_patch.py (composes on the CURRENT bytes of the overlay, so
text repacking done before is kept); patch_clubnames(data, name, guard, dot, room) for one overlay; composer_bytes() / composer_source() = the SH-4 code.
"""

import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOMETOWN_ISO = '/FLOW_PRG/HOMETOWN.BIN'

# (file offset, expected bytes, new bytes) -- little-endian SH-4 halfwords
SITES = [
    (0x2ab4, bytes.fromhex('0488'), bytes.fromhex('ff88')),     # cmp/eq #4,r0  -> cmp/eq #-1,r0
    (0x2ade, bytes.fromhex('0688'), bytes.fromhex('ff88')),     # cmp/eq #6,r0  -> cmp/eq #-1,r0
]
# context that must surround the patch sites (identifies the function, not just two halfwords)
SIG_A = bytes.fromhex('0488128f0279' '02e60b4d')                 # cmp/eq #4,r0; bf/s; add #2,r9; mov #2,r6; jsr @r13
SIG_B_TAIL = bytes.fromhex('02e60b4d')                           # (cmp/eq #6,r0; bf <disp>;) mov #2,r6; jsr @r13


class LayoutPatchError(Exception):
    pass


def patch_hometown(data):
    d = bytearray(data)
    if bytes(d[0x2ab4:0x2ab4 + len(SIG_A)]) != SIG_A:
        raise LayoutPatchError('HOMETOWN.BIN: list-label spacer (cmp/eq #4) not at 0x2ab4')
    if bytes(d[0x2ade:0x2ae0]) != SITES[1][1] or bytes(d[0x2ae2:0x2ae6]) != SIG_B_TAIL:
        raise LayoutPatchError('HOMETOWN.BIN: list-label spacer (cmp/eq #6) not at 0x2ade')
    for off, old, new in SITES:
        assert bytes(d[off:off + 2]) == old
        d[off:off + 2] = new
    return bytes(d)


# --------------------------------------------------------------------------- club / hometown name composition
CLUB_OVERLAYS = ['AUTOSAVE', 'BACKUP', 'BPMATCH', 'CHALMODE', 'CSAVE', 'CSAVE3', 'CSAVE4', 'DMCLBEDT', 'ENDOPT', 'EVENT', 'EXFLAG',
                 'EXTRADE', 'FREELOAD', 'HOMETOWN', 'LOAD', 'SCHE0', 'SCHE1', 'SONGSAVE', 'SPF_READ', 'VTRLOAD']
CLUB_SIG_A = bytes.fromhex('4365fe7500e35c3e302e')      # mov r4,r5; add #-2,r5; mov #0,r3; add r5,r14; mov.b r3,@r14   (town_short)
CLUB_SIG_A_NEW = bytes.fromhex('4365007500e35c3e302e')  # add #0,r5
CLUB_B_DELTA = 0x78                                     # pref_short strip pair is 0x78 bytes after the town_short signature
CLUB_B_OLD = bytes.fromhex('fc74fe74')                  # add #-4,r4 (idx 14 / 48) ; add #-2,r4 (everything else)
CLUB_B_NEW = bytes.fromhex('fc740074')                  # add #-4,r4 ; add #0,r4
CLUB_FMT_DELTA = 0x1a6                                  # the composer's literal pool: pointer to its "%s%s" is this far after the signature
CLUB_FMT_OLD = b'%s%s\x00\x00'
CLUB_FMT_NEW = b'%s %s\x00'
CLUB_FMT_CTX = b'%s%s\x00\x00\x00\x00Ille'            # composer format: followed by the 'Ille...' string in the 8-byte slot
CLUB_INLINE_CTX = b'%s%s\x00\x00\x00\x00%d selected\x00'  # HOMETOWN's inline candidate builder
CLUB_BASES = range(0x8c2b0000, 0x8cd60000, 0x10000)

# --- bounded composer (guard) ---------------------------------------------------------------------------------------------
COMP_DELTA = 0x90                                       # composer start = town_short signature + 0x90
COMP_LEN = 232                                          # original composer: 0x8c2e072a .. 0x8c2e0812 (HOMETOWN), then the literal pool
COMP_SHA256 = 'b4ff79d3f58e67560e751bfb764799f5a6d87267490af07146da7c9c953d2317'
COMP_TOWN_SHORT = -0xe2                                 # town_short / pref_short entry relative to the composer (bsr targets)
COMP_PREF_SHORT = -0x7a
COMP_L_SPRINTF = 0xfe                                   # slot of the library sprintf (HOMETOWN's popup join check)
COMP_L_STRLEN = 0x102                                   # composer literal pool slots (shared layout in all 20 overlays)
COMP_L_TOWNTBL = 0xf6
COMP_L_PREFTBL = 0x10e
COMP_L_POOLTBL = 0x11a
CLUB_ROOM = 12                                          # club name buffer 14 bytes = 13 characters + NUL; town + ' ' + word <= 13
CLUB_MIN_TOWN = 4                                       # the town keeps at least this many characters (the word is cut first below that)

_COMP_ENTRY = """
  mov.l r14,@-r15
  mov.l r13,@-r15
  mov.l r12,@-r15
  mov.l r11,@-r15
  mov.l r10,@-r15
  mov.l r9,@-r15
  mov.l r8,@-r15
  sts.l pr,@-r15
  add #-76,r15
  mov #108,r0
  mov.l @(r0,r15),r12
  mov r6,r11
  mov #55,r2
  cmp/hs r2,r11
  bf pool_ok
  mov #0,r11
pool_ok:
  mov.l @(L_POOL,pc),r9
  mov r11,r0
  shll2 r0
  mov.l @(r0,r9),r13
  mov r15,r14
  add #12,r14
  mov r7,r0
  mov #3,r2
  and r2,r0
  mov r0,r10
  mov #2,r2
  tst r2,r0
  bt is_town
  mov r5,r4
  bsr PREF_SHORT
  mov r14,r5
  bra joined
  nop
is_town:
  bsr TOWN_SHORT
  mov r14,r5
"""
# HOMETOWN only: the candidate popup builds its four strings with the library sprintf("%s %s", ...) through ONE literal; that literal is
# pointed at this entry (sprintf calling convention: r4 = destination, @r15 = format, @(4,r15) and @(8,r15) = the two strings; the
# one that equals the club word buffer is the word).  The town string is first copied into this routine's own frame, so the caller's
# buffers are never modified (the cut / '.' is written into the copy).  It replaces the composer copy, which HOMETOWN never calls.
_JOIN_ENTRY = """
  mov.l @(4,r15),r5
  mov.l @(8,r15),r6
  mov.l r14,@-r15
  mov.l r13,@-r15
  mov.l r12,@-r15
  mov.l r11,@-r15
  mov.l r10,@-r15
  mov.l r9,@-r15
  mov.l r8,@-r15
  sts.l pr,@-r15
  add #-76,r15
  mov r4,r12
  mov.l @(L_WORD,pc),r1
  cmp/eq r1,r5
  movt r10
  mov r5,r8
  mov r6,r13
  bf no_swap
  mov r6,r8
  mov r5,r13
no_swap:
  mov.l @(L_STRLEN,pc),r2
  jsr @r2
  mov r8,r4
  mov r0,r6
  add #1,r6
  mov #63,r2
  cmp/gt r2,r6
  bf len_ok
  mov r2,r6
len_ok:
  mov r15,r14
  add #12,r14
  mov r14,r4
  bsr cp
  mov r8,r5
  add #-1,r4
  mov #0,r1
  mov.b r1,@r4
"""
_COMP_JOIN = """joined:
  mov.l @(L_STRLEN,pc),r8
  jsr @r8
  mov r13,r4
  mov r0,r9
  jsr @r8
  mov r14,r4
  mov r0,r11
  mov #@ROOM@,r3
  sub r9,r3
  mov #4,r2
  cmp/ge r2,r3
  bt cap_ok
  mov r2,r3
cap_ok:
  cmp/gt r3,r11
  bf fits
  mov r3,r11
  mov r14,r2
  add r11,r2
  mov #0,r1
  mov.b r1,@r2
"""
_COMP_DOT = """  mov #46,r1
  add #-1,r2
  mov.b r1,@r2
"""
_COMP_TAIL = """fits:
  mov #@ROOM@,r3
  sub r11,r3
  cmp/gt r3,r9
  bf word_ok
  mov r3,r9
word_ok:
  mov r12,r4
  mov #1,r2
  mov r10,r0
  tst r2,r0
  bf word_first
  mov r14,r5
  bsr cp
  mov r11,r6
  mov #32,r1
  mov.b r1,@r4
  add #1,r4
  mov r13,r5
  bsr cp
  mov r9,r6
  bra done
  nop
word_first:
  mov r13,r5
  bsr cp
  mov r9,r6
  mov #32,r1
  mov.b r1,@r4
  add #1,r4
  mov r14,r5
  bsr cp
  mov r11,r6
done:
  mov r4,r0
  sub r12,r0
  mov #0,r1
  mov.b r1,@r4
  add #76,r15
  lds.l @r15+,pr
  mov.l @r15+,r8
  mov.l @r15+,r9
  mov.l @r15+,r10
  mov.l @r15+,r11
  mov.l @r15+,r12
  mov.l @r15+,r13
  rts
  mov.l @r15+,r14
cp:
  tst r6,r6
  bt cp_end
cp_loop:
  mov.b @r5+,r1
  mov.b r1,@r4
  add #1,r4
  dt r6
  bf cp_loop
cp_end:
  rts
  nop
"""


def composer_source(dot=True, room=CLUB_ROOM, popup=False):
    """SH-4 source of the bounded composer.  compose(r4 = municipality, r5 = prefecture, r6 = club word, r7 = mode, out = @sp)
    -> r0 = length; modes 0 / 2 = short + ' ' + word, 1 / 3 = word + ' ' + short; bit 1 selects the prefecture.
    popup=True: the HOMETOWN entry instead (sprintf-compatible join of two strings, see _JOIN_ENTRY); same bounded join behind it."""
    if not isinstance(room, int) or not 8 <= room <= 100:
        raise LayoutPatchError('club room %r: expected 8..100 (12 = a 14 byte buffer: 13 characters + NUL)' % (room,))
    src = (_JOIN_ENTRY if popup else _COMP_ENTRY) + _COMP_JOIN + (_COMP_DOT if dot else '') + _COMP_TAIL
    if popup:
        src += '  .align 4\nL_WORD:\n  .long WORD_PTR\n'
    return src.replace('@ROOM@', str(room))


def composer_bytes(origin, dot=True, room=CLUB_ROOM, popup_word=None):
    """assemble the bounded composer for a composer located at `origin` (any address with the right 4-byte phase).
    popup_word: the address of the club word buffer of HOMETOWN's candidate popup -> assemble the sprintf-compatible entry instead."""
    import re
    import sh4asm2

    class _Asm(sh4asm2.Asm):
        """sh4asm2 plus push / pop, sts.l / lds.l pr, mov.b / mov.l register-indirect stores and mov.l @(disp,Rm),Rn"""

        def _enc(self, line, a):
            m = re.match(r'^(\S+)\s*(.*)$', line)
            op, args = m.group(1).lower(), m.group(2).strip()
            ops = [x.strip() for x in re.split(r',(?![^()]*\))', args)] if args else []
            r = sh4asm2._r

            def f4(hi, n, mm, lo):
                return (hi << 12) | (n << 8) | (mm << 4) | lo
            if op == 'sts.l' and ops == ['pr', '@-r15']:
                return 0x4F22, 'sts.l pr,@-r15'
            if op == 'lds.l' and ops == ['@r15+', 'pr']:
                return 0x4F26, 'lds.l @r15+,pr'
            if op == 'mov.l' and len(ops) == 2:
                mm = re.match(r'^@\((\d+),(r\d+)\)$', ops[0].lower())
                if mm and int(mm.group(1)) % 4 == 0 and int(mm.group(1)) < 64:      # mov.l @(disp,Rm),Rn
                    return 0x5000 | (r(ops[1]) << 8) | (r(mm.group(2)) << 4) | (int(mm.group(1)) // 4), \
                        'mov.l @(%d,r%d),r%d' % (int(mm.group(1)), r(mm.group(2)), r(ops[1]))
            if op in ('mov.b', 'mov.l') and len(ops) == 2:
                sz = 0 if op == 'mov.b' else 2
                s, d = ops
                mm = re.match(r'^@-(r\d+)$', d.lower())
                if mm and s.lower().startswith('r'):
                    return f4(2, r(mm.group(1)), r(s), 4 + sz), '%s r%d,@-r%d' % (op, r(s), r(mm.group(1)))
                mm = re.match(r'^@(r\d+)\+$', s.lower())
                if mm:
                    return f4(6, r(d), r(mm.group(1)), 4 + sz), '%s @r%d+,r%d' % (op, r(mm.group(1)), r(d))
                mm = re.match(r'^@(r\d+)$', d.lower())
                if mm and s.lower().startswith('r') and not s.startswith('@'):
                    return f4(2, r(mm.group(1)), r(s), sz), '%s r%d,@r%d' % (op, r(s), r(mm.group(1)))
            return super()._enc(line, a)

    sym = {'TOWN_SHORT': origin + COMP_TOWN_SHORT, 'PREF_SHORT': origin + COMP_PREF_SHORT,
           'L_STRLEN': origin + COMP_L_STRLEN, 'L_POOL': origin + COMP_L_POOLTBL, 'WORD_PTR': popup_word or 0}
    out = _Asm(origin, sym).parse(composer_source(dot, room, popup_word is not None)).assemble()
    return b''.join(x[1] for x in out)


def _unique(d, pat):
    i = d.find(pat)
    if i < 0 or d.find(pat, i + 1) >= 0:
        return None
    return i


def _word_refs(d, word):
    """number of 4-aligned little-endian words == word"""
    pat = word.to_bytes(4, 'little')
    n = i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            return n
        if i % 4 == 0:
            n += 1
        i += 1


def _word_offs(d, word):
    """4-aligned file offsets of the little-endian word"""
    pat = word.to_bytes(4, 'little')
    out = []
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            return out
        if i % 4 == 0:
            out.append(i)
        i += 1


def _literal_loads(d, lit_off):
    """number of `mov.l @(disp,pc),Rn` instructions that load the longword at file offset lit_off"""
    import struct
    n = 0
    for o in range(0, len(d) - 1, 2):
        w = struct.unpack_from('<H', d, o)[0]
        if w >> 12 == 0xD and ((o + 4) & ~3) + (w & 0xFF) * 4 == lit_off:
            n += 1
    return n


def _calls_to(d, target_off):
    """direct bsr instructions to file offset target_off"""
    import struct
    n = 0
    for o in range(0, len(d) - 1, 2):
        w = struct.unpack_from('<H', d, o)[0]
        if w >> 12 == 0xB:
            disp = w & 0xFFF
            if disp & 0x800:
                disp -= 0x1000
            if o + 4 + disp * 2 == target_off:
                n += 1
    return n


def patch_clubnames(data, name="?", guard=True, dot=True, room=CLUB_ROOM):
    """town_short / pref_short truncation off, composer format '%s%s' -> '%s %s' (see module docstring).  Same size.
    guard=True (default): the composer is also replaced by the bounded composer (13 characters + NUL, docs/layout-issues.md section 9);
    dot=True: a town that had to be cut ends in '.'.  room = characters for town + word without the separator (default CLUB_ROOM = 12:
    a 14 byte buffer holds 13 characters + NUL); raise it only if the buffers are proven larger.
    guard=False keeps the original composer (names over 13 characters overflow)."""
    import struct
    d = bytearray(data)
    a = _unique(bytes(d), CLUB_SIG_A)
    if a is None:
        raise LayoutPatchError('%s: town_short signature not found exactly once (already patched, or another build)' % name)
    b = a + CLUB_B_DELTA
    if bytes(d[b:b + 4]) != CLUB_B_OLD:
        raise LayoutPatchError('%s: pref_short strip pair not at %#x' % (name, b))
    fmt_off = _unique(bytes(d), CLUB_FMT_CTX)
    if fmt_off is None:
        raise LayoutPatchError('%s: composer format string not found exactly once' % name)
    lit = struct.unpack_from('<I', d, a + CLUB_FMT_DELTA)[0]
    base = lit - fmt_off
    if base not in CLUB_BASES or base % 0x10000:
        raise LayoutPatchError('%s: composer format literal %#x does not match the string at %#x (base %#x)' % (name, lit, fmt_off, base))
    if _word_refs(bytes(d), lit) != 1:
        raise LayoutPatchError('%s: composer format is referenced %d times (expected 1)' % (name, _word_refs(bytes(d), lit)))
    sites = [(a, CLUB_SIG_A, CLUB_SIG_A_NEW), (b, CLUB_B_OLD, CLUB_B_NEW), (fmt_off, CLUB_FMT_OLD, CLUB_FMT_NEW)]
    inl = _unique(bytes(d), CLUB_INLINE_CTX)
    if inl is not None:                                  # HOMETOWN only: the inline copy of the candidate builder
        if _word_refs(bytes(d), base + inl) != 1:
            raise LayoutPatchError('%s: inline format referenced %d times (expected 1)' % (name, _word_refs(bytes(d), base + inl)))
        sites.append((inl, CLUB_FMT_OLD, CLUB_FMT_NEW))
    if guard:
        c = a + COMP_DELTA
        old = bytes(d[c:c + COMP_LEN])
        if hashlib.sha256(old).hexdigest() != COMP_SHA256:
            raise LayoutPatchError('%s: the club-name composer at %#x is not the known one (sha256 differs)' % (name, c))
        for slot, what in ((COMP_L_POOLTBL, 'club word table'), (COMP_L_TOWNTBL, 'town table'), (COMP_L_PREFTBL, 'prefecture table')):
            v = struct.unpack_from('<I', d, c + slot)[0]
            if not base <= v < base + len(d):
                raise LayoutPatchError('%s: composer literal for the %s (%#x) is outside the overlay' % (name, what, v))
        popup_word = None
        if inl is not None:                              # HOMETOWN: the candidate popup's four sprintf calls go through the join entry
            lit_fmt = _word_offs(bytes(d), base + inl)
            if len(lit_fmt) != 1:
                raise LayoutPatchError('%s: popup format literal not found exactly once' % name)
            lit_fmt = lit_fmt[0]
            lit_wd, lit_spf = lit_fmt - 4, lit_fmt + 4
            spf = struct.unpack_from('<I', d, lit_spf)[0]
            if spf != struct.unpack_from('<I', d, c + COMP_L_SPRINTF)[0]:
                raise LayoutPatchError('%s: popup sprintf literal %#x is not the library sprintf' % (name, spf))
            for lit, what in ((lit_wd, 'word'), (lit_fmt, 'format'), (lit_spf, 'sprintf')):
                if _literal_loads(bytes(d), lit) != 4:
                    raise LayoutPatchError('%s: the popup %s literal is not loaded exactly 4 times' % (name, what))
            if _word_refs(bytes(d), base + c) or _calls_to(bytes(d), c):
                raise LayoutPatchError('%s: the composer copy is referenced (not dead code), refusing to replace it by the popup join' % name)
            popup_word = struct.unpack_from('<I', d, lit_wd)[0]
            sites.append((lit_spf, spf.to_bytes(4, 'little'), (base + c).to_bytes(4, 'little')))
        new = composer_bytes(c, dot, room, popup_word)
        assert len(new) <= COMP_LEN, len(new)
        new += bytes([0x09, 0x00]) * ((COMP_LEN - len(new)) // 2)    # nop padding up to the old literal pool
        sites.append((c, old, new))
    for off, old, new in sites:
        assert len(old) == len(new) and bytes(d[off:off + len(old)]) == old, (name, hex(off))
        d[off:off + len(new)] = new
    return bytes(d)


def make_patches(read_extracted, current=None, guard=True, dot=True, room=CLUB_ROOM):
    """-> {iso path: new bytes}.  `current` = {iso path: bytes} of earlier stages (text repacking).
    HOMETOWN.BIN: list-label spacer + club-name composition; the other 19 CLUB_OVERLAYS: club-name composition only.
    guard / dot: see patch_clubnames (bounded composer, default on)."""
    cur = (current or {})
    out = {}
    for n in CLUB_OVERLAYS:
        iso = '/FLOW_PRG/%s.BIN' % n
        base = cur.get(iso)
        if base is None:
            base = read_extracted(iso.lstrip('/'))
        if iso == HOMETOWN_ISO:
            base = patch_hometown(base)
        out[iso] = patch_clubnames(base, n, guard=guard, dot=dot, room=room)
    return out


# ------------------------------------------------------------------ short-name tags (docs/s7t-proposals.md section 2)
# The routine short_name(dest r4, name r5) of 11 overlays builds the small name tags (Practice > Player Placement, Event, Office, ...):
# the ORIGINAL copies at most 4 BYTES of the first blank-separated word into an 8-byte buffer and sprintf()s it with " %s " (1 or 2 bytes) or
# "%s".  For Japanese ("surname given", two kanji = 4 bytes) that is the surname; for the English "Given Family" it is `Taiy`, `Keij`, `H.`.
# The REPLACEMENT (same entry, same size 152 bytes = code + three literal pool words, same stack protocol, no callee-saved register
# touched) takes the LAST blank-separated word (the family name) up to TAG_LIMIT bytes (the buffer holds 8, so 7 letters at most).
# The code is a function of the three pool words only (format " %s ", libc sprintf, format "%s"), which are read from the overlay.
TAG_ISO_DIR = '/FLOW_PRG/'
TAG_SITES = {'CAP_SLCT': 71864, 'ENDOPT': 189784, 'EVENT': 309780, 'GAME': 455720, 'G_RESULT': 50204, 'NEWCON': 133612, 'NEWS': 138572, 'OFFICE': 164788, 'TOWN': 159024, 'TRAINING': 86808, 'YOUTH': 81940}       # overlay: file offset of the routine (entry)
TAG_LEN = 0x98
TAG_CODE_LEN = 0x8c
TAG_SPRINTF = 0x8c014d80
TAG_LIMIT = 7
# the lineup name tags of GAME (in-match lineup) and TRAINING (Practice > Player Placement) are drawn 5 letters wide before the next sprite starts
# (docs/layout-issues.md s15, study 9a M3: 'Kasam t' / 'Hisan' / 'Kanaw' were clipped at 6-7 letters); the other nine overlays keep 7
TAG_LIMIT_BY_OVERLAY = {'GAME': 5, 'TRAINING': 5}
TAG_ORIG_CODE = bytes.fromhex('224fec7f441f531f00e3321f0aa00900f363f2523c32f351f2501c000022f2520172221f04e3f25133310a89f352f2502c000e6020880489f2502c011e611821e68bf363f2523c3200e11022f25001880389028801890aa00900362f0bd2262ff6540bd20b420900087f0aa00900362f08d2262ff65406d20b420900087f00a00900147f264f0b0009000000')
TAG_SRC = """
        .word 0x4f22             ; sts.l pr,@-r15
        add #-8,r15              ; buf = r15 .. r15+7
        mov r5,r6                ; q = start of the last word
        mov r5,r1                ; p
scan:   mov.b @r1+,r0
        tst r0,r0
        bt copy
        cmp/eq #32,r0
        bf scan
        mov.b @r1,r2             ; blank: the next byte starts a word unless it is the NUL (trailing blank)
        tst r2,r2
        bt scan
        bra scan
        mov r1,r6
copy:   mov r15,r3               ; d = buf
        mov r15,r7
        add #LIMIT,r7            ; end = buf + LIMIT
cl:     mov.b @r6+,r0
        tst r0,r0
        bt done
        cmp/eq #32,r0
        bt done
        .word 0x2300             ; mov.b r0,@r3
        add #1,r3
        cmp/hs r7,r3
        bf cl
done:   mov #0,r0
        .word 0x2300             ; mov.b r0,@r3
        sub r15,r3               ; n
        mov r3,r0
        cmp/eq #1,r0
        bt fmt1
        cmp/eq #2,r0
        bt fmt1
        mov.l @(FMT2P,pc),r2
        bra call
        nop
fmt1:   mov.l @(FMT1P,pc),r2
call:   mov r15,r3
        mov.l r3,@-r15           ; stack args: [sp] = fmt, [sp+4] = buf (as the original)
        mov.l r2,@-r15
        mov.l @(SPFP,pc),r1
        jsr @r1
        nop
        add #8,r15               ; the two pushed words
        add #8,r15               ; buf
        .word 0x4f26             ; lds.l @r15+,pr
        rts
        nop
        .align 4
FMT1P:  .long FMT1
SPFP:   .long SPRINTF
FMT2P:  .long FMT2
"""


def tag_routine(base_entry, fmt1, sprintf, fmt2, limit=TAG_LIMIT):
    """the 152 replacement bytes for an overlay whose routine sits at address `base_entry` with the given literal pool words"""
    import sh4asm2
    if not 1 <= limit <= 7:
        raise LayoutPatchError('tag limit %d: the local buffer holds 8 bytes (1..7 letters)' % limit)
    code, _, _ = sh4asm2.assemble(TAG_SRC.replace('LIMIT', str(limit)), base_entry, {'FMT1': fmt1, 'SPRINTF': sprintf, 'FMT2': fmt2})
    if len(code) > TAG_LEN:
        raise LayoutPatchError('short-name routine is %d bytes (room %d)' % (len(code), TAG_LEN))
    return bytes(code) + b'\x09\x00' * ((TAG_LEN - len(code)) // 2)


def tag_scan(d, name=''):
    """-> (entry offset, base, fmt1, fmt2) of the ORIGINAL routine of one overlay image.  Raises LayoutPatchError when the bytes are not exactly
    one copy of the known routine (already patched, other build) or the pool words do not point at ' %s ' / '%s' / the libc sprintf."""
    d = bytes(d)
    hits, i = [], d.find(TAG_ORIG_CODE)
    while i >= 0:
        hits.append(i)
        i = d.find(TAG_ORIG_CODE, i + 1)
    if len(hits) != 1:
        raise LayoutPatchError('%s: the short-name routine was found %d times (expected exactly 1: already patched or another image)' % (name, len(hits)))
    ent = hits[0]
    if name in TAG_SITES and TAG_SITES[name] != ent:
        raise LayoutPatchError('%s: the short-name routine is at %#x, expected %#x' % (name, ent, TAG_SITES[name]))
    if ent % 4 or ent + TAG_LEN > len(d):
        raise LayoutPatchError('%s: short-name routine at %#x is misplaced' % (name, ent))
    fmt1, spf, fmt2 = struct.unpack_from('<III', d, ent + TAG_CODE_LEN)
    if spf != TAG_SPRINTF:
        raise LayoutPatchError('%s: the routine calls %#x, not the library sprintf %#x' % (name, spf, TAG_SPRINTF))
    for base in CLUB_BASES:
        if 0 <= fmt1 - base < len(d) - 4 and d[fmt1 - base:fmt1 - base + 5] == b' %s \0\0'[:5] and 0 <= fmt2 - base < len(d) - 3                 and d[fmt2 - base:fmt2 - base + 3] == b'%s\0':
            return ent, base, fmt1, fmt2
    raise LayoutPatchError('%s: the pool words %#x / %#x do not point at the " %%s " / "%%s" formats' % (name, fmt1, fmt2))


def tag_limit_for(name, limit=None):
    """the letter limit of one overlay: TAG_LIMIT_BY_OVERLAY (GAME, TRAINING = 5), else TAG_LIMIT (7); an explicit smaller `limit` wins"""
    lim = TAG_LIMIT_BY_OVERLAY.get(name, TAG_LIMIT)
    return lim if limit is None else min(lim, limit)


def patch_tag(data, name='', limit=None):
    """one overlay image -> same size, the 152 byte routine replaced (refuses foreign or already patched bytes).  limit None = the
    per-overlay limit (tag_limit_for); an explicit integer is used as given (1..7, the test hook)"""
    if limit is None:
        limit = tag_limit_for(name)
    ent, base, fmt1, fmt2 = tag_scan(data, name)
    d = bytearray(data)
    d[ent:ent + TAG_LEN] = tag_routine(base + ent, fmt1, TAG_SPRINTF, fmt2, limit)
    return bytes(d)


def tag_patches(read_extracted, current=None, limit=None):
    """-> {iso path: new bytes} for the 11 overlays, composed on the CURRENT bytes (earlier stages are kept).  Every overlay gets its own
    limit (tag_limit_for: GAME and TRAINING 5, the other nine 7); `limit` (default None) can only LOWER them"""
    cur = current or {}
    out = {}
    for n in sorted(TAG_SITES):
        iso = TAG_ISO_DIR + n + '.BIN'
        d = cur.get(iso)
        if d is None:
            d = read_extracted(iso.lstrip('/'))
        out[iso] = patch_tag(d, n, tag_limit_for(n, limit))
    return out


# ------------------------------------------------------------------ scout panel 'Age' row (docs/layout-issues.md section 11)
SCOUT_ISO_DIR = '/FLOW_PRG/'
SCOUT_SITES = {'SCDRF': (0x7684, 0x779a), 'SEARCH': (0x8934, 0x8a4a)}      # overlay: file offsets of the `add #71,r4` delay slots (the SEARCH copy is 0x12b0 higher)
SCOUT_OLD = 0x7447             # add #71,r4
SCOUT_NEW = 0x7445             # add #69,r4
SCOUT_PUSH = bytes.fromhex('362f262f')   # mov.l r3,@-r15 ; mov.l r2,@-r15   (the stack args of the sprintf call, just before the jsr)
SCOUT_TEXT = {'FLOW_PRG/SCDRF.BIN#32c9c': '%4d/%d yrs  ', 'FLOW_PRG/SEARCH.BIN#32a04': '%4d/%d yrs  '}   # DB records of the row-2 format (12 characters)


def scout_scan(d, name=''):
    """-> [file offsets] of the two `add #71,r4` of ONE overlay image: the delay slot of the jsr @rX that runs sprintf(b + 71, 'Age %2d', age)
    in the scout panel builders (the 12-wide row buffer, see docs/layout-issues.md section 11).  The signature is
    `mov.l r3,@-r15 ; mov.l r2,@-r15 ; jsr @rX (0x4X0B) ; add #71,r4`.  Raises LayoutPatchError unless exactly 2 sites are found, at the known
    offsets (an already patched image has none, another build has other offsets)."""
    d = bytes(d)
    sites = []
    for o in range(6, len(d) - 1, 2):
        if struct.unpack_from('<H', d, o)[0] == SCOUT_OLD and (struct.unpack_from('<H', d, o - 2)[0] & 0xF0FF) == 0x400B \
                and d[o - 6:o - 2] == SCOUT_PUSH:
            sites.append(o)
    if len(sites) != 2:
        raise LayoutPatchError('%s: the scout Age sprintf was found %d times (expected exactly 2: already patched or another image)' % (name, len(sites)))
    if name in SCOUT_SITES and tuple(sites) != SCOUT_SITES[name]:
        raise LayoutPatchError('%s: the scout Age sprintf sites are %s, expected %s' % (name, [hex(s) for s in sites], [hex(s) for s in SCOUT_SITES[name]]))
    return sites


def patch_scout(data, name=''):
    """one overlay image -> same size, the two `add #71,r4` changed to `add #69,r4` (the Age row starts 2 bytes earlier, so that 'Age 25'
    + NUL ends at the newline store b[75] exactly like the 4-byte Japanese '25歳'); refuses foreign or already patched bytes"""
    d = bytearray(data)
    for o in scout_scan(data, name):
        struct.pack_into('<H', d, o, SCOUT_NEW)
    return bytes(d)


def scout_patches(read_extracted, current=None):
    """-> {iso path: new bytes} for SCDRF and SEARCH, composed on the CURRENT bytes (text repacking done before is kept)"""
    cur = current or {}
    out = {}
    for n in sorted(SCOUT_SITES):
        iso = SCOUT_ISO_DIR + n + '.BIN'
        d = cur.get(iso)
        if d is None:
            d = read_extracted(iso.lstrip('/'))
        out[iso] = patch_scout(d, n)
    return out


# ------------------------------------------------------------------ Event income table crowd line (docs/layout-issues.md section 13)
# FLOW_PRG/G_INCOME.BIN (base 0x8c4d0000), the crowd-row function at 0x2d0 builds `<hi>万<lo>人` in a 32 byte stack buffer: itoa digits, then the unit
# strings copied by the libc strncpy with HARD-CODED counts of 2 bytes (the Japanese 万 and 人 are 2 bytes each): 'man' became 'ma' and 'ppl'
# 'pp' ('1ma827pp'), 7 people read '7pp', 0 people a lone '0'.  The patch (study 9d, proven in tools/sh4sim.py on the real bytes, tools/test_crowdfix.py):
#   patch A  new string 'man ' + NUL at 0x264a0 (zero padding of the overlay), the unit pool word 0x3d8 -> it, `mov #2,r6` -> `mov #4,r6` (0x326),
#            `add #2,r14` -> `add #4,r14` (0x32e); the 'ppl' copy 2 -> 3 bytes (0x354 `mov #3,r6`, 0x35c `add #3,r14`)   -> '1man 827ppl'
#   patch B  new string '0ppl' + NUL at 0x264a8, the zero-people pool word 0x3e4 -> it, the 3 byte copy -> 4 (0x360, 0x366)  -> '0ppl'
# Every number ends at the same right edge (x = 504 + (8 - len) * 12 + its pixel width).  The units stay English DB records ('ppl' at 0x26494 is read
# in place), so the patch is only valid on an image whose G_INCOME text was translated (an untranslated image is refused).
CROWD_ISO = '/FLOW_PRG/G_INCOME.BIN'
CROWD_BASE = 0x8C4D0000
CROWD_CODE = 0x2D0
CROWD_SIG = bytes.fromhex(           # the 232 code bytes 0x2d0..0x3b8 (identical in the Japanese original, hsk_full1 and prop10e)
    'e62fd62fc62fb62f224fd87ff36bf36137d3087135d2436c4aff087b0b4320e06290b36e34d333dde11f0b43c3610820'
    '168d03650ae33335068931d100e62fd70b41e36405a009002ed100e620e70b41e3642dd5036402e64c3e0b4de364027e'
    '2ad341900b43c3610820088d036525d300e620e70b43e364036402a04c3e154c058b23d502e60b4de36405a0027e21d5'
    '03e60b4de364037e1fd30b43b62f036448241a8d047ff15308e21cc7383e08f2e832236100421c3208425a424ae02df3'
    '20f33df35a0225044ce0f8f33df35a03350413c708f350e037f4287f264ff66bf66cf66d0b00f66e')
CROWD_LEN = len(CROWD_SIG)           # 232
# (file offset, old halfword, new halfword) of the code edits, patch A then patch B
CROWD_EDITS = ((0x326, 0xE602, 0xE604), (0x32E, 0x7E02, 0x7E04), (0x354, 0xE602, 0xE603), (0x35C, 0x7E02, 0x7E03),
               (0x360, 0xE603, 0xE604), (0x366, 0x7E03, 0x7E04))
CROWD_POOL = {0x3D8: 0x264A0, 0x3E4: 0x264A8}                       # pool word offset -> file offset of the new string
CROWD_NEW = {0x264A0: b'man \0', 0x264A8: b'0ppl\0'}                # new strings (zero padding between ' ' at 0x2649c and '@R/' at 0x264bc)
CROWD_ZERO = (0x264A0, 0x264BC)                                     # must be all zero in the image
CROWD_UNITS = {0x3E0: b'ppl\0', 0x3E4: b'0\0'}                      # English unit records read in place: pool word offset -> expected string


class CrowdUntranslated(LayoutPatchError):
    """the G_INCOME unit strings are still Japanese (nothing to fix: the 2 byte copy counts are right for 万 and 人)"""


def _crowd_check(d, name):
    d = bytes(d)
    if len(d) < CROWD_ZERO[1] + 4:
        raise LayoutPatchError('%s: image too short for the crowd patch' % name)
    hits, i = [], d.find(CROWD_SIG)
    while i >= 0:
        hits.append(i)
        i = d.find(CROWD_SIG, i + 1)
    if len(hits) != 1 or hits[0] != CROWD_CODE:
        raise LayoutPatchError('%s: the crowd-row function was found %d times at %s (expected once at %#x: already patched or another image)'
                               % (name, len(hits), [hex(h) for h in hits], CROWD_CODE))
    for off, old, _ in CROWD_EDITS:
        if struct.unpack_from('<H', d, off)[0] != old:
            raise LayoutPatchError('%s: halfword at %#x is not %#06x' % (name, off, old))
    if any(d[CROWD_ZERO[0]:CROWD_ZERO[1]]):
        raise LayoutPatchError('%s: the zero area %#x..%#x is not empty' % (name, CROWD_ZERO[0], CROWD_ZERO[1]))
    for off, want in CROWD_UNITS.items():
        p = struct.unpack_from('<I', d, off)[0] - CROWD_BASE
        if not 0 <= p < len(d) - 8 or d[p:p + len(want)] != want:
            raise CrowdUntranslated('%s: the unit string behind the pool word %#x is not %r (the crowd patch needs the English text)' % (name, off, want))
    p = struct.unpack_from('<I', d, 0x3D8)[0] - CROWD_BASE
    if not 0 <= p < len(d) - 8:
        raise LayoutPatchError('%s: the 10,000 unit pointer %#x is outside the image' % (name, p))


def patch_crowd(data, name='G_INCOME'):
    """the G_INCOME.BIN image -> same size: crowd line '1man 827ppl' / '5000ppl' / '0ppl' (patch A + B above).  Raises LayoutPatchError on a
    foreign or already patched image, a non-empty zero area or an untranslated unit text."""
    _crowd_check(data, name)
    d = bytearray(data)
    for off, _, new in CROWD_EDITS:
        struct.pack_into('<H', d, off, new)
    for off, s in CROWD_NEW.items():
        d[off:off + len(s)] = s
    for pool, off in CROWD_POOL.items():
        struct.pack_into('<I', d, pool, CROWD_BASE + off)
    return bytes(d)


def crowd_patches(read_extracted, current=None):
    """-> {iso path: new bytes} for G_INCOME.BIN, composed on the CURRENT bytes (the text repacking done before is kept)"""
    d = (current or {}).get(CROWD_ISO)
    if d is None:
        d = read_extracted(CROWD_ISO.lstrip('/'))
    return {CROWD_ISO: patch_crowd(d, 'G_INCOME')}


# ------------------------------------------------------------------ commentary subtitle speed (docs/layout-issues.md section 14)
# FLOW_PRG/GAME.BIN, the commentary box update function 0x8c31eee8 (file 0x4eee8) reveals ONE character per two states: state 2 reads it (only when
# int(timeline) is odd: `sts fpul,r3 ; tst r8,r3 ; bf`), state 3 draws it and returns to the main loop, so the original costs about 2.23 ticks per character.
# The English commentary is about 1.9x longer than the Japanese one; 77% of the 17,603 lines were still typing when their clip ended (study 9f).
#   patch (i)  site 1 at +4 (file 0x4f248): `sts fpul,r3 ; tst r8,r3` (5a 03 88 23) -> `sts fpul,r0 ; tst #MASK,r0` (5a 00 MASK c8): the character is read on
#              7 of 8 (mask 7) or 3 of 4 (mask 3) integer timeline values; r0 / r3 are dead after the gate.   [speed 2.2: not used, see below]
#   patch (ii) site 2 at +10 (file 0x4f2c6): `bra 0x8c31f392` (return to the main loop after reading) -> `bra 0x8c31eefa` (18 ae): back to the dispatch right after
#              the prologue (`mov.w #0xd8,r14` ...), which reloads r8..r14 and re-dispatches on the state just stored (3), so the character is DRAWN IN THE SAME TICK
#              by the normal state 3 code (flag test and all).
#              The first version of this patch (`bra 0x8c31f2ec`, bytes 11 a0, the state 3 draw call itself) CRASHED THE EMULATOR on the first message of
#              every box (prop10g, the tactics explainer): state 1 (slot pick) reloads r13 = 0x8c159000 (a table of FUNCTION POINTERS of the debug/sound
#              library) and then FALLS THROUGH into state 2 in the same tick; the draw call of state 3 is `jsr @r13`, and r13 is only reloaded to 0x8c3202b0 by the
#              prologue of the NEXT tick.  Entering the draw directly therefore called 0x8c159000 as code (docs/layout-issues.md s14, tools/test_bcastspeed.py).
#   speed 2.2: no gate at all: site 1 at +10 (file 0x4f24e) `bra return` (a0 a0) -> `nop` (09 00), plus (ii)           -> exactly 1 character per tick
# Speeds (relative to the original, simulated with the real bytes, tools/test_bcastspeed.py): 1.7 = 1.67x (mask 3), 1.9 = 1.94x (mask 7, default), 2.2 = 2.23x.
BCAST_ISO = '/FLOW_PRG/GAME.BIN'
BCAST_SPEEDS = ('off', '1.7', '1.9', '2.2')
BCAST_SIG1 = bytes.fromhex('a6f33df35a038823018ba0a00900')           # unique in extracted/, file 0x4f244; patch at +4 (gate) or +10 (the return bra)
BCAST_SIG2 = bytes.fromhex('04e005e067a0e18003e064a0e180')           # unique in extracted/, file 0x4f2bc; patch at +10 (the bra)
BCAST_SITE1, BCAST_SITE2 = 0x4F244, 0x4F2BC
BCAST_GATE = {'1.7': bytes.fromhex('5a0003c8'), '1.9': bytes.fromhex('5a0007c8')}
BCAST_REDISPATCH = bytes.fromhex('18ae')     # bra 0x8c31eefa at 0x8c31f2c6: (0x8c31eefa - 0x8c31f2ca) / 2 = -0x1e8 -> disp12 0xe18 -> 0xae18


def _bcast_find(d, sig, expect, name, what):
    hits, i = [], d.find(sig)
    while i >= 0:
        hits.append(i)
        i = d.find(sig, i + 1)
    if hits != [expect]:
        raise LayoutPatchError('%s: the commentary %s signature was found %d times at %s (expected once at %#x: already patched or another image)'
                               % (name, what, len(hits), [hex(h) for h in hits], expect))
    return hits[0]


def patch_bcast_speed(data, speed='1.9', name='GAME'):
    """the GAME.BIN image -> same size, the commentary reveal speed of `speed` ('off' returns the image unchanged, without any check)"""
    if speed not in BCAST_SPEEDS:
        raise LayoutPatchError('unknown commentary speed %r (one of %s)' % (speed, ', '.join(BCAST_SPEEDS)))
    if speed == 'off':
        return bytes(data)
    d = bytearray(data)
    s1 = _bcast_find(bytes(data), BCAST_SIG1, BCAST_SITE1, name, 'gate')
    s2 = _bcast_find(bytes(data), BCAST_SIG2, BCAST_SITE2, name, 'draw-return')
    if speed == '2.2':
        d[s1 + 10:s1 + 12] = b'\x09\x00'
    else:
        d[s1 + 4:s1 + 8] = BCAST_GATE[speed]
    d[s2 + 10:s2 + 12] = BCAST_REDISPATCH
    return bytes(d)


def bcast_patches(read_extracted, current=None, speed='1.9'):
    """-> {iso path: new bytes} for GAME.BIN ({} for speed 'off'), composed on the CURRENT bytes"""
    if speed == 'off':
        return {}
    d = (current or {}).get(BCAST_ISO)
    if d is None:
        d = read_extracted(BCAST_ISO.lstrip('/'))
    return {BCAST_ISO: patch_bcast_speed(d, speed, 'GAME')}


# ------------------------------------------------------------------ in-match OPTIONS panel: selected-option highlight windows (docs/layout-issues.md section 18)
# FLOW_PRG/GAME.BIN (and the identical copy in FLOW_PRG/ENDING.BIN): the OPTIONS panel (row builder 0x8c2ff29e, update function 0x8c3010e4) draws every row's
# label and value with the bitmap text writer 0x8c3341d0 into ONE texture, at HALF scale: a character cell is 12 px on screen = 6 texture pixels, the value text
# starts at x = 192 px = texture u 96 (the string table `tbl@117414`: 7 rows of (label, value), the five option rows are pairs 2..6 of it).  The whole value text
# is drawn dim.  The CURRENT option is then brightened by a *sprite* that re-draws a fixed window of the same texture: sprite records 0x82..0x8c of the 20 byte
# record table (`<10h`: w, h, x, y, u0, v0, u1, v1, type, 0; w = 2 * (u1 - u0); x = 182 - 2 * u0, the sprite engine mirrors x), picked by the update function:
#     ids 0x82 / 0x83  Commentary    ON / OFF          0x84 / 0x85  Subtitles   ON / OFF          0x86 / 0x87  Player Names  ON / OFF
#     ids 0x88 / 0x89  Name Format   A / B             0x8a / 0x8b / 0x8c  Camera Type   Near / Mid / Far
# The windows are CELL RANGES fitted to the Japanese full-width value strings: `  ＯＮ・ＯＦＦ` -> ON = cells 2..5, OFF = cells 8..13; `        Ａ・Ｂ` -> 8..9 / 12..13;
# `    近・中・遠` -> the three 2-cell windows 4..5 / 8..9 / 12..13 (the original records are reproduced exactly from the Japanese strings, tools/test_optionsfix.py).
# With the English text `  ON/OFF` the ON window lit `ON/O` and the OFF window nothing; `  Near/Mid/Far` lit only `ar` (the Far window 12..13), Near and Mid had no word
# under their windows (playtest prop10h screenshot).  A pure text change cannot cure the camera row (Near is 4 characters, its window 2 cells).
# The fix is DATA only (no code): the 11 sprite records get u0 / u1 / w / x recomputed from the cells of the option words in the CURRENT value strings (read
# through the pointer table, so a repacked or edited string is followed): window = the characters of that option word, whole cells.  An image whose value strings are
# still Japanese is left alone (the original windows are right for it).  Located by the 220 byte record block (unique per overlay); refuses foreign / patched bytes.
OPT_BASE = 0x8C2D0000
OPT_ISO_DIR = '/FLOW_PRG/'
OPT_SITES = {'GAME': (0x117414, 0x117E64), 'ENDING': (0x2BF80, 0x68F20)}      # overlay: (file offset of the 10 word pointer table, of sprite record 0x82)
OPT_CELL = 12            # px per character cell on screen
OPT_HALF = 6             # texture pixels per cell (half scale)
OPT_U0 = 96              # texture u of the value text origin (x = 0xc0 px)
OPT_VALUE_CELLS = 14     # the value area is 14 cells wide (168 px): the Japanese strings are 14 bytes, longer text is cut
OPT_ROWS = ((0x82, 0x83), (0x84, 0x85), (0x86, 0x87), (0x88, 0x89), (0x8A, 0x8B, 0x8C))   # sprite ids per option row = pointer table pairs 0..4 (the table's own pairs)
OPT_REC = 20
OPT_ORIG = bytes.fromhex(
    '30001800deff49006c002c0084003800000000004800180096ff490090002c00b40038000000000030001800deff1d006c00420084004e00000000004800180096ff1d00'
    '90004200b4004e000000000030001800defff1ff6c00580084006400000000004800180096fff1ff90005800b4006400000000001800180096ffc5ff90006e009c007a00'
    '000000001800180066ffc5ffa8006e00b4007a000000000018001800c6ff99ff7800840084009000000000001800180096ff99ff900084009c009000000000001800'
    '180066ff99ffa8008400b400900000000000')


def _opt_find_block(d, name, want):
    hits, i = [], d.find(OPT_ORIG[:OPT_REC * 3])
    while i >= 0:
        hits.append(i)
        i = d.find(OPT_ORIG[:OPT_REC * 3], i + 1)
    if hits != [want]:
        raise LayoutPatchError('%s: the OPTIONS highlight sprite block was found %d times at %s (expected once at %#x: already patched or another image)' % (name, len(hits), [hex(h) for h in hits], want))
    if d[want:want + len(OPT_ORIG)] != OPT_ORIG:
        raise LayoutPatchError('%s: the OPTIONS highlight sprite records at %#x are not the original ones (already patched or another image)' % (name, want))


def opt_cells(value, parts):
    """the cell ranges [(first, end), ...] of the option words of one value string (bytes, one byte = one 12 px cell).
    SJIS (full-width) text -> None (the original windows are right for it); ASCII text: `parts` words separated by one '/', each a run of non-blank characters."""
    if any(c >= 0x80 for c in value):
        return None
    out, i, n = [], 0, len(value)
    for k in range(parts):
        while i < n and value[i] == 0x20:
            i += 1
        j = i
        while j < n and value[j] not in b' /':
            j += 1
        if j == i:
            raise LayoutPatchError('OPTIONS value %r: word %d of %d not found' % (value, k + 1, parts))
        out.append((i, j))
        i = j
        if k + 1 < parts:
            if not (i < n and value[i] == 0x2F):
                raise LayoutPatchError("OPTIONS value %r: no '/' after word %d" % (value, k + 1))
            i += 1
    if out[-1][1] > OPT_VALUE_CELLS:
        raise LayoutPatchError('OPTIONS value %r: the last word ends in cell %d, the value area is %d cells wide' % (value, out[-1][1], OPT_VALUE_CELLS))
    return out


def opt_window(rec, cells):
    """sprite record bytes (20) -> the same record with the window of cells (first, end)"""
    w, h, x, y, u0, v0, u1, v1, typ, z = struct.unpack('<10h', rec)
    first, end = cells
    u0 = OPT_U0 + OPT_HALF * first
    u1 = OPT_U0 + OPT_HALF * end
    return struct.pack('<10h', OPT_CELL * (end - first), h, 182 - 2 * u0, y, u0, v0, u1, v1, typ, z)


def _opt_value(d, tbl, pair):
    """the value string (bytes without NUL) of option row `pair` (0..4) read through the pointer table at file offset tbl"""
    p = struct.unpack_from('<I', d, tbl + 4 * (2 * pair + 1))[0] - OPT_BASE
    if not 0 <= p < len(d) - 20:
        raise LayoutPatchError('OPTIONS value pointer %#x is outside the image' % p)
    e = d.index(b'\0', p)
    return bytes(d[p:e])


def options_windows(d, name='GAME'):
    """-> {sprite id: (first cell, end cell)} for the CURRENT value strings of the overlay image d, or None when they are Japanese"""
    tbl = OPT_SITES[name][0]
    out = {}
    for pair, ids in enumerate(OPT_ROWS):
        c = opt_cells(_opt_value(d, tbl, pair), len(ids))
        if c is None:
            return None
        out.update(zip(ids, c))
    return out


def patch_options(data, name='GAME'):
    """the GAME.BIN / ENDING.BIN image -> same size: the 11 highlight windows of the OPTIONS panel follow the English option words (cell ranges above).
    A Japanese image is returned unchanged; foreign / already patched records raise LayoutPatchError."""
    d = bytearray(data)
    tbl, rec0 = OPT_SITES[name]
    _opt_find_block(bytes(d), name, rec0)
    win = options_windows(bytes(d), name)
    if win is None:
        return bytes(d)
    for sid, cells in win.items():
        off = rec0 + (sid - 0x82) * OPT_REC
        d[off:off + OPT_REC] = opt_window(bytes(d[off:off + OPT_REC]), cells)
    return bytes(d)


def options_patches(read_extracted, current=None):
    """-> {iso path: new bytes} for GAME.BIN and ENDING.BIN (only the ones that change), composed on the CURRENT bytes"""
    out = {}
    for name in sorted(OPT_SITES):
        iso = OPT_ISO_DIR + name + '.BIN'
        d = (current or {}).get(iso)
        if d is None:
            d = read_extracted(iso.lstrip('/'))
        new = patch_options(d, name)
        if new != bytes(d):
            out[iso] = new
    return out


# ------------------------------------------------------------------ commentary subtitle: proportional cell advance (docs/layout-issues.md section 19, build flag --cell-prop)
# FLOW_PRG/GAME.BIN, line engine 0x8c3202b0 (base 0x8c2d0000, file offset = address - base): the commentary (BCAST) subtitle is drawn one character per call into an
# 82 byte line record (byte 0 = glyph count, byte 1 = unit count for the wrap test, then 40 pairs `present flag, advance byte`).  The display loop 0x8c31fdc0 takes the advance
# byte of every cell as the sprite width, the UV width (x 8) and the pen step, so a HALF-WIDTH glyph is always 12 px: `mov #12,r0 ; mov.b r0,@(1,r2)` at 0x8c32049e / 0x8c3204a0 and
# a blank `mov #12,r0` at 0x8c3204f2 (flag 0: nothing drawn, 12 px pen step).  The proportional glyphs are left aligned, so 'i', 'l', 't', 'f' ... are followed by 5-7 px of paper
# ('Fi r st hal f').  The advance table at 0x8c299900 is never read by this engine (the linear writer / --lin-center, the tsString hook and --align-fix are other paths).
# Fix (two blocks of the engine, same size, signature checked, plus one zero literal):
#   half-width block 0x8c32048c..0x8c3204a1 (22 B, file 0x5048c): the `mov #12,r0` is replaced by `jsr` to the resident routine `cell_adv` of 1ST_READ.BIN (fontpatch.CELL_SRC, claim
#       `font.cell`: table[byte] clamped to 12, 0 -> 12); its cave address sits in the free zero literal 0x8c32053c (file 0x5053c; the code reads it with `mov.l @(40,pc),r3`).  The
#       block is a register-neutral replacement: r2 (record pointer) survives the call, r0/r1/r3/r4 are dead after the store, PR is saved by the engine's own prologue.
#   blank block 0x8c3204e0..0x8c3204fd (30 B, file 0x504e0): writes the table's blank advance S (1..12, derived from the BUILT table by the caller) instead of 12 and SKIPS a blank at
#       column 0: the wrap breaks the line on a space (units >= 37 and next byte blank) and then draws that space as the first cell of the new line ('...Cut out' / ' easily here.').
#       Skipping jumps to the common tail 0x8c3204fe (column + 1, glyph count + 1); the cell keeps flag 0 and advance 0 (a new line record is zero filled by 0x8c3201fe), the unit
#       count is not touched, so the wrap test, the display loop (pen += 0) and every later column are unchanged.
# Full-width glyphs (24 px), the wrap logic and the display loop are not touched.  Refuses foreign and already patched images.
CELL_ISO = '/FLOW_PRG/GAME.BIN'
CELL_BASE = 0x8C2D0000
CELL_HALF = 0x5048C                    # half-width block (22 bytes)
CELL_HALF_PRE = bytes.fromhex('2dd38020d1622d6238221289')            # mov.l 0x8c320538,r3 ; mov.b r8,@r0 ; mov.w @r13,r2 ; extu.w r2,r2 ; tst r3,r2 ; bt 0x8c3204b2
CELL_HALF_OLD = bytes.fromhex('e36009000c70bc300362e285027200400c320ce02180')
CELL_HALF_POST = bytes.fromhex('e3620c72bc3221840170218026a00900')   # mov r14,r2 ; add #12,r2 ; add r11,r2 ; units + 1 ; bra 0x8c3204fe ; nop
CELL_SPACE = 0x504E0                   # blank block (30 bytes)
CELL_SPACE_OLD = bytes.fromhex('e3630c73bc333362e363027200440c732c340ce0bc334180318401703180')
CELL_SPACE_POST = bytes.fromhex('e3630c73bc33e285')                  # the common tail 0x8c3204fe: mov r14,r3 ; add #12,r3 ; add r11,r3 ; mov.w @(4,r14),r0
CELL_SPACE_TAIL = 0x8C3204FE           # the common tail (column + 1)
CELL_LIT = 0x5053C                     # free zero literal (4 bytes) between the 0x8000 mask (0x8c320538) and the jump table (0x8c320540)
CELL_LIT_ADDR = CELL_BASE + CELL_LIT
CELL_MOVL_AT = CELL_BASE + CELL_HALF + 0xE                           # the `mov.l @(disp,pc),r3` word (0x8c32049a)
CELL_RANGE = (0x8C010000, 0x8C2D0000)  # the cave must lie in the resident image below the overlay


def _cell_asm(origin, src):
    import sh4asm2
    return b''.join(x[1] for x in sh4asm2.Asm(origin, {}).parse(src).assemble())


def cell_half_bytes():
    """the 22 byte replacement of the half-width block (see the section comment): ... shll r0 ; add r0,r2 ; add #2,r2 ; mov.l @(40,pc),r3 ; jsr @r3 ; mov.w @r13,r4 ; mov.b r0,@(1,r2)"""
    disp = (CELL_LIT_ADDR - ((CELL_MOVL_AT + 4) & ~3)) // 4
    if not 0 <= disp < 256 or (CELL_LIT_ADDR - ((CELL_MOVL_AT + 4) & ~3)) % 4:
        raise LayoutPatchError('the cell-prop literal %#x is out of reach of the mov.l at %#x' % (CELL_LIT_ADDR, CELL_MOVL_AT))
    src = """
        mov r14,r2
        add #12,r2
        add r11,r2
        .word 0x85e2
        shll r0
        add r0,r2
        add #2,r2
        .word 0x%04x
        jsr @r3
        .word 0x64d1
        .word 0x8021
""" % (0xD300 | disp)
    out = _cell_asm(CELL_BASE + CELL_HALF, src)
    assert len(out) == len(CELL_HALF_OLD)
    return out


def cell_space_bytes(space_adv):
    """the 30 byte replacement of the blank block: skip at column 0, else the blank advance `space_adv` (1..12) into the cell and unit count + 1"""
    if not 1 <= space_adv <= 12:
        raise LayoutPatchError('the cell-prop blank advance must be 1..12, got %r' % (space_adv,))
    src = """
        tst r4,r4
        bt 0x%x
        mov r14,r3
        add #12,r3
        add r11,r3
        mov r3,r2
        add #2,r2
        shll r4
        add r2,r4
        mov #%d,r0
        .word 0x8041
        .word 0x8431
        add #1,r0
        .word 0x8031
        nop
""" % (CELL_SPACE_TAIL, space_adv)
    out = _cell_asm(CELL_BASE + CELL_SPACE, src)
    assert len(out) == len(CELL_SPACE_OLD)
    return out


def _cell_find(d, sig, expect, name, what):
    hits, i = [], d.find(sig)
    while i >= 0:
        hits.append(i)
        i = d.find(sig, i + 1)
    if hits != [expect]:
        raise LayoutPatchError('%s: the commentary %s was found %d times at %s (expected once at %#x: already patched or another image)'
                               % (name, what, len(hits), [hex(h) for h in hits], expect))


def patch_cell_prop(data, cave_addr, space_adv, name='GAME'):
    """the GAME.BIN image -> same size: the commentary line engine takes the glyph advance from the routine at `cave_addr` (fontpatch `font.cell`) and the blank advance
    `space_adv`, and drops a blank at column 0.  Refuses (LayoutPatchError) a foreign or already patched image, a non-zero literal and a cave address outside the resident image."""
    d = bytearray(data)
    if cave_addr % 4 or not CELL_RANGE[0] <= cave_addr < CELL_RANGE[1]:
        raise LayoutPatchError('%s: the cell-prop routine address %#x is not a 4-aligned address of the resident image' % (name, cave_addr))
    b = bytes(d)
    if b[CELL_HALF:CELL_HALF + len(CELL_HALF_OLD)] == cell_half_bytes() or b[CELL_SPACE:CELL_SPACE + len(CELL_SPACE_OLD)] == cell_space_bytes(space_adv):
        raise LayoutPatchError('%s: the commentary line engine is already patched by --cell-prop' % name)
    _cell_find(b, CELL_HALF_PRE + CELL_HALF_OLD + CELL_HALF_POST, CELL_HALF - len(CELL_HALF_PRE), name, 'half-width advance block')
    _cell_find(b, CELL_SPACE_OLD + CELL_SPACE_POST, CELL_SPACE, name, 'blank block')
    if b[CELL_LIT:CELL_LIT + 4] != bytes(4):
        raise LayoutPatchError('%s: the literal slot %#x of the cell-prop routine address is not zero (used by another patch or another image)' % (name, CELL_LIT_ADDR))
    d[CELL_HALF:CELL_HALF + len(CELL_HALF_OLD)] = cell_half_bytes()
    d[CELL_SPACE:CELL_SPACE + len(CELL_SPACE_OLD)] = cell_space_bytes(space_adv)
    d[CELL_LIT:CELL_LIT + 4] = struct.pack('<I', cave_addr)
    return bytes(d)


def cell_patches(read_extracted, current=None, cave_addr=None, space_adv=12):
    """-> {iso path: new bytes} for GAME.BIN, composed on the CURRENT bytes (the cave itself is fontpatch's: `cave_addr` = fontpatch.cell_address())"""
    d = (current or {}).get(CELL_ISO)
    if d is None:
        d = read_extracted(CELL_ISO.lstrip('/'))
    return {CELL_ISO: patch_cell_prop(d, cave_addr, space_adv, 'GAME')}
