"""Patch engine core (docs/patch-engine.md, design: docs/expansion/patch-toolkit.md section 4).  Pure bytes, no emulator.

Three small, independent parts that every code patch (fontpatch, moneypatch, later hooks) is built on:

  CaveRegistry   named regions of 1ST_READ.BIN with start / size / owner, a symbol table, overlap refusal between owners and
                 a zero check against the image being built.  ONE place that knows where font, money and the planned
                 translation bank live (the three used to be hard-coded in three modules and collided at 0x8c299800).
  EditSet        the overlap registry: every spec contributes edits (file, offset, new bytes, owner, expected old bytes);
                 `apply()` checks them against the bytes it is given, REFUSES overlapping edits (different owners always,
                 same owner unless byte-identical) and then writes all of them in one pass.  Sizes never change.
  Family         masked-head site finder: a function is identified by its first 24+ bytes with pc-relative operands masked
                 (mov.l/mov.w @(disp,pc), bsr, ...), optional per-variant masked body hash, alignment and expected copy
                 counts.  One implementation of the mask rule.

    python -I -X utf8 tools/patchengine.py plan       # print the cave plan (also checks it is collision free)
"""
import hashlib
import re
import struct
import sys

IMG_BASE = 0x8C010000                       # 1ST_READ.BIN load address (file offset = address - IMG_BASE)
IMG_NAME = '1ST_READ.BIN'


class EngineError(Exception):
    pass


class _Zero:
    def __repr__(self):
        return 'ZERO'


ZERO = _Zero()                              # Edit.expect sentinel: the old bytes must all be zero (a cave area)


# ------------------------------------------------------------------------------------------------ cave registry
class Cave:
    __slots__ = ('name', 'addr', 'size', 'owner', 'placement', 'planned', 'note')

    def __init__(self, name, addr, size, owner, placement=None, planned=False, note=''):
        self.name, self.addr, self.size, self.owner = name, addr, size, owner
        self.placement, self.planned, self.note = placement, planned, note

    @property
    def end(self):
        return self.addr + self.size

    def overlaps(self, addr, size):
        return self.addr < addr + size and addr < self.end

    def __repr__(self):
        return 'Cave(%s %#x..%#x %s)' % (self.name, self.addr, self.end, self.owner)


