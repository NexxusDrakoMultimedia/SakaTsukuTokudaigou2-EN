"""ovf: execute the club-name composer of ANY overlay image in the SH-4 simulator (tools/sh4sim.py), many times, with write watching.

    python -I -X utf8 tools/re/ovf_sim.py IMAGE [--all] [--sample N]      IMAGE = a (built) overlay .BIN containing the composer

Harness (class Composer): one Machine with 1ST_READ.BIN loaded once; compose(town, pref, pool, mode) calls the composer of the image
(signature search, like tools/layoutpatch.py) with a canary-filled output area and returns (bytes, writes outside the 14-byte
buffer and outside the stack frame, step count).  sprintf (1ST_READ 0x8c014d80, only %s) is hooked, strlen runs natively.
`python ... IMAGE --all` runs all 1248 x 55 town + word pairs in modes 0 / 1 and the 50 x 55 prefecture + word pairs in modes 2 / 3
and compares with the Python reference rule (`reference`).
"""
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import layoutpatch as LP  # noqa: E402
import sh4sim  # noqa: E402

STRLEN = (0x8c014de4, 0x8c014df2)
SPRINTF = 0x8c014d80
OUT = 0x8d100000
SP = 0x8d200000
N_TOWN, N_PREF, N_POOL = 1248, 50, 55


class WatchMem(dict):
    """sparse memory that records the addresses stored to while `log` is a list"""
    log = None

    def __setitem__(self, k, v):
        if self.log is not None:
            self.log.append(k)
        dict.__setitem__(self, k, v)


class Machine(sh4sim.Machine):
    def __init__(self):
        super().__init__()
        self.mem = WatchMem()

    def exec_op(self, op, pc):
        if op >> 12 == 0xB and not hasattr(sh4sim.Machine, '_has_bsr'):
            return super().exec_op(op, pc)
        return super().exec_op(op, pc)


def cstr_at(m, a):
    out = bytearray()
    while True:
        b = m.rb(a + len(out))
        if b == 0:
            return bytes(out)
        out.append(b)


def reference(short, word, word_first, dot=True, room=None):
    """the documented rule (docs/layout-issues.md section 9)"""
    room = LP.CLUB_ROOM if room is None else room
    lw = len(word)
    cap = max(room - lw, LP.CLUB_MIN_TOWN)
    if len(short) > cap:
        short = short[:cap - 1] + b'.' if dot else short[:cap]
    word = word[:min(lw, room - len(short))]
    return word + b' ' + short if word_first else short + b' ' + word


class Composer:
    def __init__(self, image, first=None):
        self.image = image
        if first is None:
            first = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
        d = image
        a = d.find(LP.CLUB_SIG_A)
        if a < 0:
            a = d.find(LP.CLUB_SIG_A_NEW)                # the patched signature (town_short without the cut)
        if a < 0:
            raise ValueError('town_short signature not found')
        self.c = a + LP.COMP_DELTA
        fmt_off = d.find(b'%s %s\0\0\0Ille')
        if fmt_off < 0:
            fmt_off = d.find(b'%s%s\0\0\0\0Ille')
        lit = struct.unpack_from('<I', d, a + LP.CLUB_FMT_DELTA)[0]
        self.base = lit - fmt_off
        self.comp = self.base + self.c
        m = Machine()
        m.load(0x8c010000, first)
        m.load(self.base, image)
        m.native = [(self.base, self.base + len(image))]
        # the library calls are taken from the composer's own literal pool (slot 0x828 sprintf, 0x82c strlen) and hooked in Python:
        # CSAVE3.BIN is linked against another 1ST_READ build (docs/font-hook-notes.md), its slots point at other addresses
        sprintf_at = struct.unpack_from('<I', image, self.c + 0xfe)[0]
        strlen_at = struct.unpack_from('<I', image, self.c + LP.COMP_L_STRLEN)[0]
        m.ext_ret[sprintf_at] = self._sprintf
        m.ext_ret[strlen_at] = self._strlen
        m.mem.log = None
        self.m = m
        self.pool_tbl = struct.unpack_from('<I', d, self.c + LP.COMP_L_POOLTBL)[0] - self.base
        self.town_tbl = struct.unpack_from('<I', d, self.c + LP.COMP_L_TOWNTBL)[0] - self.base
        self.pref_tbl = struct.unpack_from('<I', d, self.c + LP.COMP_L_PREFTBL)[0] - self.base

    @staticmethod
    def _strlen(mm):
        mm.R[0] = len(cstr_at(mm, mm.R[4]))

    @staticmethod
    def _sprintf(mm):
        sp = mm.R[15]
        fmt = cstr_at(mm, mm.rn(sp, 4))
        args = [mm.rn(sp + 4 + 4 * i, 4) for i in range(4)]
        res = bytearray()
        k = i = 0
        while i < len(fmt):
            if fmt[i:i + 2] == b'%s':
                res += cstr_at(mm, args[k])
                k += 1
                i += 2
            else:
                res.append(fmt[i])
                i += 1
        for j, b in enumerate(bytes(res) + b'\0'):
            mm.mem[(mm.R[4] + j) & 0xFFFFFFFF] = b
        mm.R[0] = len(res)

    def word(self, i):
        return cstr_at(self.m, self.base + struct.unpack_from('<I', self.image, self.pool_tbl + 4 * i)[0] - self.base)

    def tables(self):
        d = self.image

        def tab(t, n, first):
            return [cstr_at(self.m, struct.unpack_from('<I', d, t + 4 * k)[0]) for k in range(first, first + n)]
        return tab(self.town_tbl, N_TOWN, 1), tab(self.pref_tbl, N_PREF, 0), tab(self.pool_tbl, N_POOL, 0)

    def compose(self, town, pref, pool, mode):
        m = self.m
        for i in range(48):
            m.mem[OUT + i] = 0xAA
        m.R = [0] * 16
        m.R[15] = SP
        m.wn(SP, OUT, 4)
        m.R[4], m.R[5], m.R[6], m.R[7] = town & 0xFFFFFFFF, pref & 0xFFFFFFFF, pool & 0xFFFFFFFF, mode & 0xFFFFFFFF
        m.PR = 0x8c000010
        m.mem.log = []
        steps = m.run(self.comp, 0x8c000010)
        log = m.mem.log
        m.mem.log = None
        bad = sorted({a for a in log if not (OUT <= a < OUT + 14 or SP - 0x180 <= a < SP + 0x20)})
        canary = [i for i in range(14, 48) if m.mem.get(OUT + i) != 0xAA]
        return cstr_at(m, OUT), m.R[0], bad, canary, steps, m.R[15] == SP


