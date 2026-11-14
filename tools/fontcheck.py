"""Static self-check of the proportional font patch (tools/fontpatch.py).   Needs capstone (pip install capstone).

    python -I -X utf8 tools/fontcheck.py            # everything (about 1-2 min)
    python -I -X utf8 tools/fontcheck.py --quick    # decode + 3 representative overlays only (used by tools/test_pipeline.py)

What is checked (nothing here runs the game or an emulator):
  1  the embedded cave bytes == the cave ASSEMBLED from the source below with tools/sh4asm2.py (written from the SH-4
     manual, independent of fontpatch.py's constants), for both placements; every instruction is decoded with CAPSTONE
     and must equal the assembler's meaning.
  2  for every site found in extracted/ (105 files) at its REAL load address: the hook bytes == the hooks assembled from
     the sources below; capstone decodes every patched word as intended; every branch target / pc-relative literal address
     is the intended one and 4-aligned; every delay slot is legal; the literal words hold the cave entry addresses;
     nothing outside the declared regions changed; the file size is unchanged; no branch or pc-relative load of the
     function points into a replaced interior (xref check).
  3  the CAVE routines are executed in tools/sh4sim.py against independent Python formulas (adv: every low byte, six window
     advances; wrap: random windows).
  4  the real layout function of the PATCHED overlay is executed (stubs for external calls, FPU as no-op): with an all-12
     table it is bit-exact the ORIGINAL (pen x, y after every code); with the real table the pen x advances follow the
     table and the wrap follows the pixel rule.  Sample strings are printed.
"""
import os
import random
import re
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fontpatch as FP       # noqa: E402
import sh4asm2               # noqa: E402
import sh4sim                # noqa: E402

try:
    import capstone as _cs
    MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception as e:       # pragma: no cover
    raise SystemExit('fontcheck needs capstone: %s' % e)

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print('FAIL', msg)
    return cond


# ------------------------------------------------------------------------------------------------ assembler sources
CAVE_SRC = """
; ---- H1: advance of one half-width code.  in: r4 = code (low byte = character), r14 = window.  out: r0 = px.
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
VAR = {   # window / register layout per variant (docs/font-hook-notes.md, docs/font-patch-design.md)
    'A': dict(adv=62, pen=10, units=11, W=60, LH=63, F=69, X0=74, Y0=76, ptr=48, cnt=44),
    'B': dict(adv=54, pen=11, units=10, W=52, LH=55, F=61, X0=66, Y0=68, ptr=44, cnt=42),
    'C': dict(adv=62, pen=11, units=10, W=60, LH=63, F=69, X0=74, Y0=76, ptr=48, cnt=44),
}
PROLOGUE = bytes.fromhex('e62fd62fc62fb62fa62f962f862f')
ENTRY = {'A': 'adv_A', 'B': 'adv_B', 'C': 'adv_A'}
WENTRY = {'A': 'wrap_A', 'B': 'wrap_B', 'C': 'wrap_A'}


def asm_cave(ct):
    return sh4asm2.assemble(CAVE_SRC, ct[0], {'TABLE': ct[1]})


def h1_src(v, entry):
    p = VAR[v]
    return """
        mov.l @(lit,pc),r3
        jsr   @r3
        mov   r12,r4
        add   r0,r%d
        bra   join
        add   #1,r%d
        .align 4