class CaveRegistry:
    """Named, non-overlapping regions of the 1ST_READ.BIN tail (and the `gap1` hole).  Two claims may overlap only when they
    belong to the same owner and carry different `placement` tags (= alternative placements of one feature, of which only
    one is ever used: font 'tail' vs 'gap1')."""

    def __init__(self, base=IMG_BASE):
        self.base = base
        self.caves = {}
        self.symbols = {}

    def claim(self, name, addr, size, owner, placement=None, planned=False, note=''):
        if name in self.caves:
            raise EngineError('cave %r is already registered' % name)
        if addr % 4 or size <= 0:
            raise EngineError('cave %r: address %#x must be 4-aligned and size positive' % (name, addr))
        for o in self.caves.values():
            if o.overlaps(addr, size) and not (o.owner == owner and o.placement != placement and None not in (o.placement, placement)):
                raise EngineError('cave %r %#x..%#x collides with %r %#x..%#x' % (name, addr, addr + size, o.name, o.addr, o.end))
        c = self.caves[name] = Cave(name, addr, size, owner, placement, planned, note)
        return c

    def __getitem__(self, name):
        try:
            return self.caves[name]
        except KeyError:
            raise EngineError('unknown cave %r' % name)

    def addr(self, name):
        return self[name].addr

    def size(self, name):
        return self[name].size

    def check_free(self, addr, size, owner, placement=None, ignore=()):
        """refuse an ad-hoc area (a non-default address handed to a patch) that touches another owner's claim, or another
        claim of the same owner with the same placement tag."""
        if addr % 4:
            raise EngineError('area %#x is not 4-aligned' % addr)
        for o in self.caves.values():
            if o.name in ignore or not o.overlaps(addr, size):
                continue
            if o.owner == owner and o.placement is not None and placement is not None and o.placement != placement:
                continue
            raise EngineError('area %#x..%#x collides with cave %r %#x..%#x (%s)' % (addr, addr + size, o.name, o.addr, o.end, o.owner))

    # -- symbols ---------------------------------------------------------------------------------------------------
    def define(self, name, value):
        if name in self.symbols and self.symbols[name] != value:
            raise EngineError('symbol %r already defined as %#x' % (name, self.symbols[name]))
        self.symbols[name] = value

    def define_all(self, prefix, mapping):
        for k, v in mapping.items():
            self.define('%s.%s' % (prefix, k), v)

    def resolve(self, name):
        try:
            return self.symbols[name]
        except KeyError:
            raise EngineError('unresolved symbol %r' % name)

    # -- image access ----------------------------------------------------------------------------------------------
    def check_zero(self, image, name):
        c = self[name]
        o = c.addr - self.base
        if o < 0 or o + c.size > len(image):
            raise EngineError('%#x..%#x lies outside %s' % (c.addr, c.end, IMG_NAME))
        if any(image[o:o + c.size]):
            raise EngineError('area %#x..%#x of %s is not zero (already patched, or used by another stage)' % (c.addr, c.end, IMG_NAME))

    def free_ranges(self, lo, hi):
        """[(start, end)] of [lo, hi) not claimed by any cave (planned claims count as claimed)"""
        spans = sorted((c.addr, c.end) for c in self.caves.values() if c.addr < hi and lo < c.end)
        out, cur = [], lo
        for a, b in spans:
            if a > cur:
                out.append((cur, a))
            cur = max(cur, b)
        if cur < hi:
            out.append((cur, hi))
        return out

    def alloc(self, name, owner, size, lo, hi, align=4, note=''):
        """first-fit allocation of `size` bytes inside [lo, hi) among the unclaimed ranges; claims and returns the Cave"""
        for a, b in self.free_ranges(lo, hi):
            s = (a + align - 1) // align * align
            if s + size <= b:
                return self.claim(name, s, size, owner, note=note)
        raise EngineError('no room for %d bytes (%s) in %#x..%#x' % (size, name, lo, hi))

    def table(self):
        return sorted(self.caves.values(), key=lambda c: (c.addr, c.name))


def default_registry():
    """The authoritative plan of the 1ST_READ.BIN tail (PROVEN zero by tools/re/ptk_tailmap.py: one zero run
    0x8c299400..0x8c2a0000, beyond crt0's BSS end).  Font and money keep their historic addresses (bytes of every build are
    unchanged); the translation bank must start at 'bank'.  'font.gap1.*' is the alternative font placement."""
    r = CaveRegistry()
    r.claim('font.lin', 0x8C299600, 0xC0, 'font', 'tail', note='--lin-center: centres narrow glyphs in the linear text writer (192 B, exactly full); money.lib owns ..0x8c299600, font.cell follows')
    r.claim('font.cell', 0x8C2996C0, 0x40, 'font', 'tail', note='--cell-prop: cell_adv (28 B), the proportional advance of the GAME.BIN commentary line engine; font.align starts 0x8c299700')
    r.claim('font.align', 0x8C299700, 0x100, 'font', 'tail', note='--align-fix: blank-run grid snap + panel width routine (208 B); money.lib owns 0x8c299400..0x8c299600')
    r.claim('font.cave', 0x8C299800, 0x100, 'font', 'tail', note='advance / wrap routine (104 B, 150 B with --prop-scale)')
    r.claim('font.table', 0x8C299900, 0x100, 'font', 'tail', note='256 byte advance table')
    r.claim('font.gap1.cave', 0x8C13BB80, 0x80, 'font', 'gap1', note='alternative placement in the hole between .text and the jump table')
    r.claim('font.gap1.table', 0x8C13BC00, 0x100, 'font', 'gap1')
    r.claim('money.cave', 0x8C299A00, 0x200, 'money', 'tail', note='money formatter (428 B incl. power table)')
    r.claim('bank', 0x8C299C00, 0x8C2A0000 - 0x8C299C00, 'bank', 'tail', planned=True,
            note='planned: translation bank / new hooks (docs/trans-bank.md); must start here, not at 0x8c299800')
    return r