class Popup(Composer):
    """HOMETOWN's candidate popup: the four library sprintf("%s %s", a, b) calls go through the join entry that replaces the (dead) composer
    copy.  join(a, b) runs it with the sprintf calling convention (r4 = destination, @sp = format, @sp+4 = a, @sp+8 = b)."""

    def __init__(self, image, first=None):
        super().__init__(image, first)
        d = image
        fmt = d.find(b'%s %s\0\0\0%d selected\0')
        if fmt < 0:
            raise ValueError('inline popup format not found (build without the guard?)')
        lit = LP._word_offs(d, self.base + fmt)
        if len(lit) != 1:
            raise ValueError('popup format literal')
        self.lit_fmt = lit[0]
        self.word_ptr = struct.unpack_from('<I', d, lit[0] - 4)[0]
        self.lit_sprintf = struct.unpack_from('<I', d, lit[0] + 4)[0]

    def join(self, a, b, word, dest_size=14):
        """a, b = the two stack strings (bytes); `word` = which one is the club word buffer ('a' or 'b')"""
        m = self.m
        ta, tb = 0x8d300000, 0x8d300100
        wa = ta if word == 'a' else tb
        ra = self.word_ptr if word == 'a' else ta
        rb = self.word_ptr if word == 'b' else tb
        strings = {}
        if word == 'a':
            strings = {self.word_ptr: a, tb: b}
        else:
            strings = {ta: a, self.word_ptr: b}
        for addr, st in strings.items():
            for i, ch in enumerate(st + b'\0'):
                m.mem[addr + i] = ch
        for i in range(48):
            m.mem[OUT + i] = 0xAA
        m.R = [0] * 16
        m.R[15] = SP
        m.wn(SP, self.base + self.lit_fmt, 4)
        m.wn(SP + 4, ra if word == 'a' else ta, 4)
        m.wn(SP + 8, rb if word == 'b' else tb, 4)
        m.R[4] = OUT
        m.PR = 0x8c000010
        m.mem.log = []
        steps = m.run(self.comp, 0x8c000010)
        log = m.mem.log
        m.mem.log = None
        bad = sorted({x for x in log if not (OUT <= x < OUT + 14 or SP - 0x180 <= x < SP + 0x20)})
        canary = [i for i in range(14, 48) if m.mem.get(OUT + i) != 0xAA]
        sp_ok = m.R[15] == SP and all(cstr_at(m, addr) == st for addr, st in strings.items())     # also: the caller's strings are untouched
        return cstr_at(m, OUT), m.R[0], bad, canary, steps, sp_ok