lit:    .long %#x
""" % (p['pen'], p['units'], entry)


def h2_src(v, entry):
    p = VAR[v]
    return """
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
lit:    .long %#x
""" % (p['pen'], p['LH'], p['X0'], p['pen'], p['units'], entry)


def capstone_text(addr, word):
    ins = list(MD.disasm(word, addr))
    return ('%s %s' % (ins[0].mnemonic, ins[0].op_str)).strip() if ins else '.word'


def load_bases():
    bases = {}
    tsv = os.path.join(HERE, 're', 'textengine', 'survey_overlays.tsv')
    for line in open(tsv, encoding='utf8').read().splitlines()[1:]:
        c = line.split('\t')
        if c[1].startswith('0x'):
            bases[c[0]] = int(c[1], 16)
    return bases


# ------------------------------------------------------------------------------------------------ 1. the cave
def check_cave():
    n_ins = 0
    for pname, ct in FP.PLACEMENTS.items():
        code, lst, sym = asm_cave(ct)
        check(code == FP.cave_bytes(ct), 'embedded cave bytes != assembled cave (%s)' % pname)
        check(len(code) == FP.CAVE_SIZE, 'cave size %d' % len(code))
        check(sym['adv_B'] - ct[0] == FP.ENTRY_ADV_B and sym['wrap_A'] - ct[0] == FP.ENTRY_WRAP_A and
              sym['wrap_B'] - ct[0] == FP.ENTRY_WRAP_B, 'cave entry offsets differ from fontpatch constants')
        for a, bb, t in lst:
            if len(bb) == 2:
                n_ins += 1
                check(capstone_text(a, bb) == t, 'cave %#x %s: capstone %r != assembler %r' % (a, bb.hex(), capstone_text(a, bb), t))
    print('1. cave: %d bytes, both placements assemble to the embedded bytes; %d instructions decoded by capstone' % (FP.CAVE_SIZE, n_ins))


# ------------------------------------------------------------------------------------------------ 2. the hooks
DELAYED = ('bra', 'bsr', 'jmp', 'jsr', 'rts', 'braf', 'bsrf', 'bt/s', 'bf/s', 'rte')


def hook_words(addr, data):
    return [(addr + i, data[i:i + 2]) for i in range(0, len(data), 2)]


def parse_target(op):
    m = re.match(r'(0x[0-9a-f]+)', op.strip())
    return int(m.group(1), 16) if m else None


def check_hook(name, v, which, base, off, new, old_len, ct):
    """decode every word of one hook (new bytes `new` at file offset `off`); returns the number of decoded instructions"""
    addr = base + off
    words = hook_words(addr, new)
    n = 0
    lit_at = None
    # find the literal: the 4-aligned long after the unconditional branch (A: bra join/done, then the long)
    texts = {}
    for a, w in words:
        texts[a] = capstone_text(a, w)
    # structural expectations from the sources
    exp = []
    src = h1_src(v, 0) if which == 'H1' else h2_src(v, 0)
    p = VAR[v]
    done = addr + (0x1A if which == 'H1' else (0x44 if v == 'A' else 0x66))
    code, lst, _ = sh4asm2.assemble(src, addr, {'join': done, 'done': done})
    ins = [(a, bb, t) for a, bb, t in lst if len(bb) == 2]
    # 'new' without the literal and the nops must equal the assembled prefix
    check(new[:len(code) - 4] == code[:-4], '%s %s %s: bytes differ from the assembled hook' % (name, which, v))
    lit_off = len(code) - 4
    check(struct.unpack_from('<I', new, lit_off)[0] == ct[0] + (FP.H1_ENTRY[v] if which == 'H1' else FP.H2_ENTRY[v]),
          '%s %s: literal is not the cave entry' % (name, which))
    check(all(new[i:i + 2] == FP.NOP for i in range(lit_off + 4, len(new), 2)), '%s %s: padding is not NOPs' % (name, which))
    check(len(new) == old_len, '%s %s: length' % (name, which))
    check((addr + lit_off) % 4 == 0, '%s %s: literal %#x not 4-aligned' % (name, which, addr + lit_off))
    prev = None
    for a, bb, t in ins:
        n += 1
        cst = capstone_text(a, bb)
        check(cst == t, '%s %s %#x: capstone %r != %r' % (name, which, a, cst, t))
        # delay slot legality
        if prev and prev.split()[0] in DELAYED:
            check(t.split()[0] not in DELAYED and not t.startswith('mov.l 0x') and not t.startswith('mov.w 0x') and not t.startswith('mova'),
                  '%s %s %#x: illegal delay slot %r after %r' % (name, which, a, t, prev))
            if prev.startswith('jsr'):
                check(t.split(',')[-1].strip() not in ('r3',), '%s %s: jsr slot clobbers the target register' % (name, which))
        prev = t
        # branch targets and literal EA
        mn = t.split()[0]
        if mn in ('bra', 'bt', 'bf', 'bt/s', 'bf/s'):
            check(parse_target(t.split(None, 1)[1]) == done, '%s %s %#x: branch target %s != %#x' % (name, which, a, t, done))
        if t.startswith('mov.l 0x'):
            ea = parse_target(t.split(None, 1)[1])
            check(ea == addr + lit_off, '%s %s %#x: pc-relative load EA %#x != literal %#x' % (name, which, a, ea, addr + lit_off))
            check(ea % 4 == 0, '%s %s: EA not aligned' % (name, which))
    return n


def func_range(d, h1):
    e = d.rfind(PROLOGUE, max(0, h1 - 0x500), h1)
    return e


def xref_check(d, base, v, h1, h2, h2len, ct):
    """no branch or pc-relative reference from the layout function into a replaced interior"""
    fe = func_range(d, h1)
    if fe < 0:
        return 0, 'no prologue'
    # the function ends at its rts: scan up to 0x300 bytes after the advance site
    end = min(len(d), h1 + 0x180)
    inter = [(h1 + 2, h1 + 16), (h2 + 2, h2 + h2len)]
    bad = []
    dec = {off: capstone_text(base + off, d[off:off + 2]) for off in range(fe, end, 2)}
    targets = set()
    for off, t in dec.items():
        if t.split()[0] in ('bra', 'bt', 'bf', 'bt/s', 'bf/s') and len(t.split(None, 1)) > 1:
            tg = parse_target(t.split(None, 1)[1])
            if tg is not None:
                targets.add(tg - base)
    dead = False                      # words after an unconditional transfer up to the next branch target are literal pools
    prev_uncond = None
    for off in range(fe, end, 2):
        if off in targets:
            dead = False
        t = dec[off]
        if not dead:
            mn = t.split()[0]
            if mn in ('bra', 'bsr', 'bt', 'bf', 'bt/s', 'bf/s') or t.startswith('mov.l 0x') or t.startswith('mov.w 0x') or t.startswith('mova 0x'):
                tg = parse_target(t.split(None, 1)[1]) if len(t.split(None, 1)) > 1 else None
                if tg is not None:
                    for lo, hi in inter:
                        if base + lo <= tg < base + hi and not (lo <= off < hi):
                            bad.append((hex(base + off), t))
        if prev_uncond is not None and off == prev_uncond + 2:      # the delay slot has been consumed: dead from here
            dead = True
            prev_uncond = None
        if not dead and t.split()[0] in ('bra', 'rts', 'jmp'):
            prev_uncond = off
    return len(bad), bad


def check_sites(quick):
    bases = load_bases()
    ct = FP.placement()
    cnt = {'A': 0, 'B': 0, 'C': 0}
    ninst = 0
    nxref = 0
    imgs = {}
    for rel in FP.overlay_paths():
        d = FP.read_extracted(rel)
        sites = FP.find_sites(d, rel)
        if not sites:
            continue
        s = sites[0]
        v = s['variant']
        cnt[v] += 1
        name = os.path.basename(rel)
        base = bases.get(name)
        check(base is not None and base % 4 == 0, '%s: unknown or unaligned base' % rel)
        base = base or 0
        imgs[rel] = (d, s, base)
        new, ss = FP.patch_overlay(d, rel, 'ABC', True, ct)
        check(len(new) == len(d), '%s: size changed' % rel)
        h1, h2, n2 = s['h1'], s['h2'], len(FP.H2_OLD[v])
        diff = [i for i in range(len(d)) if d[i] != new[i]]
        check(all(h1 <= i < h1 + 16 or h2 <= i < h2 + n2 for i in diff), '%s: bytes changed outside the hook regions' % rel)
        check(h1 > h2 + n2 or h2 > h1 + 16, '%s: regions overlap' % rel)
        ninst += check_hook(rel, v, 'H1', base, h1, new[h1:h1 + 16], 16, ct)
        ninst += check_hook(rel, v, 'H2', base, h2, new[h2:h2 + n2], n2, ct)
        nb, bad = xref_check(d, base, v, h1, h2, n2, ct)
        nxref += 1
        check(nb == 0, '%s: branch/pc-relative reference into a replaced interior: %s' % (rel, bad))
    check(cnt == {'A': 98, 'B': 6, 'C': 1}, 'site counts %s' % cnt)
    # exact (old, new) byte pairs: one distinct pair per variant and hook
    pairs = {}
    for rel, (d, s, base) in imgs.items():
        v = s['variant']
        pairs.setdefault((v, 'H1'), set()).add((d[s['h1']:s['h1'] + 16], FP.hook_h1(v, ct)))
        pairs.setdefault((v, 'H2'), set()).add((d[s['h2']:s['h2'] + len(FP.H2_OLD[v])], FP.hook_h2(v, ct)))
    check(all(len(p) == 1 for p in pairs.values()), 'more than one (old,new) pair per variant/hook')
    print('2. %d sites %s: %d patched instructions decoded by capstone and matched to the assembler, branch targets, '
          'literal EAs, delay slots, regions, sizes OK; xref check over %d functions; %d distinct (old,new) byte pairs' %
          (sum(cnt.values()), cnt, ninst, nxref, len(pairs)))
    return imgs


# ------------------------------------------------------------------------------------------------ 3. the cave in the interpreter
def run_cave(ct, tbl, entry_off, regs, win_bytes=None):
    m = sh4sim.Machine()
    code = FP.cave_bytes(ct)
    m.load(ct[0], code)
    m.load(ct[1], tbl)
    win = 0x8D000000 - 0x4000
    for k, (n, val) in (win_bytes or {}).items():
        m.wn(win + k, val, n)
    for r, val in regs.items():
        m.R[r] = val
    m.R[14] = win
    sentinel = 0x8C000000
    m.PR = sentinel
    m.native = [(ct[0], ct[0] + FP.CAVE_SIZE)]
    m.run(ct[0] + entry_off, sentinel, max_steps=1000)
    return sh4sim.s32(m.R[0])


def check_cave_exec(quick):
    ct = FP.placement()
    rnd = random.Random(5)
    tbl = bytes(rnd.choice([0, 0, 1, 5, 9, 12, 13, 24]) for _ in range(256))
    n = 0
    for entry, off_adv in (('A', FP.ENTRY_ADV_A), ('B', FP.ENTRY_ADV_B)):
        woff = 62 if entry == 'A' else 54
        for A in (24, 16, 32, 10, 5, 1, 20, -2):
            for lo in range(256) if not quick else range(0, 256, 3):
                code = 0x8000 | lo
                got = run_cave(ct, tbl, off_adv, {4: code}, {woff: (1, A & 0xFF)})
                if A == 24:
                    exp = tbl[lo] or 12
                else:
                    exp = (A + (1 if A < 0 else 0)) >> 1
                n += 1
                check(got == exp, 'cave adv entry=%s A=%d byte=%#x: got %d expected %d' % (entry, A, lo, got, exp))
    for entry, off_w in (('A', FP.ENTRY_WRAP_A), ('B', FP.ENTRY_WRAP_B)):
        d = 0 if entry == 'A' else -8
        for _ in range(300 if not quick else 80):
            W = rnd.randint(1, 30)
            A = rnd.choice([24, 24, 16, 32, 20, 10])
            flag = rnd.choice([0, 1, 2])
            x0 = rnd.randint(0, 500)
            pen = x0 + rnd.randint(0, 24 * W + 30)
            code = rnd.choice([0x8041, 0xC041, 0x4141, 0x0123])
            wb = {60 + d: (1, W), 62 + d: (1, A), 69 + d: (1, flag), 74 + d: (2, x0)}
            got = run_cave(ct, tbl, off_w, {4: pen, 5: code}, wb)
            L = A * (W - 1)
            if flag == 0 and not code & 0x4000:
                L -= A
            exp = 1 if (pen - x0) > L else 0
            n += 1
            check(got == exp, 'cave wrap entry=%s W=%d A=%d flag=%d used=%d code=%#x: got %d expected %d' % (entry, W, A, flag, pen - x0, code, got, exp))
    print('3. cave executed in tools/sh4sim.py against independent formulas: %d cases' % n)


# ------------------------------------------------------------------------------------------------ 4. the real layout function
def orig_model(codes, W, A, flag, x0, y0, lh):
    """the ORIGINAL cell rule (docs/text-engine.md s4.4)"""
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


def new_model(codes, W, A, flag, x0, y0, lh, table, wrap=True):
    """the documented behaviour of the patched function"""
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
        if wrap:
            L = A * (W - 1)
            if flag == 0 and not c & 0x4000:
                L -= A
            do_wrap = pen - x0 > L
        else:
            r4 = (units + 1) >> 1
            do_wrap = r4 > W - 1 or (r4 == W - 1 and flag == 0 and not c & 0x4000)
        if do_wrap:
            pen, y, units = x0, y + lh, 0
        if c == 0x2020 or c & 0x8000:
            w = (table[(0x8000 if c == 0x2020 else c) & 0xFF] or 12) if A == 24 else (A + (1 if A < 0 else 0)) >> 1
            pen += w
            units += 1
        else:
            pen += A
            units += 2
        out.append((pen, y))
    return out


def run_layout(img, base, v, h1, codes, W, A, flag, x0, y0, lh, extra=(), native=()):
    p = VAR[v]
    m = sh4sim.Machine()
    m.load(base, img)
    for a, d in extra:
        m.load(a, d)
    m.native = [(base, base + len(img))] + list(native)
    win = 0x8D000000 - 0x4000
    arr = win + 0x800
    for i, c in enumerate(codes):
        m.wn(arr + 2 * i, c, 2)
    m.wn(win + p['ptr'], arr, 4)
    m.wn(win + p['cnt'], len(codes), 2)
    m.wn(win + p['W'], W, 1)
    m.wn(win + p['adv'], A & 0xFF, 1)
    m.wn(win + p['LH'], lh, 1)
    m.wn(win + p['F'], flag, 1)
    m.wn(win + p['X0'], x0, 2)
    m.wn(win + p['Y0'], y0, 2)
    m.wn(win + (56 if p['adv'] == 62 else 48), 0x20, 4)
    m.R[4] = win
    m.R[15] = 0x8D000000 - 0x100
    m.PR = 0x8C000000
    join = base + h1 + 0x1A
    snaps = []
    m.run(base + func_range(img, h1), 0x8C000000, watch={join: lambda mm: snaps.append((sh4sim.s32(mm.R[p['pen']]), sh4sim.s32(mm.R[8])))},
          max_steps=400000)
    return snaps


def ascii_codes(s):
    return [0x2020 if ch == ' ' else 0x8000 | ord(ch) for ch in s]


VECTORS = [
    ascii_codes('The quick brown fox jumps over the lazy dog, 0123456789 WWWW iiii llll!') * 2,
    ascii_codes('abc') + [0x200A] + ascii_codes('def') + [0x2012] + ascii_codes('ghi') * 30,
    [0x0123, 0x0124, 0x4125, 0x0126] * 15 + ascii_codes('mixed ASCII text') + [0x4127, 0x0128] * 10,
    ([0x8000 | 0x2E, 0x8000 | 0x41, 0xC000 | 0x2E, 0x4000 | 0x0150, 0x8000 | 0xA1, 0x8000 | 0xDF] * 12),
]
WINDOWS = [(20, 24, 1), (20, 24, 0), (7, 24, 1), (13, 24, 0), (20, 16, 1), (10, 20, 0)]


def sample_table():
    import font as F
    f = FP.read_extracted('FONT.BIN')
    return FP.proportional_font(f, F.Font(f).half())[1]


def check_layout(imgs, quick):
    ct = FP.placement()
    tbl = sample_table()
    all12 = bytes([12]) * 256
    zero = bytes(256)
    cave = FP.cave_bytes(ct)
    reps = ('FLOW_PRG/MEETING.BIN', 'FLOW_PRG/COMM.BIN', 'FLOW_PRG/CSAVE3.BIN')
    todo = [r for r in reps] if quick else list(imgs)
    n = 0
    t0 = time.time()
    for rel in todo:
        d, s, base = imgs[rel]
        v = s['variant']
        full = rel in reps
        both = FP.patch_overlay(d, rel, 'ABC', True, ct)[0]
        adv_only = FP.patch_overlay(d, rel, 'ABC', False, ct)[0]
        wins = WINDOWS if full else [(20, 24, 1), (13, 24, 0)]
        vecs = VECTORS if full else VECTORS[:2]
        for W, A, flag in wins:
            for vec in vecs:
                kw = dict(W=W, A=A, flag=flag, x0=20, y0=240, lh=24)
                ref_model = orig_model(vec, **kw)
                ref = run_layout(d, base, v, s['h1'], vec, **kw)
                check(ref == ref_model, '%s: interpreter on ORIGINAL code != cell-rule model (W=%d A=%d f=%d)' % (rel, W, A, flag))
                for tname, t in (('all12', all12), ('zero', zero), ('real', tbl)):
                    extra = [(ct[0], cave), (ct[1], t)]
                    g1 = run_layout(adv_only, base, v, s['h1'], vec, extra=extra, native=[(ct[0], ct[0] + 104)], **kw)
                    g2 = run_layout(both, base, v, s['h1'], vec, extra=extra, native=[(ct[0], ct[0] + 104)], **kw)
                    if tname in ('all12', 'zero'):
                        check(g1 == ref, '%s H1 table=%s != ORIGINAL (W=%d A=%d f=%d)' % (rel, tname, W, A, flag))
                        check(g2 == ref, '%s H1+H2 table=%s != ORIGINAL (W=%d A=%d f=%d)' % (rel, tname, W, A, flag))
                    check(g1 == new_model(vec, table=t, wrap=False, **kw), '%s H1 table=%s != spec' % (rel, tname))
                    check(g2 == new_model(vec, table=t, wrap=True, **kw), '%s H1+H2 table=%s != spec (W=%d A=%d f=%d)' % (rel, tname, W, A, flag))
                    n += 4
    print('4. layout function of the patched overlays executed in tools/sh4sim.py (%d runs, %d overlays, %.0fs): all-12 / all-0 table '
          'bit-exact the ORIGINAL; real table == spec (pen x, y after every code)' % (n, len(todo), time.time() - t0))


def show_samples(imgs):
    ct = FP.placement()
    tbl = sample_table()
    rel = 'FLOW_PRG/MEETING.BIN'
    d, s, base = imgs[rel]
    both = FP.patch_overlay(d, rel, 'ABC', True, ct)[0]
    kw = dict(W=20, A=24, flag=1, x0=20, y0=240, lh=24)
    print('   MEETING.BIN (variant A) patched layout function, window W=20 cells, A=24, x0=20; pen X after each character:')
    for text in ('Hello, World! iiii WWWW', 'The goalkeeper is injured.', 'Illegal little pill: 10-0 (1250)'):
        codes = ascii_codes(text)
        got = run_layout(both, base, 'A', s['h1'], codes, extra=[(ct[0], FP.cave_bytes(ct)), (ct[1], tbl)], native=[(ct[0], ct[0] + 104)], **kw)
        orig = run_layout(d, base, 'A', s['h1'], codes, **kw)
        pens = [20] + [g[0] for g in got]
        steps = [pens[i + 1] - pens[i] for i in range(len(codes))]
        exp = [tbl[(0x8000 if c == 0x2020 else c) & 0xFF] or 12 for c in codes]
        check(steps == exp, 'sample %r: pen steps %s != table %s' % (text, steps, exp))
        print('   %r' % text)
        print('     advance per char (sim): %s' % ' '.join('%d' % x for x in steps))
        print('     table lookup          : %s' % ' '.join('%d' % x for x in exp))
        print('     end pen x: patched %d px (width %d), original %d px (width %d)' % (pens[-1], pens[-1] - 20, orig[-1][0], orig[-1][0] - 20))
    long = ascii_codes('Opening quarter-final of the regional championship decided on penalties after extra time, sold out.')
    got = run_layout(both, base, 'A', s['h1'], long, extra=[(ct[0], FP.cave_bytes(ct)), (ct[1], tbl)], native=[(ct[0], ct[0] + 104)], **kw)
    orig = run_layout(d, base, 'A', s['h1'], long, **kw)
    first_wrap_new = next((i for i in range(1, len(got)) if got[i][1] != got[i - 1][1]), None)
    first_wrap_old = next((i for i in range(1, len(orig)) if orig[i][1] != orig[i - 1][1]), None)
    print('   overflow demo (no newline code, 101 chars): first auto-wrap before char #%s (patched) vs #%s (original, fixed 12 px = 39 chars)'
          % (first_wrap_new, first_wrap_old))
    check(first_wrap_old == 39, 'original must wrap at 39 chars, got %s' % first_wrap_old)


def main(argv):
    quick = '--quick' in argv
    t0 = time.time()
    check_cave()
    imgs = check_sites(quick)
    check_cave_exec(quick)
    check_layout(imgs, quick)
    show_samples(imgs)
    print('fontcheck: %s (%.0fs)' % ('FAILED (%d)' % len(FAILS) if FAILS else 'all checks passed', time.time() - t0))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
