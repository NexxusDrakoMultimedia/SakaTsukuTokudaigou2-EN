"""Proportional half-width advance patch for the tsString layout function (docs/font-patch-design.md).

    python -I -X utf8 tools/re/font/fontpatch.py scan        # find the sites in every overlay, print the table
    python -I -X utf8 tools/re/font/fontpatch.py selftest    # encode, decode with capstone, EXECUTE original vs patched
    python -I -X utf8 tools/re/font/fontpatch.py manifest    # write build/font/font_patch_manifest.json + .tsv + cave.txt

What is patched (all in place, no file grows, no `_end` change):
  H1  half-width advance      16..18 bytes in the layout function of every overlay copy: replaced by a call into a
                              code cave in 1ST_READ.BIN that returns the pixel advance of the character
  H2  wrap test (optional)    the cell-based wrap decision is replaced by a pixel-based one (call into the same cave)
  H0  cave + table            CAVE (1ST_READ.BIN tail 0x8c299800) holds 104 bytes of code; the 256-byte table sits
                              next to it at TABLE (0x8c299900).  Alternatives (constants only): gap1 / FONT.BIN tail
Three code variants exist (A = 97 overlays + HELP copy, B = the 6 small COMM-family stubs, C = CSAVE3); all three are
handled by the same cave through two entry points per hook.
"""
import glob
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import sh4asm2           # noqa: E402
import sh4sim            # noqa: E402

try:
    import capstone as _cs
    _MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception:        # pragma: no cover
    _MD = None

# Placement (docs/font-patch-design.md s2).  PRIMARY: code and table side by side in the 1ST_READ.BIN "tail"
# [0x8c299400, 0x8c2b0000) after crt0's BSS end, starting at 0x8c299800 as the memory skeptic demanded
# (docs/capacity-design.md s9).  file offset = address - 0x8c010000.
CAVE = 0x8C299800            # 104 bytes of code, reserve [CAVE, CAVE+CAVE_MAX)
CAVE_MAX = 0x100
TABLE = 0x8C299900           # 256-byte advance table, reserve [TABLE, TABLE+256)  (cave literal; default all 12)
# ALTERNATIVES (same code, only the two constants change): cave in gap1, table at the end of the FONT.BIN window
ALT_CAVE_GAP1 = 0x8C13BB80
ALT_TABLE_FONT = 0x8CE01F00
FONT_BASE = 0x8CD5C000
FONT_WINDOW = 0x8CE02000 - FONT_BASE     # 679936

EXTRACTED = os.path.join(ROOT, 'extracted')

# ------------------------------------------------------------------------------------------------ the cave
CAVE_SRC = """
; ---- H1: advance of one half-width code.  in: r4 = code (low byte = character), r14 = window.  out: r0 = px.
; clobbers r0-r3 only (all caller-saved).  adv != 24 (small windows: 16 px etc.) keeps the original half-advance.
adv_A:  bra   adv_c
        mov   #62,r0                  ; delay slot: window offset of the advance byte (variants A and C)
adv_B:  mov   #54,r0                  ; variant B (COMM family): advance byte at +0x36
adv_c:  mov.b @(r0,r14),r2            ; r2 = window advance (24 for the normal text windows)
        mov   #24,r3
        cmp/eq r3,r2
        bf    adv_gen
        mov.l @(tblp,pc),r1           ; r1 = TABLE
        extu.b r4,r0
        mov.b @(r0,r1),r0             ; r0 = table[char]
        tst   r0,r0
        bf    adv_ret
        mov   #12,r0                  ; 0 = 'no entry': original 12 px
adv_ret: rts
        nop
adv_gen: mov  #0,r3                   ; original: (adv + (adv<0)) >> 1
        cmp/gt r2,r3
        addc  r3,r2
        shar  r2
        rts
        mov   r2,r0
; ---- H2: does the next character need a new line?  in: r4 = pen x, r5 = code, r14 = window.  out: r0 = 1 / 0
; rule: wrap iff (pen - x0) > L,  L = adv*(W-1)  [W = cells per line]; windows whose 'last cell free' byte is 0
; use L = adv*(W-2) unless the code has the 0x4000 hang flag.  Identical to the original for 12/24 px advances.
wrap_A: bra   wrap_c
        mov   #0,r1                   ; delay slot: offset delta (variants A and C)
wrap_B: mov   #-8,r1                  ; variant B: every window offset is 8 lower
wrap_c: mov   #60,r0
        add   r1,r0
        mov.b @(r0,r14),r2            ; r2 = W (cells per line, +0x3c)
        add   #2,r0
        mov.b @(r0,r14),r3            ; r3 = advance (+0x3e)
        add   #-1,r2
        mul.l r3,r2                   ; MACL = adv*(W-1)
        add   #7,r0
        mov.b @(r0,r14),r0            ; r0 = 'last cell free' flag (+0x45)
        sts   macl,r2                 ; r2 = L
        tst   r0,r0
        bf    wrap_l                  ; flag != 0 -> L as is
        mov   #64,r0
        shll8 r0                      ; r0 = 0x4000
        and   r5,r0
        tst   r0,r0
        bf    wrap_l                  ; hanging character -> L as is
        sub   r3,r2                   ; else one cell less
wrap_l: mov   #74,r0
        add   r1,r0
        mov.w @(r0,r14),r0            ; r0 = x0 (+0x4a)
        sub   r0,r4                   ; r4 = used width
        cmp/gt r2,r4
        movt  r0
        rts
        nop
        .align 4
tblp:   .long TABLE
"""