def synth_english(image, towns=None, prefs=None, pool=None):
    """image + an appended block of English strings, with pointer-table entries repointed (only the simulator image grows).
    Defaults: town 1223 Kagoshima, prefectures 46 Kagoshima / 14 Izu Is. / 13 Kanagawa, club words 46 Mythos / 11 Shadows."""
    c = Composer(image)
    d = bytearray(image)
    block = bytearray()
    start = (len(d) + 3) & ~3
    d += b'\0' * (start - len(d))

    def put(tbl, idx, text):
        nonlocal block
        struct.pack_into('<I', d, tbl + 4 * idx, c.base + start + len(block))
        block += text + b'\0'
    for idx, t in (towns or {1223: b'Kagoshima'}).items():
        put(c.town_tbl, idx, t)
    for idx, t in (prefs or {46: b'Kagoshima', 14: b'Izu Is.', 13: b'Kanagawa'}).items():
        put(c.pref_tbl, idx, t)
    for idx, t in (pool or {46: b'Mythos', 11: b'Shadows'}).items():
        put(c.pool_tbl, idx, t)
    return bytes(d + block)


def pref_short(idx, name):
    """pref_short after the layoutpatch: 'Izu Is.' / 'Amami Is.' (idx 14 / 48) lose 4 characters, everything else is kept"""
    return name[:-4] if idx in (14, 48) and len(name) >= 2 else name


def check_one(comp, kind, idx, w, mode, towns, prefs, pool, dot, problems):
    """one composer run + reference comparison; -> (result bytes, truncated?)"""
    out, ret, bad, canary, steps, sp_ok = comp.compose(idx if kind == 'town' else 0, idx if kind == 'pref' else 0, w, mode)
    short = towns[idx - 1] if kind == 'town' else pref_short(idx, prefs[idx])
    want = reference(short, pool[w], bool(mode & 1), dot)
    tag = (kind, idx, w, mode)
    if bad:
        problems.append(('write outside the 14 byte buffer / frame', tag, [hex(x) for x in bad[:4]]))
    if canary:
        problems.append(('canary overwritten beyond byte 14', tag, canary[:4]))
    if len(out) > 13 or ret != len(out):
        problems.append(('length', tag, len(out), ret))
    if comp.m.mem.get(OUT + len(out)) != 0:
        problems.append(('no NUL', tag))
    if out != want:
        problems.append(('differs from the reference rule', tag, out, want))
    if not sp_ok:
        problems.append(('stack not balanced', tag))
    return out, len(short) > max(LP.CLUB_ROOM - len(pool[w]), LP.CLUB_MIN_TOWN)


def run_all(comp, dot=True, verbose=True):
    towns, prefs, pool = comp.tables()
    problems = []
    cut = Counter()
    lens = Counter()
    cut_by_word = Counter()
    examples = []
    n = 0
    for t in range(1, len(towns) + 1):
        for w in range(len(pool)):
            for mode in (0, 1):
                out, trunc = check_one(comp, 'town', t, w, mode, towns, prefs, pool, dot, problems)
                n += 1
                if mode == 0:
                    lens[len(out)] += 1
                    if trunc:
                        cut['town'] += 1
                        cut_by_word[pool[w]] += 1
                        if len(examples) < 400:
                            examples.append((towns[t - 1], pool[w], out))
    pc = Counter()
    for p in range(0, 49):
        for w in range(len(pool)):
            for mode in (2, 3):
                out, trunc = check_one(comp, 'pref', p, w, mode, towns, prefs, pool, dot, problems)
                n += 1
                if mode == 2:
                    pc['pairs'] += 1
                    pc['cut'] += trunc
    return dict(runs=n, problems=problems, cut=cut, lens=lens, cut_by_word=cut_by_word, examples=examples, pref=pc,
                towns=towns, prefs=prefs, pool=pool)


def robustness(comp):
    """out-of-range arguments must not break the bound either (the original composer printed an error and kept going)"""
    problems = []
    for town in (0, -1, 1, 1248, 1249, 5000, 0x7fffffff):
        for pref in (-1, 0, 14, 48, 49, 100):
            for pool in (-1, 0, 1, 54, 55, 56, 1000):
                for mode in (0, 1, 2, 3, 4, 5, 7, -1):
                    out, ret, bad, canary, steps, sp_ok = comp.compose(town, pref, pool, mode)
                    if bad or canary or len(out) > 13 or ret != len(out) or not sp_ok:
                        problems.append((town, pref, pool, mode, out, ret, bad[:2], canary[:2]))
    return problems


def popup_mode(image):
    """-> Popup when the image's sprintf literal of the candidate popup points at the composer address (HOMETOWN with the guard), else None"""
    try:
        p = Popup(image)
    except ValueError:
        return None
    return p if p.lit_sprintf == p.comp else None


