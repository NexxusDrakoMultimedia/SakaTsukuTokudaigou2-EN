"""Static self-check of the money formatter patch (tools/moneypatch.py).   Needs capstone (pip install capstone).

    python -I -X utf8 tools/moneycheck.py            # everything (about 1 min)
    python -I -X utf8 tools/moneycheck.py --quick    # decode + 3 representative overlays only (used by tools/test_pipeline.py)
    python -I -X utf8 tools/moneycheck.py --e2e      # also build with the real translations and expand every English %m / %D text
    python -I -X utf8 tools/moneycheck.py --before   # also print what the ORIGINAL function prints (Japanese pieces and the
                                                     # first English translation of the pieces) for a table of amounts

Nothing here runs the game or an emulator.  What is checked:
  1  every word of the cave is decoded with CAPSTONE and must equal the assembler's canonical text; every pc-relative
     literal / branch target is the intended one; delay slots are legal.
  2  for every one of the 102 variant-A money functions found in extracted/ (6 variant-B copies belong to overlays linked against
     another 1ST_READ build, INFERRED dead: found and counted, left alone) (at its REAL load address): the hook is exactly
     mov.l @(1,pc),r0 / jmp @r0 / nop / nop / .long CAVE (capstone), nothing else in the file changed, same size; 1ST_READ.BIN
     changed only inside the cave, which was zero before.
  3  the ORIGINAL function (both byte variants) is executed in tools/sh4sim.py (plus the few opcodes it lacks, here) with
     the 1ST_READ helpers it calls (signed div / mod by repeated test, strncpy, strlen) as Python hooks: it prints the Japanese
     text and, with the English pieces of the first translation, '130015000,00' for 1,315,000,000 yen (the playtest bug).
  4  the cave is executed on 40,000 amounts (all edge values, every digit count, random) and flags 0/1: the bytes written
     == Python reference() == the length returned in r0; r8-r15 and PR are preserved; nothing is written outside
     dst[0:n] and the stack below the entry sp; the text parses back to EXACTLY V * 10,000 yen.
  5  the real path: patched overlay + patched 1ST_READ in one memory image; the function is entered at its (hooked) original
     address with the original calling convention and must return to the caller with the reference text.
"""
import os
import random
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import moneypatch as MP          # noqa: E402
import sh4sim                    # noqa: E402

try:
    import capstone as _cs
    MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception as e:           # pragma: no cover
    raise SystemExit('moneycheck needs capstone: %s' % e)

M = sh4sim.M
FAILS = []
STYLE = MP.DEFAULT_STYLE


def cave_bytes():
    return MP.cave_bytes(MP.CAVE_ADDR, STYLE)


def cave_symbols():
    return MP.cave_symbols(MP.CAVE_ADDR, STYLE)


def patch_overlay(d, rel, **kw):
    return MP.patch_overlay(d, rel, style=STYLE, **kw)


def patch_1st_read(k):
    return MP.patch_1st_read(k, style=STYLE)


def ref(v, flag=0):
    return MP.reference(v, flag, STYLE)


RET = 0xDEAD0000
STACK = 0x8CFF0000
OUT = 0x8CF00000


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print('FAIL', msg)
    return cond


class Mach(sh4sim.Machine):
    """sh4sim.Machine plus the opcodes the money code needs (bsr, dt) and a write log."""

    def __init__(self):
        super().__init__()
        self.writes = set()

    def wn(self, a, v, n):
        for i in range(n):
            self.writes.add((a + i) & M)
        super().wn(a, v, n)

    def exec_op(self, op, pc):
        if (op >> 12) == 0xB:                           # bsr
            disp = op & 0xFFF
            if disp & 0x800:
                disp -= 0x1000
            self.PR = pc + 4
            return ('call', pc + 4 + disp * 2)
        if (op & 0xF0FF) == 0x4010:                     # dt Rn
            n = (op >> 8) & 15
            self.R[n] = (self.R[n] - 1) & M
            self.T = int(self.R[n] == 0)
            return None
        return super().exec_op(op, pc)


def hooks_1st_read(m):
    """the 1ST_READ helpers the ORIGINAL function calls: 0x8c012bf8 r0 = r1 / r0 (signed), 0x8c013460 r0 = r1 % r0,
    0x8c013294 strncpy(r4, r5, r6) (copies up to n bytes, stops at NUL and NUL-pads to n), 0x8c014de4 strlen(r4)."""
    def div(m):
        a, b = sh4sim.s32(m.R[1]), sh4sim.s32(m.R[0])
        q = abs(a) // abs(b)
        m.R[0] = (-q if (a < 0) != (b < 0) else q) & M

    def mod(m):
        a, b = sh4sim.s32(m.R[1]), sh4sim.s32(m.R[0])
        r = abs(a) % abs(b)
        m.R[0] = (-r if a < 0 else r) & M

    def strncpy(m):
        dst, src, n = m.R[4], m.R[5], m.R[6]
        z = False
        for i in range(n):
            c = 0 if z else m.rb(src + i)
            z = z or c == 0
            m.wn(dst + i, c, 1)
        m.R[0] = dst

    def strlen(m):
        a, n = m.R[4], 0
        while m.rb(a + n):
            n += 1
        m.R[0] = n
    m.ext_ret.update({0x8C012BF8: div, 0x8C013460: mod, 0x8C013294: strncpy, 0x8C014DE4: strlen})


def call(m, fn, v, flag, dst=OUT, sentinel=None):
    m.R = [0] * 16
    m.R[15] = STACK
    m.R[4], m.R[5], m.R[6] = dst, v & M, flag
    m.PR = RET
    for i in range(64):
        m.wn(dst + i, 0x55 if sentinel is None else sentinel, 1)
    m.writes = set()
    steps = m.run(fn, RET)
    n = m.R[0]
    return n, bytes(m.rb(dst + i) for i in range(n)), steps


# ------------------------------------------------------------------------------------------------ 1: decode
def norm(t):
    return t.replace(', ', ',').replace(' ', '').lower()