def assemble_cave(table=TABLE, cave=CAVE):
    code, listing, sym = sh4asm2.assemble(CAVE_SRC, cave, {'TABLE': table})
    if len(code) > CAVE_MAX:
        raise ValueError('cave too large: %d' % len(code))
    return code, listing, sym


# ------------------------------------------------------------------------------------------------ variants
# window offsets (from the decompiled/disassembled layout functions, see docs)
VAR = {
    'A': dict(adv=62, pen=10, units=11, W=60, LH=63, F=69, X0=74, Y0=76, ptr=48, cnt=44, adv_e='adv_A', wrap_e='wrap_A'),
    'B': dict(adv=54, pen=11, units=10, W=52, LH=55, F=61, X0=66, Y0=68, ptr=44, cnt=42, adv_e='adv_B', wrap_e='wrap_B'),
    'C': dict(adv=62, pen=11, units=10, W=60, LH=63, F=69, X0=74, Y0=76, ptr=48, cnt=44, adv_e='adv_A', wrap_e='wrap_A'),
}
B_NAMES = ('COMM.BIN', 'CON_REP.BIN', 'NF_CON.BIN', 'PASS_PL.BIN', 'J1_REP.BIN', 'PL_CON.BIN')

ADV_RE = re.compile(rb'(.)\xe0(.)\x02\x00\xe3\x27\x33\x3e\x32\x21\x42\x2c([\x3a\x3b])\x04\xa0\x01([\x7a\x7b])'
                    rb'(.)\xe0(.)\x03\x02([\x7a\x7b])\x3c([\x3a\x3b])', re.S)
PROLOGUE = bytes.fromhex('e62fd62fc62fb62fa62f962f862f')


def variant_of(m):
    ofs = m.group(1)[0]
    pen = m.group(3)[0]
    if ofs == 54 and pen == 0x3b:
        return 'B'
    if ofs == 62 and pen == 0x3a:
        return 'A'
    if ofs == 62 and pen == 0x3b:
        return 'C'
    raise ValueError('unknown advance variant ofs=%d pen=%#x' % (ofs, pen))


def wrap_old_template(v, a):
    """expected original bytes of the wrap fragment for variant v (A: whole block up to the draw code; B/C: first fragment)."""
    P = VAR[v]
    U = P['units']
    pen = P['pen']
    # first part is common (the bf displacement byte is a wildcard ('.') in the regex made from it)
    return P