def run_all_popup(pj, dot=True):
    """HOMETOWN's popup join over all 1248 x 55 municipality + word pairs and all 49 x 55 prefecture + word pairs, both orders"""
    towns, prefs, pool = pj.tables()
    problems = []
    cut = Counter()
    lens = Counter()
    cut_by_word = Counter()
    examples = []
    n = 0
    items = [('town', t, towns[t - 1]) for t in range(1, len(towns) + 1)] + [('pref', p, pref_short(p, prefs[p])) for p in range(0, 49)]
    for kind, idx, short in items:
        for w, word in enumerate(pool):
            for word_first in (False, True):
                r = pj.join(word, short, 'a') if word_first else pj.join(short, word, 'b')
                n += 1
                want = reference(short, word, word_first, dot)
                if r[0] != want or r[2] or r[3] or not r[5] or len(r[0]) > 13 or r[1] != len(r[0]):
                    problems.append((kind, idx, w, word_first, r[0], want, r[2][:2], r[3][:2]))
                if not word_first:
                    trunc = len(short) > max(LP.CLUB_ROOM - len(word), LP.CLUB_MIN_TOWN)
                    if kind == 'town':
                        lens[len(r[0])] += 1
                        if trunc:
                            cut['town'] += 1
                            cut_by_word[word] += 1
                            if len(examples) < 400:
                                examples.append((short, word, r[0]))
                    else:
                        cut['pref_pairs'] += 1
                        cut['pref'] += trunc
    return dict(runs=n, problems=problems, cut=cut, lens=lens, cut_by_word=cut_by_word, examples=examples, towns=towns, prefs=prefs, pool=pool)


def main():
    import argparse
    import random
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--all', action='store_true', help='all 68,640 town + word pairs (modes 0, 1) and all prefecture pairs (modes 2, 3)')
    ap.add_argument('--sample', type=int, default=0, help='N random pairs of all four modes')
    ap.add_argument('--nodot', action='store_true')
    ap.add_argument('--robust', action='store_true')
    a = ap.parse_args()
    image = open(a.image, 'rb').read()
    pj = popup_mode(image)
    comp = pj or Composer(image)
    towns, prefs, pool = comp.tables()
    print('%s at %#x, base %#x, %d towns %d prefs %d words' % ('POPUP JOIN (HOMETOWN)' if pj else 'composer', comp.comp, comp.base, len(towns), len(prefs), len(pool)))
    t0 = time.time()
    if pj and (a.sample or a.robust):
        print('(--sample / --robust apply to the composer overlays; this image is HOMETOWN with the popup join)')
        a.sample = 0
        a.robust = False
    if a.all:
        r = run_all_popup(pj, not a.nodot) if pj else run_all(comp, not a.nodot)
        r['pref'] = r.get('pref') or Counter({'pairs': r['cut']['pref_pairs'] // 1, 'cut': r['cut']['pref']})
        print('%d runs in %.0f s, problems: %d' % (r['runs'], time.time() - t0, len(r['problems'])))
        for p in r['problems'][:10]:
            print('  PROBLEM', p)
        print('town + word pairs needing a cut: %d of %d (%.1f %%)' % (r['cut']['town'], len(towns) * len(pool), 100.0 * r['cut']['town'] / (len(towns) * len(pool))))
        print('prefecture + word pairs needing a cut: %d of %d' % (r['pref']['cut'], r['pref']['pairs']))
        print('result length histogram (mode 0):', sorted(r['lens'].items()))
        print('cuts by club word (top):', r['cut_by_word'].most_common(8))
        for t, w, o in r['examples'][:6] + r['examples'][len(r['examples']) // 2:len(r['examples']) // 2 + 6]:
            print('   %-12s + %-9s -> %s' % (t.decode(), w.decode(), o.decode()))
    if a.sample:
        rnd = random.Random(1)
        problems = []
        for _ in range(a.sample):
            kind = rnd.choice(['town', 'pref'])
            w = rnd.randrange(len(pool))
            if kind == 'town':
                check_one(comp, kind, rnd.randrange(1, len(towns) + 1), w, rnd.choice([0, 1]), towns, prefs, pool, not a.nodot, problems)
            else:
                check_one(comp, kind, rnd.randrange(0, 49), w, rnd.choice([2, 3]), towns, prefs, pool, not a.nodot, problems)
        print('%d random runs, problems: %d' % (a.sample, len(problems)), problems[:3])
    if a.robust:
        pr = robustness(comp)
        print('robustness (out-of-range arguments): %d problems' % len(pr), pr[:3])


if __name__ == '__main__':
    main()