def check_decode():
    print('--- 1: capstone decode of the cave')
    code, items, sym = MP.cave_assembly(MP.CAVE_ADDR, STYLE)
    ins_words = [(a, w, t) for a, w, t in items if not t.startswith('.long')]
    nlong = len(items) - len(ins_words)
    ok = True
    pc_lit = 0
    for a, w, t in ins_words:
        got = list(MD.disasm(w, a))
        if len(got) != 1:
            check(False, 'capstone cannot decode %s at %#x' % (w.hex(), a))
            ok = False
            continue
        i = got[0]
        want = norm(t)
        have = norm('%s %s' % (i.mnemonic, i.op_str))
        # nop assembled by .align padding / explicit nop both print 'nop'
        if have != want:
            check(False, 'cave word %s at %#x: assembler says %r, capstone says %r' % (w.hex(), a, want, have))
            ok = False
    check(ok, 'cave decode')
    check(len(code) <= MP.RESERVE, 'cave size %d within reserve' % len(code))
    # literal table: mova target must be the first .long, 4-aligned
    check(sym['m_pow'] % 4 == 0 and sym['m_pow'] + 40 == MP.CAVE_ADDR + len(code), 'power table is the last 40 bytes, aligned')
    vals = [struct.unpack_from('<I', code, sym['m_pow'] - MP.CAVE_ADDR + 4 * k)[0] for k in range(10)]
    check(vals == [10 ** (9 - k) for k in range(10)], 'power table 10^9..10^0')
    # delay slots
    for k, (a, w, t) in enumerate(ins_words[:-1]):
        op = struct.unpack('<H', w)[0]
        br = (op >> 12) in (0xA, 0xB) or (op & 0xF0FF) in (0x400B, 0x402B) or op == 0x000B or (op >> 8) in (0x8D, 0x8F)
        if br:
            nxt = struct.unpack('<H', ins_words[k + 1][1])[0]
            check(not sh4sim.Machine.illegal_slot(nxt), 'legal delay slot after %s at %#x' % (t, a))
    print('   %d instruction words + %d literals, %d bytes' % (len(ins_words), nlong, len(code)))
    return code, sym


# ------------------------------------------------------------------------------------------------ 2: sites
def check_sites(paths):
    print('--- 2: hook sites (%d files)' % len(paths))
    k0 = MP.read_extracted('1ST_READ.BIN')
    k1 = patch_1st_read(k0)
    cave = cave_bytes()
    o = MP.CAVE_ADDR - MP.IMG_BASE
    lo_ = MP.LIB_ADDR - MP.IMG_BASE if STYLE == 'jp' else None
    libb = MP.lib_bytes() if STYLE == 'jp' else b''
    diff = [i for i in range(o - 16, o + 0x200 + 16) if k1[i] != k0[i]] if lo_ is None else [i for i in range(len(k0)) if k1[i] != k0[i]]
    allowed = set(range(o, o + len(cave))) | (set(range(lo_, lo_ + len(libb))) if lo_ is not None else set())
    if lo_ is not None:
        ln_ = MP.LIBN_ADDR - MP.IMG_BASE
        allowed |= set(range(ln_, ln_ + len(MP.libn_bytes())))
    check(len(k1) == len(k0) and set(diff) <= allowed and k1[o:o + len(cave)] == cave and (lo_ is None or k1[lo_:lo_ + len(libb)] == libb),
          '1ST_READ.BIN differs only inside the cave (and the number-library wrappers)')
    check(not any(k0[o:o + MP.RESERVE]), 'cave area was zero')
    try:
        patch_1st_read(k1)
        check(False, 'a second patch must be refused')
    except MP.MoneyPatchError:
        pass
    n = 0
    for rel in paths:
        d = MP.read_extracted(rel)
        nd, sites = patch_overlay(d, rel)
        check(len(nd) == len(d), '%s same size' % rel)
        if not sites:
            check(nd == d, '%s untouched' % rel)
            continue
        changed = [i for i in range(len(d)) if d[i] != nd[i]]
        want = set()
        for s in sites:
            want |= set(range(s['off'], s['off'] + MP.HOOK_LEN))
            if s.get('dlit') is not None:
                want |= set(range(s['dlit'], s['dlit'] + 4))
            for o in s.get('panel') or []:                          # the compact flag of the info panel call sites (jp, section 8)
                want |= set(range(o, o + 2))
            if STYLE == 'jp' and rel in MP.LIB_SITES:               # the number-library stub (money function + 12, 16 bytes) and the pool words
                want |= set(range(s['off'] + MP.LIB_STUB_REL, s['off'] + MP.LIB_STUB_REL + 16))
                for po, _ in MP.LIB_SITES[rel] + ([MP.LIB_ZERO[rel]] if rel in MP.LIB_ZERO else []):
                    want |= set(range(po, po + 4))
            if STYLE == 'jp' and rel in MP.LIBN_SITES:              # the numeric-format stub (money function + 32, 24 bytes), pool words, digit counter
                want |= set(range(s['off'] + MP.LIBN_STUB_REL, s['off'] + MP.LIBN_STUB_REL + 24))
                sp = MP.LIBN_SITES[rel]
                for po, _ in sp['pools'] + ([sp['counter']] if 'counter' in sp else []):
                    want |= set(range(po, po + 4))
            if STYLE == 'jp' and rel in MP.LIBN_GAME:               # GAME's money text function: the 12 byte hook
                want |= set(range(MP.LIBN_GAME[rel]['off'], MP.LIBN_GAME[rel]['off'] + MP.HOOK_LEN))
        check(set(changed) <= want, '%s changes only the hook bytes, the %%D literal and the panel flag' % rel)
        for s in sites:
            if s.get('dlit') is not None:
                check(struct.unpack_from('<I', nd, s['dlit'])[0] == cave_symbols()['m_dec'], '%s %%D literal is m_dec' % rel)
                check(struct.unpack_from('<I', d, s['dlit'])[0] != cave_symbols()['m_dec'], '%s %%D literal was the full-width function' % rel)
        base = None
        for s in sites:
            n += 1
            h = nd[s['off']:s['off'] + 16]
            ins = list(MD.disasm(h[:8], 0x8C300000 + s['off']))
            txt = [norm('%s %s' % (i.mnemonic, i.op_str)) for i in ins]
            check(txt == ['mov.l0x%08x,r0' % (0x8C300000 + s['off'] + 8), 'jmp@r0', 'nop', 'nop'],
                  '%s hook decodes as mov.l @lit,r0 / jmp @r0 / nop / nop (%s)' % (rel, txt))
            # the literal read by the mov.l at (site&~3)+4+1*4 = site+8
            check(struct.unpack_from('<I', nd, s['off'] + 8)[0] == MP.CAVE_ADDR, '%s literal is the cave address' % rel)
            check(s['off'] % 4 == 0, '%s site aligned' % rel)
            # a second hooking pass finds nothing (the signature is gone) = idempotent refusal to double patch
        check(MP.find_sites(nd, rel) == [], '%s: no site left after patching' % rel)
    print('   %d sites checked' % n)
    return n


