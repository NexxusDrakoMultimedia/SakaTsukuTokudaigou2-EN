"""Self-test of the commentary subtitle speed patch (tools/layoutpatch.py patch_bcast_speed / bcast_patches, docs/layout-issues.md section 14):
python -I -X utf8 tools/test_bcastspeed.py   (a few seconds: it scans all extracted files for the signatures; builds no disc)

The commentary (BCAST) subtitle box of FLOW_PRG/GAME.BIN is a state machine at 0x8c31eee8 (file 0x4eee8) called once per game tick by the manager 0x8c31dd04:
state 0 = reset, state 1 = pick the next queued slot (and FALL THROUGH into state 2 in the same tick), state 2 reads ONE character (only when int(timeline) is
odd), state 3 draws it with `jsr @r13` (r13 = 0x8c3202b0, loaded by the prologue of every tick), states 4 / 5 = '%n' / '%p'.  The original costs about
2.23 ticks per character (the timeline float grows by 1.1 per tick).  The REAL box routine of the REAL GAME.BIN runs in the SH-4 simulator (tools/sh4sim.py plus
the FPU instructions of the slot pick and of the gate, written here; the draw routine 0x8c3202b0 is hooked and records what it is given):
  1. the FIRST version of the patch (site 2 `64 a0` -> `11 a0`, a `bra` straight to the state 3 draw call) is reproduced as a NEGATIVE CONTROL and is shown to
     call 0x8c159000 (a table of function pointers) whenever the first character of a message is read in the tick that picked the slot: state 1 loads
     r13 = 0x8c159000 and falls into state 2, and only the prologue of the next tick puts 0x8c3202b0 back.  This crashed the emulator on the first message
     of every box (prop10g: the pre-match tactics explainer).  The earlier test started in state 2 and never saw it;
  2. the shipped patch (site 2 `64 a0` -> `18 ae`, `bra 0x8c31eefa`: back to the dispatch behind the prologue, which reloads r8..r14 and runs the NORMAL state 3
     code, flag test included) calls ONLY the draw routine, from every start state and timeline phase, draws exactly the characters / '%n' / '%p' of the text
     in order, and for several queued messages;
  3. speed: original 2.23 ticks per character, 1.7 -> 1.33 (1.67x), 1.9 -> 1.15 (1.94x), 2.2 -> 1.00 (2.23x), measured from state 1 (the real start of a message);
  4. isolation: from every state that does not read a character (3, 4, 5, 6, 7, 8, an empty queue) and with the debug flag 0x8c3e3428 set, the patched routine
     does exactly what the original does (same memory writes, same calls); the patched bytes are reachable only from state 2 (no branch of GAME.BIN targets
     them); both signatures are unique over ALL files of extracted/ and the box routine has ONE literal reference (the manager), so the Event / scout message
     typewriter (the tsString library) and every other file are untouched.
Not provable without a boot: the real tick rate and the on-screen look."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import layoutpatch as LP   # noqa: E402
import sh4sim              # noqa: E402

FAILS = []
BASE = 0x8C2D0000            # load address of GAME.BIN
BOXFN = 0x8C31EEE8           # the box update function
B0 = 0x8C4B7B14              # manager base; the box struct is at +0xd8
BOX = B0 + 0xD8
TL = B0 + 0x47E8             # the timeline float
DRAW = 0x8C3202B0            # the draw routine (only the box calls it)
BADTAB = 0x8C159000          # r13 after state 1: a table of function pointers
FLAG = 0x8C3E3428            # the debug flag (nothing in extracted/ writes it)
FABA, FA10 = 0x8C30FABA, 0x8C30FA10
SENT = 0x8C000100
OLD_REDIRECT = bytes.fromhex('11a0')     # the crashing first version of site 2


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        FAILS.append(msg)


def read_ext(rel):
    with open(os.path.join(ROOT, 'extracted', *rel.split('/')), 'rb') as f:
        return f.read()


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class Mach(sh4sim.Machine):
    """sh4sim.Machine plus the FPU instructions of the box routine: fmov.s @(r0,Rm),FRn, ftrc, float, fcmp/gt, lds / sts FPUL (the floats live in the memory model)"""

    def __init__(self):
        super().__init__()
        self.FR = [0.0] * 16
        self.fpul = 0

    def rf(self, a):
        return struct.unpack('<f', struct.pack('<I', self.rn(a, 4)))[0]

    def exec_op(self, op, pc):
        n = (op >> 8) & 15
        m = (op >> 4) & 15
        R = self.R
        if op & 0xF00F == 0xF006:               # fmov.s @(r0,Rm),FRn
            self.FR[n] = self.rf((R[0] + R[m]) & sh4sim.M)
            return None
        if op & 0xF0FF == 0xF03D:               # ftrc FRm,FPUL
            self.fpul = int(self.FR[n]) & sh4sim.M
            return None
        if op & 0xF0FF == 0xF02D:               # float FPUL,FRn
            self.FR[n] = float(sh4sim.s32(self.fpul))
            return None
        if op & 0xF00F == 0xF005:               # fcmp/gt FRm,FRn
            self.T = int(self.FR[n] > self.FR[m])
            return None
        if op & 0xF0FF == 0x005A:               # sts FPUL,Rn
            R[n] = self.fpul
            return None
        if op & 0xF0FF == 0x405A:               # lds Rm,FPUL
            self.fpul = R[n]
            return None
        return super().exec_op(op, pc)


def make(img, slots=(), state=1, tl=0.0, flag=0, junk=False):
    """a box in `state`; slots = [(text bytes, channel, start time)], placed in slot 0, 1, ...  The box code and its literal pools are loaded from `img`."""
    mc = Mach()
    lo, hi = 0x4EDF0, 0x4F500
    mc.load(BASE + lo, img[lo:hi])
    mc.wn(BOX + 1, state, 1)
    mc.wn(TL, struct.unpack('<I', struct.pack('<f', tl))[0], 4)
    for i, (text, ch, start) in enumerate(slots):
        s = BOX + 16 + i * 0x206
        mc.wn(s + 0, ch, 1)
        mc.wn(s + 1, 1, 1)
        mc.wn(s + 2, len(text), 2)
        mc.wn(s + 4, start, 2)
        mc.load(s + 6, text + b'\0\0')
    mc.wn(FLAG, flag, 4)
    mc.log = []                                  # (r5 mode, the two bytes of the character buffer) of every draw call

    def draw(m):
        mc.log.append((m.R[5], bytes(m.rb(m.R[4] + i) for i in range(2))))
        m.R[0] = 1
    mc.ext_ret[DRAW] = draw
    return mc


def tick(mc, t):
    mc.wn(TL, struct.unpack('<I', struct.pack('<f', t))[0], 4)
    mc.R[15] = 0x8CF00000
    mc.PR = SENT
    mc.run(BOXFN, SENT, max_steps=50000)


def play(img, slots, state=1, t0=0.0, dt=1.1, flag=0, max_ticks=1500, want=None):
    """tick the box until `want` draw calls happened (or max_ticks) -> (machine, ticks, set of call targets)"""
    mc = make(img, slots, state, t0, flag)
    t = t0
    k = 0
    for k in range(max_ticks):
        tick(mc, t)
        t = f32(t + dt)
        if want is not None and len(mc.log) >= want:
            break
    return mc, k + 1, {c[0] for c in mc.calls}


def chars(log):
    """the draw log -> the text it spells: ('n' / 'p' for mode 1 / 2, the character bytes otherwise)"""
    out = b''
    for mode, b in log:
        out += b'%n' if mode == 1 else b'%p' if mode == 2 else (b[:1] if b[1:2] == b'\0' else b)
    return out


def writes(mc):
    """the memory the run touched beyond the code image (for the identity checks)"""
    return {a: v for a, v in mc.mem.items() if not (BASE + 0x4EDF0 <= a < BASE + 0x4F500)}


def branch_targets(d):
    """every direct branch target of the GAME.BIN image (bra bsr bt bf bt/s bf/s) plus every 32-bit literal, with the branching address"""
    out = {}
    for o in range(0, len(d) - 1, 2):
        w = d[o] | (d[o + 1] << 8)
        hi = w >> 12
        if hi in (0xA, 0xB):
            disp = w & 0xFFF
            disp -= 0x1000 if disp & 0x800 else 0
            out.setdefault(BASE + o + 4 + disp * 2, []).append(o)
        elif hi == 8 and ((w >> 8) & 15) in (9, 0xB, 0xD, 0xF):
            disp = w & 0xFF
            disp -= 0x100 if disp & 0x80 else 0
            out.setdefault(BASE + o + 4 + disp * 2, []).append(o)
    return out


def main():
    print('== byte level')
    g = read_ext('FLOW_PRG/GAME.BIN')
    check(g.count(LP.BCAST_SIG1) == 1 and g.find(LP.BCAST_SIG1) == LP.BCAST_SITE1 == 0x4F244, 'gate signature a6f33df35a038823018ba0a00900: once, file 0x4f244')
    check(g.count(LP.BCAST_SIG2) == 1 and g.find(LP.BCAST_SIG2) == LP.BCAST_SITE2 == 0x4F2BC, 'draw-return signature 04e005e067a0e18003e064a0e180: once, file 0x4f2bc')
    check(g[0x4F248:0x4F24C] == bytes.fromhex('5a038823') and g[0x4F24E:0x4F250] == bytes.fromhex('a0a0') and g[0x4F2C6:0x4F2C8] == bytes.fromhex('64a0'),
          'original bytes at the sites: 5a 03 88 23 / a0 a0 / 64 a0')
    check(LP.BCAST_REDISPATCH == bytes.fromhex('18ae'), 'site 2 redirect bytes are 18 ae (bra 0x8c31eefa), not the crashing 11 a0')
    # the bra arithmetic, independent of the table above: target = pc + 4 + disp * 2
    w = struct.unpack('<H', LP.BCAST_REDISPATCH)[0]
    disp = (w & 0xFFF) - 0x1000
    check(w >> 12 == 0xA and BASE + 0x4F2C6 + 4 + disp * 2 == 0x8C31EEFA, 'bra at 0x8c31f2c6 -> 0x8c31eefa (decoded: %#x)' % (BASE + 0x4F2C6 + 4 + disp * 2))
    check(g[0x4EEF8:0x4EEFC] == bytes.fromhex('f47f239e'), 'the re-entry 0x8c31eefa is right behind the frame set-up (`add #-12,r15`, then `mov.w 0xd8,r14`): the stack frame is kept')
    want = {'1.7': {0x4F248: '5a0003c8', 0x4F2C6: '18ae'}, '1.9': {0x4F248: '5a0007c8', 0x4F2C6: '18ae'}, '2.2': {0x4F24E: '0900', 0x4F2C6: '18ae'}}
    news = {}
    for sp in ('1.7', '1.9', '2.2'):
        p = LP.patch_bcast_speed(g, sp)
        news[sp] = p
        diff = [i for i in range(len(g)) if g[i] != p[i]]
        exp = set()
        for off, hx in want[sp].items():
            b = bytes.fromhex(hx)
            check(p[off:off + len(b)] == b, '%s: bytes %#x = %s' % (sp, off, hx))
            exp.update(range(off, off + len(b)))
        check(len(p) == len(g) and set(diff) <= exp and 3 <= len(diff) <= 6, '%s: same size, %d bytes differ, all inside the two sites' % (sp, len(diff)))
    off_img = LP.patch_bcast_speed(g, 'off', 'GAME')
    check(off_img == g, "speed 'off' returns the image unchanged (no check, no change)")
    check(LP.bcast_patches(lambda p: g, None, 'off') == {}, "bcast_patches('off') returns nothing")

    print('== unique over the whole extracted tree; the only caller of the box')
    hits = {}
    refs = {}
    for root, _, fs in os.walk(os.path.join(ROOT, 'extracted')):
        for f in fs:
            with open(os.path.join(root, f), 'rb') as fh:
                d = fh.read()
            rel = os.path.relpath(os.path.join(root, f), ROOT).replace('\\', '/')
            for nm, sig in (('gate', LP.BCAST_SIG1), ('return', LP.BCAST_SIG2)):
                c = d.count(sig)
                if c:
                    hits[(rel, nm)] = c
            c = d.count(struct.pack('<I', BOXFN))
            if c:
                refs[rel] = c
    check(hits == {('extracted/FLOW_PRG/GAME.BIN', 'gate'): 1, ('extracted/FLOW_PRG/GAME.BIN', 'return'): 1},
          'both signatures occur exactly once, in FLOW_PRG/GAME.BIN only (%s)' % sorted(hits.items()))
    check(refs == {'extracted/FLOW_PRG/GAME.BIN': 1}, 'the literal 0x8c31eee8 (the box routine) occurs once in extracted/, in GAME.BIN (the manager 0x8c31dd04): %s' % refs)
    targets = branch_targets(g)
    inside = {a: targets.get(a, []) for a in (0x8C31F248, 0x8C31F24A, 0x8C31F2C6, 0x8C31F2C8)}
    check(all(not v for v in inside.values()),
          'no direct branch of GAME.BIN targets a patched instruction (0x8c31f248, 0x8c31f24a, 0x8c31f2c6) or the delay slot of the redirect: %s' % {hex(k): v for k, v in inside.items() if v})
    pool = [o for o in range(0, len(g) - 3, 4) if struct.unpack_from('<I', g, o)[0] in (0x8C31F248, 0x8C31F24A, 0x8C31F2C6, 0x8C31F2C8)]
    check(not pool, 'no 32-bit pointer to a patched instruction exists in GAME.BIN (%s)' % [hex(o) for o in pool])
    loads, stores = 0, 0
    for o in range(0, len(g) - 2, 2):
        w = g[o] | (g[o + 1] << 8)
        if w >> 12 == 0xD:
            pool = ((o + 4) & ~3) + (w & 0xFF) * 4
            if pool + 4 <= len(g) and struct.unpack_from('<I', g, pool)[0] == FLAG:
                rn = (w >> 8) & 15
                nxt = [g[o + k] | (g[o + k + 1] << 8) for k in range(2, 14, 2)]
                loads += any(x & 0xF00F == 0x6002 and (x >> 4) & 15 == rn for x in nxt[:4])       # mov.l @Rn,Rm
                stores += any(x & 0xF00F == 0x2002 and (x >> 8) & 15 == rn for x in nxt)          # mov.l Rm,@Rn
    check(loads >= 28 and stores == 0, 'the debug flag word 0x8c3e3428 is only ever read in GAME.BIN (%d literal loads, each followed by mov.l @Rn,Rm; %d stores through them); no other file holds its address' % (loads, stores))
    other = [rel for rel in os.listdir(os.path.join(ROOT, 'extracted', 'FLOW_PRG')) if rel != 'GAME.BIN' and struct.pack('<I', FLAG) in read_ext('FLOW_PRG/' + rel)]
    check(not other and struct.pack('<I', FLAG) not in read_ext('1ST_READ.BIN'), 'no other FLOW_PRG overlay and not 1ST_READ.BIN contains the address of the debug flag %s' % other)

    print('== NEGATIVE CONTROL: the first version of site 2 (11 a0) is caught by this harness')
    first = bytearray(news['1.9'])
    first[0x4F2C6:0x4F2C8] = OLD_REDIRECT
    first = bytes(first)
    text = b'Hello world, this is it.'
    bad = []
    for t0 in (1.0, 1.1, 2.2, 3.3, 7.7):
        _, _, tg = play(first, [(text, 0, 0)], 1, t0, max_ticks=80)
        if BADTAB in tg:
            bad.append(t0)
    check(bad == [1.0, 1.1, 2.2, 3.3, 7.7], 'first version, message start at timeline %s: `jsr @r13` calls 0x8c159000 (the function pointer table) instead of the draw routine' % bad)
    _, _, tg = play(first, [(text, 0, 0)], 2, 1.0, max_ticks=80)
    check(tg == {DRAW}, 'the same first version started in state 2 (the old test) only ever calls the draw routine: that is why it passed (%s)' % sorted(hex(x) for x in tg))
    first_tab = {k: v for k, v in LP.__dict__.items() if k == 'BCAST_REDISPATCH'}
    check(first_tab['BCAST_REDISPATCH'] != OLD_REDIRECT, 'layoutpatch no longer ships 11 a0')

    print('== simulation: the real box routine, a message queued in a slot (the pre-match tactics explainer / commentary start: state 1 and 0)')
    texts = [b'The quick brown fox jumps over the lazy dog and keeps going for a while.',
             b'Line one%nLine two%pPage two, 100% sure: %x is skipped?',
             b'S\x93\xfa\x96\x7b - two byte characters (Shift-JIS) are read as pairs.']
    images = {'orig': g, '1.7': news['1.7'], '1.9': news['1.9'], '2.2': news['2.2']}
    for sp, img in images.items():
        ok_targets = ok_text = True
        for st in (0, 1):
            for txt in texts:
                exp = b''
                i = 0
                while i < len(txt):
                    c = txt[i]
                    if c == 0x25 and i + 1 < len(txt):
                        if txt[i + 1] in b'np':
                            exp += txt[i:i + 2]
                        i += 2
                        continue
                    if (0x80 <= c <= 0x9F or 0xE0 <= c <= 0xFF) and i + 1 < len(txt):
                        exp += txt[i:i + 2]
                        i += 2
                        continue
                    exp += txt[i:i + 1]
                    i += 1
                for t0 in (0.0, 1.0, 1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7, 8.8):
                    mc, nt, tg = play(img, [(txt, 0, 0)], st, t0, max_ticks=700, want=None)
                    ok_targets &= tg <= {DRAW}
                    got = chars(mc.log)
                    ok_text &= got == exp
                    if got != exp and ok_text is False and len(FAILS) < 5:
                        print('   mismatch', sp, st, t0, got[:60], exp[:60])
        check(ok_targets, 'speed %s: every call of the box (start state 0 and 1, 10 timeline phases, 3 texts) goes to the draw routine 0x8c3202b0 and nothing else' % sp)
        check(ok_text, 'speed %s: the draw calls spell exactly the text (characters, %%n, %%p, two-byte pairs), in order, nothing lost or doubled' % sp)

    print('== several queued messages (the state 1 slot pick runs again after each one)')
    q = [(b'First line of the commentary.', 0, 0), (b'Second line.', 1, 0), (b'Third and last line of the queue!', 0, 0)]
    for sp, img in images.items():
        mc, nt, tg = play(img, q, 1, 0.0, max_ticks=1200)
        spelled = chars(mc.log)
        check(tg <= {DRAW} and spelled == b''.join(x[0] for x in q),
              'speed %s: three queued messages are drawn complete and in queue order, only the draw routine is called (%d ticks)' % (sp, nt))

    print('== speed (ticks per character, from the slot pick: the real start of a message)')
    text = (b'The quick brown fox jumps over the lazy dog and keeps going for a while ' * 2)[:60]
    expect = {'orig': (2.233, 0.07), '1.7': (1.333, 0.07), '1.9': (1.15, 0.07), '2.2': (1.0, 0.07)}
    tpc = {}
    for sp, img in images.items():
        for dt in (1.1, 1.0):
            mc, nt, tg = play(img, [(text, 0, 0)], 1, 0.0, dt, max_ticks=900, want=len(text))
            t = nt / len(text)
            check(chars(mc.log) == text and tg <= {DRAW}, 'speed %s dt %.1f: all %d characters drawn, identical to the input text' % (sp, dt, len(text)))
            if dt == 1.1:
                tpc[sp] = t
                v, tol = expect[sp]
                check(abs(t - v) <= tol, 'speed %s: %.3f ticks per character (expected about %.3f)' % (sp, t, v))
            else:
                check(sp == 'orig' or t <= tpc['orig'] + 0.01, 'speed %s dt 1.0: %.3f ticks per character, not slower than the original' % (sp, t))
    r = {sp: tpc['orig'] / tpc[sp] for sp in ('1.7', '1.9', '2.2')}
    check(1.6 <= r['1.7'] <= 1.78 and 1.85 <= r['1.9'] <= 2.02 and 2.1 <= r['2.2'] <= 2.32,
          'speed-up factors: 1.7 -> %.2fx, 1.9 -> %.2fx, 2.2 -> %.2fx' % (r['1.7'], r['1.9'], r['2.2']))
    long_text = (b'ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789, ' * 3)[:188]
    for sp in ('1.7', '1.9', '2.2'):
        mc, _, tg = play(images[sp], [(long_text, 0, 0)], 1, 0.0, 1.1, max_ticks=900, want=len(long_text))
        check(chars(mc.log) == long_text and tg <= {DRAW}, 'speed %s: a 188 character line (letters, digits, blanks, commas) is drawn in order, nothing lost' % sp)

    print('== isolation: every path that does not read a character is byte-for-byte the original')
    cases = []
    for st in (3, 4, 5, 6, 7, 8, 0x55):
        for fl in (0, 1, 0x8C000000):
            cases.append((st, fl, [(b'Stay put', 0, 0)]))
    cases.append((1, 0, []))
    cases.append((0, 0, []))
    cases.append((1, 0, [(b'not yet', 0, 99)]))        # a slot whose start time lies in the future: nothing is picked
    same = 0
    for st, fl, slots in cases:
        for t0 in (0.0, 1.1, 2.2):
            ref = None
            for sp, img in images.items():
                mc = make(img, slots, st, t0, fl)
                mc.wn(BOX + 6, 3, 2)
                mc.wn(BOX + 4, 40, 2)
                mc.wn(BOX + 12, BOX + 16 + 6, 4)
                tick(mc, t0)
                sig = (writes(mc), [c[:3] for c in mc.calls], mc.log)
                if ref is None:
                    ref = sig
                elif sig != ref:
                    check(False, 'state %#x flag %#x timeline %s: speed %s differs from the original' % (st, fl, t0, sp))
            same += 1
    check(same == len(cases) * 3, 'states 3 4 5 6 7 8 0x55 (flag 0, 1, a pointer), the empty queue, a future slot: %d runs, memory writes and calls equal to the original for 1.7 / 1.9 / 2.2' % same)
    # the debug flag set: the draw routine must not be called by the patched routine (the original never calls it either)
    for sp, img in images.items():
        mc, _, tg = play(img, [(b'flag set', 0, 0)], 1, 1.1, max_ticks=60, flag=1)
        check(DRAW not in tg, 'speed %s with the debug flag set: the draw routine is never called (targets %s)' % (sp, sorted(hex(x) for x in tg)))

    print('== refusals and composition')
    for bad, why in ((news['1.9'], 'already patched (1.9)'), (news['2.2'], 'already patched (2.2)'), (b'\0' * len(g), 'foreign (zero) image'),
                     (g[:LP.BCAST_SITE2 + 10] + b'\0\0' + g[LP.BCAST_SITE2 + 12:], 'one site only'), (g[:100] + b'\0' * 4 + g[100:], 'moved sites'),
                     (first, 'the first (crashing) version')):
        try:
            LP.patch_bcast_speed(bad, '1.9')
            check(False, '%s is refused' % why)
        except LP.LayoutPatchError:
            check(True, '%s is refused' % why)
    try:
        LP.patch_bcast_speed(g, '3.0')
        check(False, 'an unknown speed is refused')
    except LP.LayoutPatchError:
        check(True, 'an unknown speed is refused')
    cur = bytearray(g)
    cur[0x100:0x104] = b'KEEP'
    out = LP.bcast_patches(lambda p: g, {LP.BCAST_ISO: bytes(cur)}, '1.9')
    check(list(out) == [LP.BCAST_ISO] and out[LP.BCAST_ISO][0x100:0x104] == b'KEEP' and out[LP.BCAST_ISO][0x4F248:0x4F24C] == bytes.fromhex('5a0007c8'),
          'composes on the CURRENT bytes (earlier changes kept), returns only GAME.BIN')
    out = LP.bcast_patches(lambda p: g, None, '1.9')
    check(out[LP.BCAST_ISO] == news['1.9'], 'reads the extracted GAME.BIN when no current image exists')

    print('== build wiring (build_patch.apply_bcast_speed)')
    import build_patch as BP
    res = BP.Result()
    BP.apply_bcast_speed(res, 'off')
    check(not res.patches and not res.files, "apply_bcast_speed('off') does nothing")
    for sp in ('1.7', '1.9', '2.2'):
        res = BP.Result()
        BP.apply_bcast_speed(res, sp)
        check(list(res.patches) == [LP.BCAST_ISO] and res.patches[LP.BCAST_ISO] == news[sp] and len(res.files) == 1 and any('bcast speed' in n for n in res.notes),
              'apply_bcast_speed(%s) patches only GAME.BIN and adds a layout report and a note' % sp)
    try:
        BP.apply_bcast_speed(res, '1.9')
        check(False, 'a second application stops the build')
    except BP.PipelineError as e:
        check('bcast speed' in str(e), 'a second application stops the build (PipelineError: %s)' % str(e)[:60])
    try:
        BP.build_patches(only=['NOTHING'], bcast_speed='3.0')
        check(False, 'build_patches refuses an unknown speed')
    except BP.PipelineError as e:
        check('bcast-speed' in str(e), 'build_patches refuses an unknown speed')

    print('\n%d checks failed' % len(FAILS) if FAILS else '\nall checks passed')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