def wrap_regex(v):
    """byte regex for the original wrap decision (variant A: 68 bytes; B/C: first fragment, 36 bytes)."""
    P = VAR[v]
    U, pen, W, LH, X0 = P['units'], P['pen'], P['W'], P['LH'], P['X0']

    def w(x):
        return struct.pack('<H', x)

    def e(b):
        return re.escape(b)
    # mov rU,r4 ; mov #W,r0 ; mov #0,r3 ; mov.b @(r0,r14),r2 ; add #1,r4 ; cmp/gt r4,r3 ; add #-1,r2 ; addc r3,r4 ;
    # shar r4 ; cmp/gt r2,r4 ; bf <x> ; mov #LH,r0 ; mov.b @(r0,r14),r2 ; mov #X0,r0 ; mov.w @(r0,r14),rPEN ;
    # add r2,r8 ; bra <x> ; mov r13,rU
    head = (w(0x6403 | (U << 4)) + w(0xE000 | W) + w(0xE300) + w(0x02EC) + w(0x7401) + w(0x3347) + w(0x72FF)
            + w(0x343E) + w(0x4421) + w(0x3427))
    bf = b'.\x8b'
    wrapact = None
    if v == 'A':
        # mov #LH,r0 ; mov.b @(r0,r14),r2 ; mov #X0,r0 ; mov.w @(r0,r14),r10 ; add r2,r8 ; bra ; mov r13,r11
        wrapact = (w(0xE000 | LH) + w(0x02EC) + w(0xE000 | X0) + w(0x0AED) + w(0x382C))
    else:
        # mov #LH,r0 ; mov.b @(r0,r14),r2 ; mov #X0,r0 ; mov.w @(r0,r14),r11 ; add r2,r8
        wrapact = (w(0xE000 | LH) + w(0x02EC) + w(0xE000 | X0) + w(0x0BED) + w(0x382C))
    bra = b'.\xa0'
    delay = w(0x6AD3 if v != 'A' else 0x6BD3)    # mov r13,r10 (B/C) / mov r13,r11 (A)
    pat = e(head) + bf + e(wrapact) + bra + e(delay)
    return re.compile(pat, re.S)


# ------------------------------------------------------------------------------------------------ site discovery
def load_bases():
    bases = {}
    tsv = os.path.join(ROOT, 'tools', 're', 'textengine', 'survey_overlays.tsv')
    for line in open(tsv, encoding='utf8').read().splitlines()[1:]:
        c = line.split('\t')
        if c[1].startswith('0x'):
            bases[c[0]] = int(c[1], 16)
    return bases


def scan_all():
    """returns list of site dicts for every overlay copy that contains the layout function."""
    bases = load_bases()
    sites = []
    files = sorted(glob.glob(os.path.join(EXTRACTED, 'FLOW_PRG', '*.BIN'))) + [os.path.join(EXTRACTED, 'ATFIRST', 'HELP.BIN')]
    for p in files:
        d = open(p, 'rb').read()
        name = os.path.basename(p)
        iso = os.path.relpath(p, EXTRACTED).replace(os.sep, '/')
        base = bases.get(name)
        for m in ADV_RE.finditer(d):
            off = m.start()
            if off % 2:
                continue
            v = variant_of(m)
            # the 2nd half of the regex must repeat the same offset/regs as the first (full-width branch)
            assert m.group(1)[0] == m.group(5)[0] and m.group(3)[0] == m.group(8)[0]
            s = dict(iso=iso, name=name, base=base, adv_off=off, variant=v)
            # wrap site
            wr = wrap_regex(v)
            woff = off - (0x15c if v == 'A' else 0xde)
            wm = wr.match(d, woff)
            s['wrap_off'] = woff if wm else None
            s['wrap_len'] = (wm.end() - woff) if wm else None
            # function entry (prologue before the wrap site)
            fe = d.rfind(PROLOGUE, max(0, off - 0x500), off)
            s['func_off'] = fe if fe >= 0 else None
            sites.append(s)
    return sites