# ------------------------------------------------------------------------------------------------ 3: the original function
piece_addrs = MP.piece_addrs


def machine_for(d, base):
    m = Mach()
    m.load(base, d)
    m.native = [(base, base + len(d))]
    hooks_1st_read(m)
    return m


def jp(raw):
    return raw.decode('cp932', 'replace')


def check_original(before):
    print('--- 3: the ORIGINAL function in the interpreter')
    res = {}
    for rel, variant in (('FLOW_PRG/MEETING.BIN', 'A'), ('FLOW_PRG/HOMETOWN.BIN', 'A'), ('FLOW_PRG/SPONSOR.BIN', 'A')):
        d = MP.read_extracted(rel)
        site = [s for s in MP.find_sites(d, rel) if s['variant'] == variant][0]
        import textdb
        base = textdb.load_image(rel).base
        fn = base + site['off']
        pcs = piece_addrs(d, site['off'], base)
        check(len(pcs) == 4, '%s: four unit-string literals found %s' % (rel, [hex(x) for x in pcs]))
        m = machine_for(d, base)
        outs = {}
        for V in (0, 1, 15, 150, 6000, 9999, 10000, 131500, 100300, 815000, 10300):
            n, raw, _ = call(m, fn, V, 0)
            outs[V] = (n, raw)
        # the Japanese text must parse back to the amount
        for V, (n, raw) in outs.items():
            t = jp(raw)
            import re
            t2 = t.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            mm = re.match(r'^(?:(\d+)億)?(?:(\d+)万)?円$|^(\d+)万円$|^0円$', t2)
            val = None
            if t2 == '0円':
                val = 0
            elif mm:
                val = int(mm.group(1) or 0) * 10000 + int(mm.group(2) or mm.group(3) or 0)
            check(val == V, '%s: original prints %r for %d (parsed %r)' % (rel, t, V, val))
        res[rel] = (m, fn, pcs, base, d)
        # English pieces of the first translation (copied with strncpy 2/4/2/3 bytes)
        for nm, adr, txt in zip('u1 u2 u3 u4'.split(), pcs, (b'00M\0', b'0,000 Y\0', b'Y\0', b'Y0\0')):
            for i, c in enumerate(txt):
                m.wn(adr + i, c, 1)
        eng = {}
        for V in (0, 1, 15, 150, 6000, 9999, 10000, 10300, 100300, 131500, 815000):
            n, raw, _ = call(m, fn, V, 0)
            eng[V] = jp(raw)
        if rel.endswith('MEETING.BIN'):
            check(eng[131500] == '130015000,00', 'playtest bug reproduced: 131500 -> %r' % eng[131500])
            check(eng[6000] == '60000,00' and eng[815000] == '810050000,00', 'playtest bug reproduced for 6000 / 815000')
        if before:
            print('   %s variant %s   V (10k yen)  JP pieces | first-translation pieces' % (rel, variant))
            for V in (0, 1, 15, 150, 6000, 9999, 10000, 10300, 100300, 131500, 815000):
                print('      %8d  %-18s | %r' % (V, jp(outs[V][1]), eng.get(V, '-')))
    return res


# ------------------------------------------------------------------------------------------------ 4: the cave
def parse_yen(t):
    """the text of the style under test -> yen, exactly (None if it does not parse, or is not canonical)."""
    import re
    neg = t.startswith('-')
    if neg:
        t = t[1:]
    if STYLE == 'jp':
        if t == '0 Yen':
            return None if neg else 0
        mm = re.match(r'^(?:([1-9]\d*) oku)?( )?(?:([1-9]\d{0,3})( man|m))?$', t)
        if not mm or not (mm.group(1) or mm.group(3)) or bool(mm.group(2)) != bool(mm.group(1) and mm.group(3)):
            return None
        if mm.group(4) == 'm' and not mm.group(1):      # the compact unit only exists behind an oku part
            return None
        y = int(mm.group(1) or 0) * 10 ** 8 + int(mm.group(3) or 0) * 10 ** 4
        return -y if neg else y
    mm = re.match(r'^Y(\d+)(?:\.(\d+))?(k|M|bn)?$', t)
    if not mm:
        return None
    ip, fp, unit = mm.group(1), mm.group(2) or '', mm.group(3)
    scale = {None: 1, 'k': 10 ** 3, 'M': 10 ** 6, 'bn': 10 ** 9}[unit]
    num = int(ip + fp)
    den = 10 ** len(fp)
    if (num * scale) % den:
        return None
    y = num * scale // den
    return -y if neg else y