REGISTRY = default_registry()


# ------------------------------------------------------------------------------------------------ edits / overlap registry
class Edit:
    __slots__ = ('file', 'start', 'new', 'owner', 'expect')

    def __init__(self, file, start, new, owner, expect=None):
        self.file, self.start, self.new, self.owner = file, start, bytes(new), owner
        self.expect = expect                         # None | bytes | ZERO

    @property
    def end(self):
        return self.start + len(self.new)

    def __repr__(self):
        return 'Edit(%s %#x..%#x %s)' % (self.file, self.start, self.end, self.owner)


class EditSet:
    """Overlap registry.  Edits are collected from any number of specs; `apply(files)` evaluates all of them against the
    bytes it is given (the ORIGINAL bytes of the files, or the current bytes of an earlier pipeline stage), so the result
    does not depend on the order in which the specs were added."""

    def __init__(self, bases=None):
        self.edits = []
        self.bases = dict(bases or {})               # file -> load address, only used to print addresses in messages

    def add(self, owner, file, start, new, expect=None):
        e = Edit(file, start, new, owner, expect)
        self.edits.append(e)
        return e

    def _where(self, e):
        return '%s %#x..%#x' % (e.file, e.start + self.bases.get(e.file, 0), e.end + self.bases.get(e.file, 0))

    def conflicts(self):
        """[(a, b)] of overlapping edits that must be refused (identical duplicates of one owner are tolerated)"""
        out = []
        by = {}
        for e in self.edits:
            by.setdefault(e.file, []).append(e)
        for lst in by.values():
            lst.sort(key=lambda e: (e.start, e.end))
            for i, a in enumerate(lst):
                for b in lst[i + 1:]:
                    if b.start >= a.end:
                        break
                    if a.owner == b.owner and a.start == b.start and a.new == b.new:
                        continue
                    out.append((a, b))
        return out

    def check(self):
        c = self.conflicts()
        if c:
            raise EngineError('overlapping edits: ' + '; '.join('%s [%s] x %s [%s]' % (self._where(a), a.owner, self._where(b), b.owner)
                                                                  for a, b in c))

    def apply(self, files):
        """files {name: bytes} -> {name: bytes} for every file that has edits.  Nothing is written unless every edit passed:
        no overlaps, in bounds, old bytes as expected (ZERO = all zero).  The result has the size of the input."""
        self.check()
        out = {}
        for e in self.edits:
            if e.file not in files:
                raise EngineError('edit for unknown file %r' % e.file)
            d = files[e.file]
            if e.start < 0 or e.end > len(d):
                raise EngineError('%s lies outside the file (%d bytes)' % (self._where(e), len(d)))
            old = d[e.start:e.end]
            if e.expect is ZERO:
                if any(old):
                    raise EngineError('area %#x..%#x of %s is not zero (already patched, or used by another stage)' % (
                        e.start + self.bases.get(e.file, 0), e.end + self.bases.get(e.file, 0), e.file))
            elif e.expect is not None and bytes(old) != bytes(e.expect):
                raise EngineError('%s [%s]: bytes differ from the expected original' % (self._where(e), e.owner))
        for e in self.edits:
            b = out.get(e.file)
            if b is None:
                b = out[e.file] = bytearray(files[e.file])
            b[e.start:e.end] = e.new
        return {k: bytes(v) for k, v in out.items()}

    def declared(self, file):
        """set of byte offsets of `file` that the edits are allowed to change"""
        s = set()
        for e in self.edits:
            if e.file == file:
                s.update(range(e.start, e.end))
        return s