# ------------------------------------------------------------------------------------------------ hook generation
def pad_nops(code, size, a):
    assert len(code) <= size, (len(code), size)
    return code + b'\x09\x00' * ((size - len(code)) // 2)


def hook_adv(site, sym):
    """16/18 byte replacement of the half-width advance (H1)."""
    v = VAR[site['variant']]
    a = site['adv_off']                    # file offset; RAM address = base + a, base is 4-aligned -> only a%4 matters
    A = (site.get('base') or 0) + a
    src = """
        mov.l @(lit,pc),r3
        jsr   @r3
        mov   r12,r4
        add   r0,r%d
        bra   join
        add   #1,r%d
        .align 4
lit:    .long %s
""" % (v['pen'], v['units'], '%#x' % sym[v['adv_e']])
    syms = {'join': A + 0x1A}
    code, lst, _ = sh4asm2.assemble(src, A, syms)
    assert len(code) in (16, 18)
    return A, code, lst, len(code)


def hook_adv_inline(site, table=TABLE):
    """OPTION 1A (no cave at all): 16/18-byte replacement that reads the table directly.  No adv != 24 handling and no
    'width 0 -> 12' fallback: the table must be complete (index 0 = space width).  Used for the first emulator test."""
    v = VAR[site['variant']]
    A = (site.get('base') or 0) + site['adv_off']
    src = """
        mov.l @(lit,pc),r3
        extu.b r12,r0
        mov.b @(r0,r3),r2
        add   r2,r%d
        bra   join
        add   #1,r%d
        .align 4
lit:    .long %s
""" % (v['pen'], v['units'], '%#x' % table)
    code, lst, _ = sh4asm2.assemble(src, A, {'join': A + 0x1A})
    assert len(code) in (16, 18)
    return A, code, lst, len(code)


def hook_wrap(site, sym):
    """replacement of the wrap decision (H2): 68 bytes (A) / 36 bytes (B, C)."""
    v = VAR[site['variant']]
    a = site['wrap_off']
    A = (site.get('base') or 0) + a
    end = A + site['wrap_len']
    if site['variant'] == 'A':
        endlab = A + 0x44                  # first instruction of the draw code (original 'bf/bra' target)
        size = 0x44
    else:
        endlab = A + 0x66                  # B/C: original join (the 'bra' target of the old fragment) is +0x66
        size = 36
    src = """
        mov   r12,r5
        mov.l @(lit,pc),r3
        jsr   @r3
        mov   r%d,r4
        tst   r0,r0
        bt    done
        mov   #%d,r0
        mov.b @(r0,r14),r2
        add   r2,r8
        mov   #%d,r0
        mov.w @(r0,r14),r%d
        bra   done
        mov   r13,r%d
        .align 4
lit:    .long %s
""" % (v['pen'], v['LH'], v['X0'], v['pen'], v['units'], '%#x' % sym[v['wrap_e']])
    syms = {'done': endlab}
    code, lst, _ = sh4asm2.assemble(src, A, syms)
    return A, pad_nops(code, size, A), lst, size


def canon(text):
    return text.strip()


def capstone_check(addr, code):
    """decode `code` with capstone; return list of canonical texts (one per 2-byte word)."""
    out = []
    for i in range(0, len(code), 2):
        ins = list(_MD.disasm(code[i:i + 2], addr + i))
        out.append(('%s %s' % (ins[0].mnemonic, ins[0].op_str)).strip() if ins else '.word')
    return out


# ------------------------------------------------------------------------------------------------ models
def orig_model(codes, W, A, flag, x0, y0, lh):
    pen, y, units = x0, y0, 0
    out = []
    for c in codes:
        c &= 0xFFFF
        if c & 0x2000:
            if c == 0x200A:
                pen, y, units = x0, y + lh, 0
                out.append((pen, y))
                continue
            if c != 0x2020:
                out.append((pen, y))
                continue
        r4 = (units + 1) >> 1
        if r4 > W - 1 or (r4 == W - 1 and flag == 0 and not c & 0x4000):
            pen, y, units = x0, y + lh, 0
        if c == 0x2020 or c & 0x8000:
            pen += (A + (1 if A < 0 else 0)) >> 1
            units += 1
        else:
            pen += A
            units += 2
        out.append((pen, y))
    return out


def new_model(codes, W, A, flag, x0, y0, lh, table, wrap=True, adv=True):
    """spec of the patched behaviour.  wrap/adv select which hooks are active."""
    pen, y, units = x0, y0, 0
    out = []
    for c in codes:
        c &= 0xFFFF
        if c & 0x2000:
            if c == 0x200A:
                pen, y, units = x0, y + lh, 0
                out.append((pen, y))
                continue
            if c != 0x2020:
                out.append((pen, y))
                continue
        used = pen - x0
        if wrap:
            L = A * (W - 1)
            if flag == 0 and not c & 0x4000:
                L -= A
            do_wrap = used > L
        else:
            r4 = (units + 1) >> 1
            do_wrap = r4 > W - 1 or (r4 == W - 1 and flag == 0 and not c & 0x4000)
        if do_wrap:
            pen, y, units = x0, y + lh, 0
        if c == 0x2020 or c & 0x8000:
            if adv and A == 24:
                w = table[(0x8000 if c == 0x2020 else c) & 0xFF] or 12
            else:
                w = (A + (1 if A < 0 else 0)) >> 1
            pen += w
            units += 1
        else:
            pen += A
            units += 2
        out.append((pen, y))
    return out


# ------------------------------------------------------------------------------------------------ execution harness
def run_layout(img, base, site, codes, W, A, flag, x0, y0, lh, extra=(), count=None, clobber=None, want_calls=False):
    """execute the layout function found in `img` (bytes) for the window described; returns [(pen, y)] per code."""
    v = VAR[site['variant']]
    m = sh4sim.Machine()
    m.load(base, img)
    for a, d in extra:
        m.load(a, d)
    m.native = [(base, base + len(img)), (CAVE, CAVE + CAVE_MAX), (ALT_CAVE_GAP1, ALT_CAVE_GAP1 + CAVE_MAX)]
    win = 0x8D000000 - 0x4000
    code_arr = win + 0x800
    for i, c in enumerate(codes):
        m.wn(code_arr + 2 * i, c, 2)
    m.wn(win + v['ptr'], code_arr, 4)
    m.wn(win + v['cnt'], len(codes) if count is None else count, 2)
    m.wn(win + v['W'], W, 1)
    m.wn(win + v['adv'], A, 1)
    m.wn(win + v['LH'], lh, 1)
    m.wn(win + v['F'], flag, 1)
    m.wn(win + v['X0'], x0, 2)
    m.wn(win + v['Y0'], y0, 2)
    m.wn(win + 56 if v['adv'] == 62 else win + 48, 0x20, 4)
    m.R[4] = win
    m.R[15] = 0x8D000000 - 0x100
    m.PR = 0x8C000000
    # the layout function pushes r8..r14 (+PR); it returns by rts to PR
    join = base + site['adv_off'] + 0x1A
    pen_reg = v['pen']
    snaps = []
    seen = {'n': 0}

    def snap(mm):
        snaps.append((sh4sim.s32(mm.R[pen_reg]), sh4sim.s32(mm.R[8])))

    entry = base + site['func_off']
    watch = {join: snap}
    if clobber is not None:
        # liveness test: at the exit of every patched region overwrite the registers the hook is allowed to
        # modify (r0-r5) with pseudo-random values; the rest of the function must not care.
        import random
        rnd = random.Random(clobber)
        exits = [join, base + site['adv_off'] + 0x1A] + ([base + site['wrap_off'] + (0x44 if site['variant'] == 'A' else 0x66)]
                                                         if site.get('wrap_off') is not None else [])

        def junk(mm, orig=None):
            for r in range(6):
                mm.R[r] = rnd.getrandbits(32)
            mm.T = rnd.getrandbits(1)
        for a in exits:
            prev = watch.get(a)
            watch[a] = (lambda mm, prev=prev: (prev(mm) if prev else None, junk(mm)))
    m.run(entry, 0x8C000000, watch=watch, max_steps=400000)
    if want_calls:
        ext = [c for c in m.calls if not (CAVE <= c[0] < CAVE + CAVE_MAX)]
        return snaps, ext
    return snaps


def table_vec(kind):
    t = bytearray(256)
    if kind == 'all12':
        t[:] = bytes([12]) * 256
    elif kind == 'prop':
        for c in range(256):
            t[c] = 3 + (c * 7) % 10          # 3..12
        t[0x20 - 0x20] = 6                   # space (index 0)
    elif kind == 'zero':
        pass
    return bytes(t)


def test_vectors():
    asc = lambda s: [0x8000 | ord(ch) if ch != ' ' else 0x2020 for ch in s]
    vecs = []
    vecs.append(asc('The quick brown fox jumps over the lazy dog, 0123456789 WWWW iiii llll!') * 2)
    vecs.append(asc('abc') + [0x200A] + asc('def') + [0x2012] + asc('ghi') * 30)
    vecs.append([0x0123, 0x0124, 0x4125, 0x0126] * 15 + asc('mixed ASCII text') + [0x4127, 0x0128] * 10)
    vecs.append(([0x8000 | 0x2E, 0x8000 | 0x41, 0xC000 | 0x2E, 0x4000 | 0x0150, 0x8000 | 0xA1, 0x8000 | 0xDF] * 12))
    return vecs


# ------------------------------------------------------------------------------------------------ patch application
def build_hooks(site, sym, hooks=('adv', 'wrap')):
    out = []
    if 'adv' in hooks:
        A, code, lst, size = hook_adv(site, sym)
        out.append(('H1', site['adv_off'], code, lst, size, A))
    if 'adv_inline' in hooks:
        A, code, lst, size = hook_adv_inline(site, TABLE)
        out.append(('H1i', site['adv_off'], code, lst, size, A))
    if 'wrap' in hooks and site['wrap_off'] is not None:
        A, code, lst, size = hook_wrap(site, sym)
        out.append(('H2', site['wrap_off'], code, lst, size, A))
    return out


def apply_hooks(img, site, sym, hooks=('adv', 'wrap')):
    b = bytearray(img)
    for name, off, code, lst, size, A in build_hooks(site, sym, hooks):
        assert len(code) == size, (name, len(code), size)
        b[off:off + size] = code
    return bytes(b)


# ------------------------------------------------------------------------------------------------ build API
# (used by tools/build_patch.py; see docs/font-patch-design.md s9).  All functions are pure: bytes in, bytes out.
def scan_bytes(d, name=''):
    """sites inside one overlay image (base-agnostic: only base % 4 == 0 matters, which holds for every load base)."""
    sites = []
    for m in ADV_RE.finditer(d):
        off = m.start()
        if off % 2:
            continue
        v = variant_of(m)
        s = dict(iso=name, name=os.path.basename(name), base=0, adv_off=off, variant=v)
        woff = off - (0x15C if v == 'A' else 0xDE)
        wm = wrap_regex(v).match(d, woff) if woff >= 0 else None
        s['wrap_off'] = woff if wm else None
        s['wrap_len'] = (wm.end() - woff) if wm else None
        s['func_off'] = None
        sites.append(s)
    return sites


def patch_overlay(d, name='', hooks=('adv', 'wrap'), table=TABLE, cave=CAVE):
    """returns (new image, [site dicts]).  Raises ValueError unless the image has exactly one layout function.
    An image without the signature is returned unchanged with an empty list (overlays without the tsString library)."""
    sites = scan_bytes(d, name)
    if not sites:
        return bytes(d), []
    if len(sites) != 1:
        raise ValueError('%s: %d layout functions found' % (name, len(sites)))
    _, _, sym = assemble_cave(table, cave)
    s = sites[0]
    if 'wrap' in hooks and s['wrap_off'] is None:
        raise ValueError('%s: advance site found but the wrap block does not match the template' % name)
    return apply_hooks(d, s, sym, hooks), sites


def patch_1st_read(k, table_bytes=None, table=TABLE, cave=CAVE):
    """write cave + 256-byte table into the zero tail of 1ST_READ.BIN (file offset address - 0x8c010000).
    table_bytes None -> all 12 (behaviour identical to the original game)."""
    code, _, _ = assemble_cave(table, cave)
    tb = bytes([12]) * 256 if table_bytes is None else bytes(table_bytes)
    if len(tb) != 256 or max(tb) > 24:
        raise ValueError('table must be 256 bytes with values <= 24')
    b = bytearray(k)
    for addr, data in ((cave, code), (table, tb)):
        o = addr - 0x8C010000
        if any(b[o:o + max(len(data), CAVE_MAX if addr == cave else 256)]):
            raise ValueError('area %#x of 1ST_READ.BIN is not zero (already patched or used by another stage)' % addr)
        b[o:o + len(data)] = data
    return bytes(b)


def embed_table(font, table):
    """append the 256-byte advance table at the fixed address TABLE (= last 256 bytes of the FONT.BIN load window);
    the file is zero padded to exactly FONT_WINDOW (679,936) bytes."""
    if len(table) != 256:
        raise ValueError('table must be 256 bytes')
    if len(font) > FONT_WINDOW - 256:
        raise ValueError('FONT.BIN is %d bytes; the table needs the last 256 bytes of the %d byte window' % (len(font), FONT_WINDOW))
    return bytes(font) + bytes(FONT_WINDOW - 256 - len(font)) + bytes(table)


# ------------------------------------------------------------------------------------------------ commands
def cmd_scan():
    sites = scan_all()
    print('sites', len(sites))
    from collections import Counter
    print(Counter(s['variant'] for s in sites))
    bad = [s for s in sites if s['wrap_off'] is None or s['func_off'] is None]
    print('sites without wrap match or prologue:', [(s['name'], s['variant']) for s in bad])
    mis = [(s['name'], hex((s['base'] or 0) + s['adv_off'])) for s in sites if (s['base'] is None) or (s['base'] % 4)]
    print('base unknown:', mis)
    for s in sites:
        print('%-26s %s base=%s adv@%#x wrap@%s mod4=%d' % (s['iso'], s['variant'], hex(s['base']) if s['base'] else '?',
                                                       (s['base'] or 0) + s['adv_off'],
                                                       hex((s['base'] or 0) + s['wrap_off']) if s['wrap_off'] is not None else '-',
                                                       s['adv_off'] % 4))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    if argv[1] == 'scan':
        cmd_scan()
    elif argv[1] in ('selftest', 'manifest', 'liveness'):
        import fontpatch_tests
        return fontpatch_tests.run(argv[1])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