def sample_values(rng, extra=0, exhaustive=False):
    vals = {0, 1, 2, 9, 10, 15, 50, 99, 100, 101, 110, 150, 999, 1000, 1500, 6000, 9999, 10000, 10001, 12345, 99999, 100000,
            100001, 100050, 100100, 100300, 131500, 815000, 999999, 1000000, 1315000, 99999999, 100000000, 123456789,
            2147483647, 2147483646, 1000000000, 2 ** 31 - 100}
    for L in range(1, 11):
        for _ in range(40 + extra):
            vals.add(rng.randrange(10 ** (L - 1), min(10 ** L, 2 ** 31)))
    for k in range(0, 10):
        vals.add(10 ** k)
        vals.add(10 ** k - 1)
        vals.add(2 * 10 ** k)
    for _ in range(2000 + 10 * extra):
        vals.add(rng.randrange(0, 2 ** 31) // rng.choice((1, 10, 100, 1000, 100000)) * rng.choice((1, 10, 100, 100000)) % 2 ** 31)
    if exhaustive:
        vals.update(range(0, 20001))                                  # every man part of 0, 1 and 2 oku
        for k in range(1, 400):
            vals.update((k * 10000, k * 10000 - 1, k * 10000 + 1, k * 10000 + 1000, k * 10000 + 10))
        for k in range(1, 215000, 997):
            vals.update((k * 10000, k * 10000 + 5000, k * 10000 + 9999, k * 10000 + 100))
        for e in range(0, 10):
            for d in (1, 2, 5, 9):
                for o in (-1, 0, 1):
                    x = d * 10 ** e + o
                    if 0 <= x < 2 ** 31:
                        vals.add(x)
                        vals.add(x * 10000 % 2 ** 31)
        vals.discard(2 ** 31)
    out = sorted(vals)
    out += [-v for v in out if v]
    out.append(-2 ** 31)
    return out


def check_cave(quick):
    print('--- 4: the cave executed (%s)' % ('quick' if quick else 'full'))
    cave = cave_bytes()
    m = Mach()
    m.load(MP.CAVE_ADDR, cave)
    m.native = [(MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
    rng = random.Random(20260511)
    vals = sample_values(rng, 0 if not quick else -35, exhaustive=not quick)
    nb = 0
    maxsteps = 0
    stack_lo = STACK
    for V in vals:
        for flag in ((0, 1, MP.COMPACT_FLAG) if STYLE == 'jp' else (0, 1)):
            if quick and flag and rng.random() > 0.2:
                continue
            m.R = [0] * 16
            # callee-saved registers must come back unchanged
            for r in (7, 8, 9, 10, 11, 12, 13, 14):
                m.R[r] = 0x1000 + r * 0x111
            m.R[15] = STACK
            m.R[4], m.R[5], m.R[6] = OUT, V & M, flag
            m.PR = RET
            for i in range(64):
                m.wn(OUT + i, 0x55, 1)
            m.writes = set()
            saved = list(m.R)
            steps = m.run(MP.CAVE_ADDR, RET)
            maxsteps = max(maxsteps, steps)
            n = m.R[0]
            raw = bytes(m.rb(OUT + i) for i in range(n))
            want = ref(V, flag)
            if raw.decode('ascii', 'replace') != want or n != len(want):
                check(False, 'cave(%d,%d) = %r (n=%d), reference %r' % (V, flag, raw, n, want))
                continue
            for r in (8, 9, 10, 11, 12, 13, 14, 15):
                if m.R[r] != saved[r]:
                    check(False, 'cave(%d,%d) changed r%d' % (V, flag, r))
            if m.PR != RET:
                check(False, 'cave(%d,%d) changed PR' % (V, flag))
            outside = [a for a in m.writes if not (OUT <= a < OUT + n) and not (STACK - 128 <= a < STACK)]
            if outside:
                check(False, 'cave(%d,%d) wrote outside dst/stack: %s' % (V, flag, [hex(a) for a in sorted(outside)[:4]]))
            stack_lo = min(stack_lo, min([a for a in m.writes if a >= STACK - 128] or [STACK]))
            if not flag or STYLE == 'jp':                 # jp ignores the flag
                y = parse_yen(want)
                check(y == V * 10000, 'text %r does not parse back to %d yen (got %r)' % (want, V * 10000, y))
                if STYLE == 'jp':
                    check(len(want) <= 20, 'jp text %r longer than 20 bytes' % want)
                    if flag == MP.COMPACT_FLAG:
                        full = ref(V, 0)
                        both = abs(V) >= 10000 and abs(V) % 10000 != 0
                        check(want == (full.replace(' man', 'm') if both else full) and len(want) == len(full) - (3 if both else 0),
                              'compact %r vs full %r (V=%d)' % (want, full, V))
            else:
                check(want == ('-' if V < 0 else '') + 'Y' + str(abs(V)) + '0000' if V else want == 'Y0', 'flag text %r' % want)
            nb += 1
    print('   %d calls, max %d instructions per call, lowest stack byte written sp-%d' % (nb, maxsteps, STACK - stack_lo))
    dec = cave_symbols()['m_dec']
    nd = 0
    for V in vals:
        m.R = [0] * 16
        for r in (8, 9, 10, 11, 12, 13, 14):
            m.R[r] = 0x3000 + r
        m.R[15] = STACK
        m.R[4], m.R[5], m.R[6], m.R[7] = OUT, V & M, 0, 0x8CF10000
        m.PR = RET
        for i in range(64):
            m.wn(OUT + i, 0x55, 1)
        m.writes = set()
        m.run(dec, RET)
        n = m.R[0]
        raw = bytes(m.rb(OUT + i) for i in range(n)).decode('ascii', 'replace')
        check(raw == str(V) and all(m.R[r] == 0x3000 + r for r in (8, 9, 10, 11, 12, 13, 14)) and m.R[15] == STACK and m.PR == RET,
              'dec(%d) = %r' % (V, raw))
        check(all(OUT <= a < OUT + n or STACK - 16 <= a < STACK for a in m.writes), 'dec(%d) writes' % V)
        nd += 1
    print('   %%D routine: %d calls ok' % nd)
    # width statistics for the translators
    w = [len(ref(V)) for V in vals if V >= 0]
    print('   text width over the sample: max %d, widest for |V| < 1,000,000 (10k yen): %d' % (
        max(w), max(len(ref(V)) for V in vals if 0 <= V < 1000000)))
    if STYLE == 'jp':
        check(max(len(ref(V)) for V in vals) == 20 and ref(-2 ** 31) == '-214748 oku 3648 man', 'jp worst case is INT_MIN, 20 bytes')


# ------------------------------------------------------------------------------------------------ 5: real path
def check_real_path(paths):
    print('--- 5: patched overlay + patched 1ST_READ, original calling convention (%d overlays)' % len(paths))
    k = patch_1st_read(MP.read_extracted('1ST_READ.BIN'))
    cave = k[MP.CAVE_ADDR - MP.IMG_BASE:MP.CAVE_ADDR - MP.IMG_BASE + len(cave_bytes())]
    import textdb
    n = 0
    for rel in paths:
        d = MP.read_extracted(rel)
        nd, sites = patch_overlay(d, rel)
        if not sites:
            continue
        base = textdb.load_image(rel).base
        m = Mach()
        m.load(base, nd)
        m.load(MP.CAVE_ADDR, cave)
        m.native = [(base, base + len(nd)), (MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
        hooks_1st_read(m)
        for s in sites:
            for V, flag in ((131500, 0), (6000, 0), (10300, 0), (0, 0), (15, 0), (-50, 0), (131500, 1), (100050, 0), (2 ** 31 - 1, 0)) + (((131500, MP.COMPACT_FLAG), (10300, MP.COMPACT_FLAG), (6000, MP.COMPACT_FLAG)) if STYLE == 'jp' else ()):
                m.R = [0] * 16
                for r in (8, 9, 10, 11, 12, 13, 14):
                    m.R[r] = 0x2000 + r
                m.R[15] = STACK
                m.R[4], m.R[5], m.R[6] = OUT, V & M, flag
                m.PR = RET
                m.run(base + s['off'], RET)
                nn = m.R[0]
                raw = bytes(m.rb(OUT + i) for i in range(nn)).decode('ascii', 'replace')
                check(raw == ref(V, flag), '%s: hooked function(%d,%d) = %r' % (rel, V, flag, raw))
                check(all(m.R[r] == 0x2000 + r for r in (8, 9, 10, 11, 12, 13, 14)) and m.R[15] == STACK and m.PR == RET,
                      '%s: registers / sp / PR preserved' % rel)
            n += 1
    print('   %d hooked functions executed' % n)


EXPANDER_PREFIX = bytes.fromhex('e62fd62fc62fb62fa62f962f862f224ff47f7827')


def check_expander(paths, quick):
    """the REAL expander (the `%s %d %D %m` function) of every patched overlay, before / after.  Formats are expanded exactly as
    the game does (raw = 0, arguments as consecutive words); the result must equal the Python model.  jp style: also with the `%M` token
    (compact_token=True: `%M` prints the compact form, `%m` and everything else is unchanged) and without it (`%M` prints a literal M)."""
    print('--- 6: the expander %%s %%d %%D %%m (%%M) executed, before and after (%d overlays)' % len(paths))
    import textdb
    k = patch_1st_read(MP.read_extracted('1ST_READ.BIN'))
    cave = k[MP.CAVE_ADDR - MP.IMG_BASE:MP.CAVE_ADDR - MP.IMG_BASE + len(cave_bytes())]
    STR = 0x8CF20000
    FMT = 0x8CF30000
    ARGS = 0x8CF40000
    n = 0
    ntok = 0
    shown = False
    for rel in paths:
        d = MP.read_extracted(rel)
        nd, sites = patch_overlay(d, rel)
        if not sites or sites[0].get('dlit') is None:
            continue
        i = d.find(EXPANDER_PREFIX)
        if i < 0 or d.find(EXPANDER_PREFIX, i + 2) >= 0:
            check(False, '%s: expander prefix found %d times' % (rel, 0 if i < 0 else 2))
            continue
        base = sites[0]['base']          # derived from the literal pool itself, not from textdb's guess
        variants = [('after', nd, False), ('before', d, False)]
        if STYLE == 'jp':
            ndt, sites_t = patch_overlay(d, rel, compact_token=True)
            check(len(ndt) == len(d) and sum(1 for a, b in zip(d, ndt) if a != b) > sum(1 for a, b in zip(d, nd) if a != b), '%s: token edits' % rel)
            variants.append(('token', ndt, True))
        for label, img, tok in variants:
            m = Mach()
            m.load(base, img)
            if label != 'before':
                m.load(MP.CAVE_ADDR, cave)
            m.native = [(base, base + len(img)), (MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
            hooks_1st_read(m)
            for i2, c in enumerate(b'name-text\0'):
                m.wn(STR + i2, c, 1)
            fmt = b'a%Db%dc%sd%m|%D|%d|%m|%%e|%M|%M|%m|%x|%2d'
            for i2, c in enumerate(fmt + b'\0'):
                m.wn(FMT + i2, c, 1)
            for V in ((7, 8, 150, 12, -3, 131500, 0, 10300, 131500, 6000), (12345, -45, 6000, 3, 100, 815000, 2 ** 31 - 1, 100050, 0, 99999999)):
                args = [V[0], V[1], STR, V[2], V[3], V[4], V[5], V[6], V[7], V[8]]
                # %D %d %s %m %D %d %m [%M %M %m]
                for i2, a in enumerate(args):
                    m.wn(ARGS + 4 * i2, a & M, 4)
                m.R = [0] * 16
                m.R[15] = STACK
                m.R[4], m.R[5], m.R[6], m.R[7] = OUT, FMT, ARGS, 0
                m.PR = RET
                try:
                    m.run(base + i, RET)
                except sh4sim.SimError as e:
                    check(False, '%s expander (%s): %s' % (rel, label, e))
                    break
                got = bytearray()
                a = OUT
                while m.rb(a):
                    got.append(m.rb(a))
                    a += 1
                got = bytes(got)
                if label != 'before':
                    # the trailing '%x|%2d' : unknown conversions print the character after the % (no argument is consumed)
                    tail = '|x|2d'
                    if tok:
                        mid = '|%s|%s|%s' % (ref(V[6], MP.COMPACT_FLAG), ref(V[7], MP.COMPACT_FLAG), ref(V[8]))
                    else:
                        mid = '|M|M|%s' % ref(V[6])             # without the token `%M` is the literal M and consumes no argument
                    want = 'a%db%dcname-textd%s|%d|%d|%s|%%e' % (V[0], V[1], ref(V[2]), V[3], V[4], ref(V[5]))
                    want = want.replace('%%e', '%e') + mid + tail
                    check(got.decode('ascii', 'replace') == want, '%s expander %s: %r != %r' % (rel, label, got, want))
                    ntok += tok
                elif not shown and rel.endswith('MEETING.BIN'):
                    print('   before (original bytes, V=%s): %s' % (V, got.decode('cp932', 'replace')))
                    shown = True
        n += 1
        if quick and n >= 3:
            break
    print('   %d expanders executed (%d with the %%M token)' % (n, ntok // 2))


def _notex():
    """an empty textures directory: the texture stage is irrelevant to the money checks (and must not depend on art work in progress)"""
    import tempfile
    return tempfile.mkdtemp(prefix='mc_notex_')


def check_e2e():
    """full pipeline: build_patches(money_fmt=True) on the real translation DB, then every English text with %m / %D / %d / %s
    of every hooked overlay is expanded by the REAL expander of the BUILT overlay (text repacking, hooks, cave all in) and compared
    with the Python model."""
    import re
    import json
    import build_patch as BP
    print('--- 7: end to end (build_patches with the real translations, then the expander on the built overlays)')
    res = BP.build_patches(money_fmt=True, money_style=STYLE, repack=True, share='dup', append_safe=True, prop_font=True,
                           texture_policy='grow', textures_dir=_notex())      # the release flags (docs/pipeline.md); textures do not matter here
    k = res.patches['/1ST_READ.BIN']
    cave = k[MP.CAVE_ADDR - MP.IMG_BASE:MP.CAVE_ADDR - MP.IMG_BASE + len(cave_bytes())]
    check(cave == cave_bytes(), 'built 1ST_READ.BIN carries the cave')
    by_src = BP.load_tdb('translation')
    STR, FMT, ARGS = 0x8CF20000, 0x8CF30000, 0x8CF40000
    tok = re.compile(r'%[sdDm%]')
    n = nrec = 0
    for src, recs in sorted(by_src.items()):
        if not src.startswith(('FLOW_PRG/', 'ATFIRST/')):
            continue
        texts = sorted({r['en'] for r in recs if r.get('en') and '#' not in r['en'] and re.search(r'%[Dm]', r['en'])})
        if not texts:
            continue
        built = res.patches.get('/' + src)
        if built is None:
            continue
        d0 = MP.read_extracted(src)
        sites = MP.find_sites(d0, src)
        if not sites or sites[0]['variant'] != 'A':
            continue
        r0 = MP.find_d_literal(d0, sites[0]['off'])
        if not r0:
            continue
        base = r0[1]
        i = d0.find(EXPANDER_PREFIX)
        m = Mach()
        m.load(base, built)
        m.load(MP.CAVE_ADDR, cave)
        m.native = [(base, base + len(built)), (MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
        hooks_1st_read(m)
        for i2, c in enumerate(b'NAME\0'):
            m.wn(STR + i2, c, 1)
        for text in texts:
            raw = text.encode('ascii')
            for i2, c in enumerate(raw + b'\0'):
                m.wn(FMT + i2, c, 1)
            vals = {'d': 3, 'D': 12, 'm': 131500}
            args, want = [], []
            pos = 0
            for mt in tok.finditer(text):
                want.append(text[pos:mt.start()])
                pos = mt.end()
                c = mt.group(0)[1]
                if c == '%':
                    want.append('%')
                elif c == 's':
                    args.append(STR)
                    want.append('NAME')
                elif c == 'm':
                    args.append(vals['m'])
                    want.append(ref(vals['m']))
                else:
                    args.append(vals[c])
                    want.append(str(vals[c]))
            want.append(text[pos:])
            want = ''.join(want)
            for i2, a in enumerate(args):
                m.wn(ARGS + 4 * i2, a & M, 4)
            m.R = [0] * 16
            m.R[15] = STACK
            m.R[4], m.R[5], m.R[6], m.R[7] = OUT, FMT, ARGS, 0
            m.PR = RET
            try:
                m.run(base + i, RET)
            except sh4sim.SimError as e:
                check(False, '%s: %r: %s' % (src, text[:40], e))
                continue
            got = bytearray()
            a = OUT
            while m.rb(a):
                got.append(m.rb(a))
                a += 1
            check(got.decode('latin-1') == want, '%s: expansion of %r = %r, model %r' % (src, text[:50], bytes(got)[:60], want[:60]))
            nrec += 1
        n += 1
    print('   %d overlays, %d distinct English texts with %%m/%%D expanded by the built overlays' % (n, nrec))


def check_tv_card():
    """TV station card, capital line (FLOW_PRG/TV_EVENT.BIN, docs/number-formats.md s4.4): the private draw_money(V, x, y) at
    0x8c2d0ed0 is replaced; executed here with the text-object constructor 0x8c2d4930 as a Python hook."""
    print('--- 7: TV station card capital routine')
    t = MP.TV_CARD
    rel = t['rel']
    d = MP.read_extracted(rel)
    check(MP.tv_card_sig(d) == MP.TV_CARD_SIG, 'original TV card function has the known signature')
    sites = MP.find_sites(d, rel)
    check(len(sites) == 1, 'TV_EVENT has one money function')
    nd, sites = patch_overlay(d, rel)
    nd2 = MP.patch_tv_card(nd, sites[0]['off'], rel, STYLE)
    check(len(nd2) == len(d), 'same size')
    changed = [i for i in range(len(d)) if nd[i] != nd2[i]]
    check(bool(changed) and min(changed) >= t['fn'] and max(changed) < t['tail_end'], 'changes confined to %#x..%#x' % (t['fn'], t['tail_end']))
    check(all(not (t['fn_end'] <= i < t['tail']) for i in changed), 'literal pool %#x..%#x untouched' % (t['fn_end'], t['tail']))
    try:
        MP.patch_tv_card(nd2, sites[0]['off'], rel, STYLE)
        check(False, 'a second TV card patch must be refused')
    except MP.MoneyPatchError:
        pass
    code, tail, items = MP.tv_card_bytes(t['base'] + sites[0]['off'], STYLE)
    for a, w, text in items:
        if text.startswith('.'):
            continue
        ins = list(MD.disasm(w, a))
        check(len(ins) == 1 and norm('%s %s' % (ins[0].mnemonic, ins[0].op_str)) == norm(text), 'TV card word %#x decodes as %s' % (a, text))
    check(struct.unpack_from('<I', nd2, t['tail'])[0] == t['base'] + sites[0]['off'], 'money function literal')
    k = patch_1st_read(MP.read_extracted('1ST_READ.BIN'))
    cave = k[MP.CAVE_ADDR - MP.IMG_BASE:MP.CAVE_ADDR - MP.IMG_BASE + len(cave_bytes())]
    base = t['base']
    OBJ = 0x8CF10000
    ctor = struct.unpack_from('<I', nd2, t['lit_text'])[0]
    fmt = struct.unpack_from('<I', nd2, t['lit_fmt'])[0]
    seen = []

    def hook(m):
        sp = m.R[15]
        a = sum(m.rb(sp + i) << (8 * i) for i in range(4))
        b = sum(m.rb(sp + 4 + i) << (8 * i) for i in range(4))
        n = 0
        while m.rb(b + n):
            n += 1
        seen.append((a, bytes(m.rb(b + i) for i in range(n)), b))
        m.R[0] = OBJ
    TABLE = [325000, 650000, 2270000, 4410000, 8340000, 9450000]          # 0x8c2d9a54[level]
    vals = [0, 1, 15, 150, 6000, 9999, 10000, 10300, 100050, 131500] + TABLE + [99999999, 2 ** 31 - 1, -2 ** 31]
    X0 = MP.TV_CARD_X_JP if STYLE == 'jp' else 512                      # jp (mn6): compact form from x = 456 so that it ends inside the plate (616)
    for V in vals:
        m = Mach()
        m.load(base, nd2)
        m.load(MP.CAVE_ADDR, cave)
        m.native = [(base, base + len(nd2)), (MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
        hooks_1st_read(m)
        m.ext_ret[ctor] = hook
        for i in range(0x200):
            m.wn(OBJ + i, 0, 1)
        m.R = [0] * 16
        for r in (8, 9, 10, 11, 12, 13, 14):
            m.R[r] = 0x3000 + r
        m.R[15] = STACK
        m.R[4], m.R[5], m.R[6] = V, 512, 148
        m.PR = RET
        del seen[:]
        m.writes = set()
        m.run(base + t['fn'], RET)
        check(len(seen) == 1, 'V=%d: one text object' % V)
        if seen:
            f, txt, buf = seen[0]
            check(f == fmt, 'V=%d: format is the "%%s" record literal' % V)
            check(txt.decode('ascii', 'replace') == ref(V, MP.COMPACT_FLAG if STYLE == 'jp' else 0), 'V=%d: text %r' % (V, txt))
            lim = (9 if abs(V) <= 9450000 else 15) if STYLE == 'western' else (12 if abs(V) <= 9450000 else 20)
            check(len(txt) <= lim, 'V=%d: fits the field / the stack buffer (%r)' % (V, txt))
            check(STACK - 0x40 <= buf < STACK, 'V=%d: buffer on the stack' % V)
            bufsz = 16 if STYLE == 'western' else 32
            check(len(txt) + 1 <= bufsz, 'V=%d: text + NUL within the %d-byte buffer' % (V, bufsz))
        xy = (m.rb(OBJ + 74) | m.rb(OBJ + 75) << 8, m.rb(OBJ + 76) | m.rb(OBJ + 77) << 8)
        check(xy == (X0, 148), 'V=%d: object x,y = %s' % (V, xy))
        check(all(m.R[r] == 0x3000 + r for r in (8, 9, 10, 11, 12, 13, 14)) and m.R[15] == STACK and m.PR == RET, 'V=%d: callee-saved regs / sp / PR preserved' % V)
        check(not any(a for a in m.writes if base <= a < base + len(nd2)), 'V=%d: no write into the overlay image' % V)
    print('   %d values executed' % len(vals))
    if STYLE == 'jp':
        import pixelwidth
        want = {325000: '32 oku 5000m', 650000: '65 oku', 2270000: '227 oku', 4410000: '441 oku', 8340000: '834 oku', 9450000: '945 oku'}
        for V in TABLE:
            check(ref(V, MP.COMPACT_FLAG) == want[V], 'jp TV capital %d = %r' % (V, ref(V, MP.COMPACT_FLAG)))
        wid = {V: pixelwidth.line_px(ref(V, MP.COMPACT_FLAG))[0] for V in TABLE}
        print('   jp TV capital pixel widths (start x=%d): %s' % (X0, ', '.join('%s=%s' % (ref(V, MP.COMPACT_FLAG), wid[V]) for V in TABLE)))
        for V in TABLE:
            if wid[V] is not None:
                check(X0 + wid[V] <= 616, 'jp TV capital %r ends at %d > 616 (plate)' % (ref(V, MP.COMPACT_FLAG), X0 + wid[V]))


def check_panel():
    """the scout info panel (SCDRF / SEARCH): the 4 call sites of the 12 byte salary field.  The code from the money call to the strncpy that
    right-aligns the text is executed in the interpreter on the real bytes (hooked overlay + cave): with the panel patch the field holds the
    compact text right-aligned and the byte BEFORE the field is untouched; without it (panel_compact=False) the 13 byte '1 oku 300 man' overwrites
    the byte before the field (the playtest bug, ' oku 300 man' shown)."""
    print('--- 8: the info panel field (SCDRF / SEARCH, 4 sites)')
    if STYLE != 'jp':
        print('   (jp style only)')
        return
    k = patch_1st_read(MP.read_extracted('1ST_READ.BIN'))
    cave = k[MP.CAVE_ADDR - MP.IMG_BASE:MP.CAVE_ADDR - MP.IMG_BASE + len(cave_bytes())]
    BUF = 0x8CF50000
    nsite = 0
    longest = 0
    for rel in ('FLOW_PRG/SCDRF.BIN', 'FLOW_PRG/SEARCH.BIN'):
        d = MP.read_extracted(rel)
        on, sites = patch_overlay(d, rel)
        off, _ = patch_overlay(d, rel, panel_compact=False)
        panel = sites[0]['panel']
        check(len(panel) == 2, '%s: %d panel sites (2 expected)' % (rel, len(panel)))
        base = sites[0]['base']
        diff = [i for i in range(len(d)) if on[i] != off[i]]
        check(sorted(set(i & ~1 for i in diff)) == sorted(panel) and all(on[i] == MP.MOV_COMPACT_R6 >> 8 * (i & 1) & 0xFF for i in diff),
              '%s: panel edits are exactly the %d `mov #0,r6` halfwords' % (rel, len(panel)))
        for site in panel:
            tail = next(o for o in range(site, site + 40, 2) if MP._match_tail(d, o))
            first = site - 8 if MP._hw(d, site - 8) == 0x6543 else site - 2          # `mov r4,r5` (V in r4) or the pool load (V in r11)
            vreg = 4 if first == site - 8 else 11
            stop = base + tail + 0x14                                              # the `bra` after the strncpy
            for label, img in (('on', on), ('off', off)):
                m = Mach()
                m.load(base, img)
                m.load(MP.CAVE_ADDR, cave)
                m.native = [(base, base + len(img)), (MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
                hooks_1st_read(m)
                for V in (1, 15, 100, 103 * 100, 1030000 // 100, 10300, 13 * 10000 + 1500, 99 * 10000 + 9900, 6000, 10000, 200 * 10000 + 100, 0):
                    for i2 in range(100):
                        m.wn(BUF + i2, 0x41, 1)                                    # 'A' marks every byte
                    for i2 in range(37, 89):
                        m.wn(BUF + i2, 32, 1)
                    m.R = [0] * 16
                    m.R[15] = STACK
                    m.R[14] = BUF
                    m.R[vreg] = V
                    m.PR = RET
                    m.run(base + first, stop)
                    field = bytes(m.rb(BUF + 37 + i2) for i2 in range(12)).decode('ascii')
                    before = chr(m.rb(BUF + 36))
                    text = ref(V, MP.COMPACT_FLAG) if label == 'on' else ref(V, 0)
                    longest = max(longest, len(text)) if label == 'on' else longest
                    if len(text) <= 12:
                        check(field == text.rjust(12) and before == 'A', '%s %s site %#x V=%d: field %r (byte before %r), want %r' % (
                            rel, label, site, V, field, before, text.rjust(12)))
                    else:
                        check(label == 'off' and before == text[len(text) - 13] and field == text[len(text) - 12:], '%s %s site %#x V=%d: overflow case %r %r' % (
                            rel, label, site, V, field, before))
            nsite += 1
    # the compact text of every multiple of 100 man (the unit of the salary: word * 100) below 100 oku fits 12 bytes
    worst = max(len(MP.reference(100 * w, MP.COMPACT_FLAG, 'jp')) for w in range(1, 10000))
    check(worst <= 12, 'compact text of w * 100 man (w < 10000, i.e. below 100 oku) is at most 12 bytes (worst %d)' % worst)
    full = max(len(MP.reference(100 * w, 0, 'jp')) for w in range(1, 10000))
    print('   %d sites executed; compact worst case below 100 oku: %d bytes (full form %d)' % (nsite, worst, full))


def check_libn(LS, quick):
    """9b: the numeric-format wrapper (libn): G_INCOME / ABROAD FIRE PLNUMSET SELNAT / INVEST formats through the patched overlays, GAME's text function."""
    for rel in MP.LIBN_SITES:
        bad, L = LS.check_libn(rel, quick)
        check(bad == 0, '%s: numeric wrapper (%d failures)' % (rel, bad))
    bad = LS.check_game(quick)
    check(bad == 0, 'GAME money text function through n_gm (%d failures)' % bad)
    print('   %d numeric overlays + GAME' % len(MP.LIBN_SITES))


def check_lib(quick):
    """9: the number library (mn6): the wrapper behind the literal-pool word of `real`, executed through the REAL patched overlays (tools/re/mn6_libsim.py):
    synthetic calls (fmt, a1, a2) for every library overlay, and the real library functions F1 / F2a with real amounts (0, 58 man, 3 oku 9000 man, ...)."""
    print('--- 9: the number-library wrapper (9 overlays)')
    if STYLE != 'jp':
        print('   (jp style only)')
        return
    sys.path.insert(0, os.path.join(HERE, 're'))
    import mn6_libsim as LS
    LS.MC = sys.modules[__name__]
    for rel in MP.LIB_SITES:
        bad, L = LS.check_lib(rel, quick)
        check(bad == 0, '%s: wrapper calls (%d failures)' % (rel, bad))
    bad = LS.check_functions(quick)
    check(bad == 0, 'library functions F1 / F2a through the wrapper (%d failures)' % bad)
    check_libn(LS, quick)
    print('   %d overlays, functions %s' % (len(MP.LIB_SITES), 'quick' if quick else 'all'))


def main(argv):
    global STYLE
    quick = '--quick' in argv
    before = '--before' in argv
    styles = list(MP.STYLES)
    for i, x in enumerate(argv):
        if x == '--style':
            styles = [argv[i + 1]] if argv[i + 1] != 'both' else list(MP.STYLES)
    t0 = time.time()
    paths0 = MP.overlay_paths()
    cnt = {'A': 0, 'B': 0}
    for rel in paths0:
        for st in MP.find_sites(MP.read_extracted(rel), rel):
            cnt[st['variant']] += 1
    check(cnt == MP.EXPECTED_SITES, 'site census %s == %s' % (cnt, MP.EXPECTED_SITES))
    check_original(before)
    for style in styles:
        STYLE = style
        print('==== style %s' % style)
        paths = paths0
        check_decode()
        if quick:
            paths = ['FLOW_PRG/MEETING.BIN', 'FLOW_PRG/COMM.BIN', 'FLOW_PRG/HOMETOWN.BIN', 'ATFIRST/HELP.BIN']   # COMM = variant B: left alone
        check_sites(paths)
        check_cave(quick)
        check_real_path(paths if not quick else paths[:3])
        check_expander(paths, quick)
        check_tv_card()
        check_panel()
        check_lib(quick)
        if '--e2e' in argv and style == MP.DEFAULT_STYLE:       # build_patches() builds the default style
            check_e2e()
    print('%s: %d failure(s), %.1fs' % ('moneycheck', len(FAILS), time.time() - t0))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