def changed_offsets(a, b):
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def verify_confined(before, after, es, file):
    """nothing outside the declared edit ranges changed and the size is unchanged (layer L0 of the design)"""
    if len(before) != len(after):
        raise EngineError('%s changed size %d -> %d' % (file, len(before), len(after)))
    decl = es.declared(file)
    bad = [i for i in changed_offsets(before, after) if i not in decl]
    if bad:
        raise EngineError('%s: %d bytes changed outside the declared ranges (first %#x)' % (file, len(bad), bad[0]))


# ------------------------------------------------------------------------------------------------ masks and site families
MASK_RULES = ('none', 'pc', 'pc+bsr', 'branch')


def word_mask(op, rule):
    """16-bit mask of the bits of instruction word `op` that are significant under `rule`:
      none    every bit;   pc  mov.w/mov.l @(disp,pc) (9xxx, Dxxx): displacement ignored;
      pc+bsr  pc plus bsr (Bxxx): 12 bit displacement ignored (the rule of moneypatch);
      branch  pc+bsr plus bra (Axxx) and bt/bf/bt.s/bf.s (89xx 8Bxx 8Dxx 8Fxx), mova (C7xx)."""
    if rule == 'none':
        return 0xFFFF
    hi = op >> 12
    if hi in (0x9, 0xD):
        return 0xFF00
    if hi == 0xB:
        return 0xF000
    if rule == 'branch':
        if hi == 0xA:
            return 0xF000
        if hi == 0x8 and ((op >> 8) & 15) in (9, 0xB, 0xD, 0xF):
            return 0xFF00
        if hi == 0xC and ((op >> 8) & 15) == 7:
            return 0xFF00
    return 0xFFFF


def mask_bytes(b, rule='pc+bsr'):
    """bytes with the insignificant bits zeroed (little-endian 16-bit words; an odd trailing byte is kept)"""
    o = bytearray(b)
    for i in range(0, len(o) - 1, 2):
        w = o[i] | (o[i + 1] << 8)
        w &= word_mask(w, rule)
        o[i], o[i + 1] = w & 0xFF, w >> 8
    return bytes(o)


class Site:
    __slots__ = ('file', 'off', 'variant')

    def __init__(self, file, off, variant):
        self.file, self.off, self.variant = file, off, variant

    def __repr__(self):
        return 'Site(%s %#x %s)' % (self.file, self.off, self.variant)


MIN_MASKED_HEAD = 24                        # a masked head must cover at least this many bytes (the old 12 byte prologues matched look-alikes)
MIN_EXACT_HEAD = 16                         # an exact (rule 'none') template needs at least this many


class Family:
    """A set of byte-identical-modulo-masks functions.
      head      original bytes of the function start, compared under `rule` (>= 24 bytes for a masked rule, >= 16 exact)
      variants  {masked-body hash prefix: variant name} over body_len bytes from the start (None: one anonymous variant); a
                head match whose hash is unknown raises (a damaged or unknown copy must not be patched blindly)
      align     required offset % 4 (the hook literal is pc-relative); a mismatch raises (misaligned='skip': ignores the match)
      expect    int total or {variant: count}, checked by check_count()"""

    def __init__(self, name, head, rule='pc+bsr', variants=None, body_len=None, align=4, expect=None, hash_rule=None, align_off=0, misaligned='raise'):
        head = bytes(head)
        if rule not in MASK_RULES:
            raise EngineError('family %s: unknown mask rule %r' % (name, rule))
        need = MIN_EXACT_HEAD if rule == 'none' else MIN_MASKED_HEAD
        if len(head) < need or len(head) % 2:
            raise EngineError('family %s: head of %d bytes (need an even number >= %d for rule %r)' % (name, len(head), need, rule))
        if variants and not body_len:
            raise EngineError('family %s: variants need body_len' % name)
        self.name, self.head, self.rule, self.variants = name, head, rule, dict(variants or {})
        self.body_len, self.align, self.expect, self.align_off = body_len, align, expect, align_off
        self.misaligned = misaligned          # 'raise' or 'skip' for a head match at the wrong alignment
        self.hash_rule = hash_rule or rule
        self.mhead = mask_bytes(head, rule)
        # anchor: longest run of fully significant words, found with bytes.find (fast), then verified in full
        best, cur = (0, 0), 0
        for i in range(0, len(head), 2):
            op = head[i] | (head[i + 1] << 8)
            if word_mask(op, rule) == 0xFFFF:
                cur += 2
                if cur > best[0]:
                    best = (cur, i + 2 - cur)
            else:
                cur = 0
        if best[0] < 8:
            raise EngineError('family %s: fewer than 8 unmasked bytes in a row, head too vague' % name)
        self._run, self._run_off = head[best[1]:best[1] + best[0]], best[1]

    def head_matches(self, d, i):
        return i >= 0 and i + len(self.head) <= len(d) and mask_bytes(d[i:i + len(self.head)], self.rule) == self.mhead

    def key(self, d, i):
        return hashlib.sha1(mask_bytes(d[i:i + self.body_len], self.hash_rule)).hexdigest()[:10]

    def find(self, d, file=''):
        """[Site] in image `d`, ascending offsets"""
        out, pos = [], 0
        while True:
            j = d.find(self._run, pos)
            if j < 0:
                break
            pos = j + 2
            i = j - self._run_off
            if not self.head_matches(d, i) or (i % 2):
                continue
            if self.variants:
                if i + self.body_len > len(d):
                    continue
                k = self.key(d, i)
                if k not in self.variants:
                    raise EngineError('%s: %s look-alike at %#x with unknown signature %s' % (file, self.name, i, k))
                var = self.variants[k]
            else:
                var = None
            if (i - self.align_off) % self.align:
                if self.misaligned == 'skip':
                    continue
                raise EngineError('%s: site %#x is not %d-aligned' % (file, i, self.align))
            out.append(Site(file, i, var))
        return out

    def check_count(self, counts):
        """counts {variant: n} (or an int) against `expect`; raises EngineError on a difference"""
        if self.expect is None:
            return
        if isinstance(self.expect, int):
            n = counts if isinstance(counts, int) else sum(counts.values())
            if n != self.expect:
                raise EngineError('family %s: expected %d copies, found %d' % (self.name, self.expect, n))
            return
        for v, n in self.expect.items():
            if (counts.get(v, 0) if not isinstance(counts, int) else counts) != n:
                raise EngineError('family %s: expected %d copies of variant %s, found %d' % (self.name, n, v, counts.get(v, 0)))


def scan_family(fam, images):
    """images {file: bytes} -> ([Site], {variant: count}); calls fam.check_count()"""
    sites, cnt = [], {}
    for f in sorted(images):
        for s in fam.find(images[f], f):
            sites.append(s)
            cnt[s.variant] = cnt.get(s.variant, 0) + 1
    fam.check_count(cnt)
    return sites, cnt


def family_tsv(sites):
    return '\n'.join('%s\t%#x\t%s' % (s.file, s.off, s.variant or '') for s in sites)


# ------------------------------------------------------------------------------------------------ hook builders
def hook12(cave_addr):
    """mov.l @(1,pc),r0 / jmp @r0 / nop / nop / .long cave   (site must be 4-aligned: the literal sits at site+8)"""
    return struct.pack('<HHHHI', 0xD001, 0x402B, 0x0009, 0x0009, cave_addr)


def main(argv):
    if len(argv) > 1 and argv[1] == 'plan':
        print('%-16s %-10s %-10s %6s  %-8s %s' % ('name', 'start', 'end', 'size', 'owner', 'note'))
        for c in REGISTRY.table():
            print('%-16s %#010x %#010x %6d  %-8s %s%s' % (c.name, c.addr, c.end, c.size, c.owner, 'PLANNED ' if c.planned else '', c.note))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
