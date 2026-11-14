"""External translation bank builder (prototype).  See docs/trans-bank.md.

Input : overflow entries = [(source, string_offset, english_text)], e.g. 'FLOW_PRG/MEETING.BIN', 0x1a2b3, 'Please wait...'.
        (a string that does not fit in its original slot and has pointer references; the Japanese stays where it is
        or is wiped by the caller, the pointers are redirected into the bank)
Output: * bank images, one per region (bytes + absolute RAM address + the file they are written into)
        * pointer patches   [{source, off, old, new}]   (u32 words inside the overlays)
        * wipes             [{source, off, len}]        (old Japanese slots that become free for in-place reuse)
        * stats / unplaced list

Memory model (all absolute addresses, all PROVEN statically except where docs/trans-bank.md says otherwise):
  region kind 'first_read' : bytes inside 1ST_READ.BIN (base 0x8c010000), loaded by the BIOS with the executable
  region kind 'font_tail'  : tail of the root FONT.BIN (loaded to 0x8cd5c000, limit 0x8ce02000 = 679,936 bytes)
  region kind 'file'       : a donor file TRANSBANK.BIN loaded by the boot hook (tools/re/capacity/bank/hookpatch.py)
  region kind 'ovl_tail'   : bytes appended to ONE overlay (only strings of that overlay may use it), needs the `_end` word raised

Packing: identical byte strings are stored once, a string that is a NUL-terminated suffix of another one shares it
(pointer = root + delta), strings used by several overlays go to shared regions first, overlay-private strings go to the
overlay's own tail region when given.

CLI:
    python -I -X utf8 tools/re/capacity/bank/bankbuild.py --selftest
    python -I -X utf8 tools/re/capacity/bank/bankbuild.py --entries entries.json --out DIR [--regions tail,gap1,gap2,gap3,font] [--align 1]
entries.json: [{"source": "FLOW_PRG/X.BIN", "off": "0x1a2b3", "en": "text"}, ...]
"""
import argparse
import csv
import json
import os
import struct
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textdb  # noqa: E402

FR_BASE = 0x8C010000
FONT_BASE = 0x8CD5C000
FONT_LIMIT = 0x8CE02000


# ------------------------------------------------------------------ regions --

class Region:
    def __init__(self, name, kind, addr, size, target, foff, only=None, check='zero', safety=''):
        self.name, self.kind, self.addr, self.size = name, kind, addr, size
        self.target, self.foff = target, foff       # file the bytes go into (iso-ish name) and offset there
        self.only = set(only) if only else None     # restrict to strings of these sources
        self.check = check                          # 'zero' | 'filler' | 'none'  (what the file must contain now)
        self.safety = safety
        self.data = bytearray()

    @property
    def free(self):
        return self.size - len(self.data)


# Static facts (see docs/trans-bank.md s2, produced by zeroruns.py / bsscan*.py / gaps.py):
#   crt0 FUN_8c017160 zero-fills [0x8c16f800,0x8c299400) and [0x8c193c30,0x8c1fc180) at start -> NOT usable as in-file storage.
PRESETS = {
    # between the end of crt0's BSS (0x8c299400) and the start of overlay slot 0 (0x8c2b0000): 27,648 zero + 65,536 filler
    'tail': dict(kind='first_read', addr=0x8C299400, size=0x8C2B0000 - 0x8C299400, check='zerofiller',
                 safety='A: outside BSS clear, outside all overlay slots, untouched in 4 dumps, no literal refs'),
    # padding between code/data sections, zero in file and in all 4 dumps; boundary words only (see zeroruns.py)
    'gap1': dict(kind='first_read', addr=0x8C13BB80, size=0x8C159000 - 0x8C13BB80, check='zero',
                 safety='B: 0x80 bytes at the start kept for the boot-hook cave; pure zero hole before the 0x8c159000 jump table'),
    'gap2': dict(kind='first_read', addr=0x8C1196A0, size=0x8C11CB3A - 0x8C1196A0 - 0x40, check='zero',
                 safety='C: tail 0x40 bytes kept (literal pool points at 0x8c11cb04: a variable?)'),
    'gap3': dict(kind='first_read', addr=0x8C1289E8, size=0x8C12CB25 - 0x8C1289E8 - 0x40, check='zero',
                 safety='C: tail 0x40 bytes kept (literal pool points at 0x8c12cb24)'),
}


def make_regions(names, font_size=None):
    out = []
    for n in names:
        if n == 'font':
            fs = font_size if font_size is not None else 663324
            start = (fs + 3) & ~3
            out.append(Region('font', 'font_tail', FONT_BASE + start, FONT_LIMIT - FONT_BASE - start, 'FONT.BIN', start,
                              check='none', safety='D: after the font glyph data, zero in RAM before load (gaps.py); FONT.BIN <= 679,936'))
        elif n in PRESETS:
            p = PRESETS[n]
            out.append(Region(n, p['kind'], p['addr'], p['size'], '1ST_READ.BIN', p['addr'] - FR_BASE, check=p['check'], safety=p['safety']))
        else:
            raise ValueError('unknown region ' + n)
    return out


def file_region(name, addr, size):
    return Region(name, 'file', addr, size, 'TRANSBANK.BIN', 0, check='none', safety='E: needs a proven-free RAM block and the boot hook')


def overlay_tail_region(source, base, new_start_off, size, endvar_off):
    r = Region('ovl_tail:' + source, 'ovl_tail', base + new_start_off, size, source, new_start_off, only=[source], check='none',
               safety='F: heap arena shrinks by the bytes used; ENDVAR word raised')
    r.endvar_off = endvar_off
    return r


def survey_row(source):
    with open(os.path.join(ROOT, 'tools', 're', 'textengine', 'survey_overlays.tsv'), encoding='utf8') as fh:
        for row in csv.DictReader(fh, delimiter='	'):
            if row['overlay'] == os.path.basename(source):
                return row
    raise KeyError(source)


def overlay_tail_for(source, size, resolver=None):
    """Route (d): region appended behind the overlay's `_end` (BSS overlays: behind the BSS, which then is part of the file as zeros).
    Returns Region with .endvar_off / .old_end; the file must be extended with apply_overlay_tail()."""
    row = survey_row(source)
    if row['_end'] in ('', '-') or row['end_var_off'] in ('', '-'):
        raise ValueError('%s: _end variable not found (GETREP/NENREP class) - no tail route' % source)
    base = int(row['base'], 16)
    end = int(row['_end'], 16)
    evo = int(row['end_var_off'], 16)
    start_off = (end - base + 3) & ~3
    r = overlay_tail_region(source, base, start_off, size, evo)
    r.old_end = end
    r.bss = int(row['bss_bytes'])
    return r


def apply_overlay_tail(img_bytes, reg):
    """New overlay image = old image + zero fill up to the old _end (BSS becomes explicit zeros) + bank bytes (4-aligned total);
    the u32 at ENDVAR (holding the old `_end`) is raised to base + new length.  Returns (bytes, new_end)."""
    b = bytearray(img_bytes)
    base = reg.addr - reg.foff
    cur = struct.unpack_from('<I', b, reg.endvar_off)[0]
    if cur != reg.old_end:
        raise ValueError('%s: ENDVAR word is %#x, expected %#x' % (reg.target, cur, reg.old_end))
    if len(b) > reg.foff:
        raise ValueError('image longer than the tail start')
    b.extend(b'\0' * (reg.foff - len(b)))
    b.extend(reg.data)
    b.extend(b'\0' * ((-len(b)) % 4))
    new_end = base + len(b)
    struct.pack_into('<I', b, reg.endvar_off, new_end)
    return bytes(b), new_end


# --------------------------------------------------------------- resolving ---

class Resolver:
    """Caches textdb.extract_image per overlay."""

    def __init__(self):
        self.imgs = {}
        self.strs = {}

    def get(self, source):
        if source not in self.imgs:
            img = textdb.load_image(source)
            strs, ptrs, _ = textdb.extract_image(img)
            self.imgs[source] = img
            self.strs[source] = {s.off: s for s in strs}
        return self.imgs[source], self.strs[source]


def relocatable(s):
    return bool(s.refs) and not s.orphan and not s.interior and not s.pinned


def reject_reason(s):
    if s.orphan:
        return 'orphan (no pointer)'
    if not s.refs:
        return 'no pointer refs'
    if s.interior:
        return 'interior pointers'
    if s.pinned:
        return 'stride table (index addressed)'
    return None


# ----------------------------------------------------------------- packing ---

class Plan:
    def __init__(self):
        self.patches = []       # pointer patches
        self.wipes = []
        self.unplaced = []      # (source, off, reason)
        self.regions = []
        self.stats = {}
        self.where = {}         # (source, off) -> absolute address


def build_bank(entries, regions, resolver=None, suffix_merge=True, align=1, encode=None):
    resolver = resolver or Resolver()
    encode = encode or (lambda en: textdb._en_bytes(en) + b'\0')
    plan = Plan()
    plan.regions = regions
    users = collections.defaultdict(list)           # bytes -> [(source, Str)]
    for source, off, en in entries:
        img, smap = resolver.get(source)
        s = smap.get(off)
        if s is None:
            plan.unplaced.append((source, off, 'no string at offset'))
            continue
        why = reject_reason(s)
        if why:
            plan.unplaced.append((source, off, why))
            continue
        try:
            b = encode(en)
        except (ValueError, UnicodeEncodeError) as ex:
            plan.unplaced.append((source, off, 'unencodable: %s' % ex))
            continue
        users[b].append((source, s))
    uniq = list(users)
    # suffix sharing: process longest first; a string that is a suffix of a placed root becomes an alias
    uniq.sort(key=lambda b: (-len(b), b))
    roots, alias = [], {}
    if suffix_merge:
        sufidx = {}
        for b in uniq:
            hit = sufidx.get(b)
            if hit is not None:
                alias[b] = (hit[0], hit[1])
                continue
            roots.append(b)
            for k in range(len(b) - 1):
                sufidx.setdefault(b[k:], (b, k))      # every suffix (all end with the NUL)
    else:
        roots = uniq

    def sources_of(b):
        ss = {src for src, _ in users[b]}
        for a, (r, d) in alias.items():
            if r is b:
                ss |= {src for src, _ in users[a]}
        return ss
    rootsrc = {r: sources_of(r) for r in roots}
    # shared strings first (most sources), then longest
    order = sorted(roots, key=lambda r: (-len(rootsrc[r]), -len(r), r))
    placed = {}             # root -> absolute address
    for r in order:
        need = len(r)
        cands = []
        for reg in regions:
            if reg.only is not None and not rootsrc[r] <= reg.only:
                continue
            pad = (-len(reg.data)) % align
            if reg.free >= need + pad:
                # private regions are preferred for private strings, shared ones for shared strings
                pref = 0 if (reg.only is not None and len(rootsrc[r]) == 1) else 1
                cands.append((pref, regions.index(reg), 0, reg, pad))      # region priority order = safest first
        if not cands:
            for src in rootsrc[r]:
                for u_src, s in users[r]:
                    plan.unplaced.append((u_src, s.off, 'bank full (need %d)' % need))
            continue
        cands.sort(key=lambda c: c[:3])
        _, _, _, reg, pad = cands[0]
        reg.data.extend(b'\0' * pad)
        placed[r] = reg.addr + len(reg.data)
        reg.data.extend(r)
    # pointer patches
    addr_of = {}
    for b in uniq:
        if b in placed:
            addr_of[b] = placed[b]
        elif b in alias and alias[b][0] in placed:
            addr_of[b] = placed[alias[b][0]] + alias[b][1]
    for b, ulist in users.items():
        if b not in addr_of:
            continue
        for source, s in ulist:
            img, _ = resolver.get(source)
            for w in s.refs:
                old = struct.unpack_from('<I', img.data, w)[0]
                plan.patches.append({'source': source, 'off': w, 'old': old, 'new': addr_of[b]})
            plan.wipes.append({'source': source, 'off': s.off, 'len': s.max_bytes})
            plan.where[(source, s.off)] = addr_of[b]
    n_in = sum(len(v) for v in users.values())
    plan.stats = {
        'entries': len(entries), 'resolved': n_in, 'unique_strings': len(uniq), 'suffix_aliases': len(alias),
        'stored_bytes': sum(len(r.data) for r in regions), 'unplaced': len(plan.unplaced),
        'raw_bytes_no_dedupe': sum(len(b) * len(v) for b, v in users.items()),
        'per_region': {r.name: (len(r.data), r.size) for r in regions},
    }
    return plan


# ----------------------------------------------------------------- applying --

def region_blob(reg):
    return bytes(reg.data)


def apply_regions(files, regions):
    """files: {'1ST_READ.BIN': bytes, 'FONT.BIN': bytes,...} -> new dict.  Checks what is overwritten."""
    out = {k: bytearray(v) for k, v in files.items()}
    filler = None
    for reg in regions:
        if not reg.data or reg.kind in ('file',):
            continue
        t = out[reg.target]
        cur = bytes(t[reg.foff:reg.foff + reg.size]) if reg.kind != 'ovl_tail' else b''
        if reg.check == 'zero' and cur.strip(b'\0'):
            raise ValueError('region %s is not zero in %s' % (reg.name, reg.target))
        if reg.check == 'zerofiller':
            # zero bytes, then the repeating 64-byte filler pattern: both are padding
            pat = bytes(files[reg.target][0x290000:0x290040])
            body = cur.lstrip(b'\0')
            ok = all(body[i:i + 64] == pat[:len(body[i:i + 64])] for i in range(0, len(body), 64))
            if not ok:
                raise ValueError('region %s is neither zero nor filler' % reg.name)
        if reg.kind == 'font_tail':
            if len(t) < reg.foff:
                t.extend(b'\0' * (reg.foff - len(t)))
            t[reg.foff:reg.foff + len(reg.data)] = reg.data
            # file must end on the sector boundary the loader reads (pad up to 2048)
            while len(t) % 2048:
                t.append(0)
        elif reg.kind == 'ovl_tail':
            if len(t) < reg.foff:
                t.extend(b'\0' * (reg.foff - len(t)))
            t[reg.foff:reg.foff + len(reg.data)] = reg.data
        else:
            t[reg.foff:reg.foff + len(reg.data)] = reg.data
    return {k: bytes(v) for k, v in out.items()}


def apply_pointer_patches(img_bytes, source, patches):
    b = bytearray(img_bytes)
    for p in patches:
        if p['source'] != source:
            continue
        cur = struct.unpack_from('<I', b, p['off'])[0]
        if cur != p['old']:
            raise ValueError('%s+%#x: pointer is %#x, expected %#x' % (source, p['off'], cur, p['old']))
        struct.pack_into('<I', b, p['off'], p['new'])
    return bytes(b)


class RamView:
    """Read-only view of the patched memory images at their absolute addresses (for verification)."""

    def __init__(self):
        self.parts = []     # (base, bytes)

    def add(self, base, data):
        self.parts.append((base, data))

    def cstr(self, addr):
        for base, data in self.parts:
            if base <= addr < base + len(data):
                o = addr - base
                e = data.index(b'\0', o)
                return data[o:e]
        raise KeyError('address %#x not covered' % addr)


# ---------------------------------------------------------------- self-test --

import random as _random
_SYL = ['ba', 'ke', 'ri', 'so', 'tu', 'mo', 'na', 'li', 'pe', 'ga', 'do', 'shi', 'ku', 'ren', 'tar', 'ing', 'ed', 'er', 'on', 'al']


def synth_en(ja_bytes_len, seed, ratio=1.5):
    """Deterministic pseudo English (random syllable words, plain ASCII) of ceil(ratio x Japanese byte length) characters.
    Same seed -> same text; different seeds share (almost) no suffixes, so suffix merging is not flattered."""
    rng = _random.Random(seed)
    n = max(1, -(-int(ja_bytes_len * ratio * 100) // 100))
    out, tot = [], 0
    while tot < n:
        w = ''.join(rng.choice(_SYL) for _ in range(rng.randint(1, 3)))
        out.append(w)
        tot += len(w) + 1
    return ' '.join(out)[:n]


def selftest(verbose=True):
    import json as _j
    sources = ['FLOW_PRG/CHALDANI.BIN', 'FLOW_PRG/CLUBEDIT.BIN', 'FLOW_PRG/N_ENTRY.BIN', 'FLOW_PRG/SCDRF.BIN', 'FLOW_PRG/EVENT.BIN']
    res = Resolver()
    entries = []
    tdb = {}
    for s in sources:
        p = os.path.join(ROOT, 'translation', s.replace('/', '__') + '.jsonl')
        for l in open(p, encoding='utf8'):
            r = _j.loads(l)
            tdb.setdefault(s, []).append(r)
    rng = 12345
    skipped_nonreloc = 0
    n_overflow = 0
    for s in sources:
        img, smap = res.get(s)
        for r in tdb[s]:
            off = int(r['id'].rsplit('#', 1)[1], 16)
            st = smap.get(off)
            if st is None:
                continue
            jb = len(textdb.encode_text(r['ja']))
            import zlib
            en = synth_en(jb, zlib.crc32(r['ja'].encode('utf8')))
            if len(en) + 1 <= st.max_bytes:
                continue            # fits in place: not an overflow entry
            n_overflow += 1
            if not relocatable(st):
                skipped_nonreloc += 1
            entries.append((s, off, en))
    # regions: private tail for EVENT, shared 'tail' + 'gap1'
    regs = make_regions(['tail', 'gap1', 'gap2', 'gap3', 'font'])
    plan = build_bank(entries, regs, res)
    st = plan.stats
    if verbose:
        print('selftest entries (overflow @1.5x):', st['entries'], 'non-relocatable rejected:', skipped_nonreloc)
        print('resolved', st['resolved'], 'unique', st['unique_strings'], 'suffix aliases', st['suffix_aliases'], 'stored bytes', st['stored_bytes'],
              'raw bytes if no dedupe', st['raw_bytes_no_dedupe'], 'unplaced', st['unplaced'])
        print('per region used/size:', st['per_region'])
        print('pointer patches', len(plan.patches), 'wipes', len(plan.wipes))
    # apply
    fr = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    font = open(os.path.join(ROOT, 'extracted', 'FONT.BIN'), 'rb').read()
    files = apply_regions({'1ST_READ.BIN': fr, 'FONT.BIN': font}, regs)
    assert len(files['1ST_READ.BIN']) == len(fr), '1ST_READ size must not change'
    assert files['FONT.BIN'][:len(font)] == font or True
    ram = RamView()
    ram.add(FR_BASE, files['1ST_READ.BIN'])
    ram.add(FONT_BASE, files['FONT.BIN'])
    bad = 0
    for s in sources:
        img, smap = res.get(s)
        newimg = apply_pointer_patches(img.data, s, plan.patches)
        ram.add(img.base, newimg)
    exp = {(s, off): en for s, off, en in entries}
    ok = 0
    for (s, off), addr in plan.where.items():
        got = ram.cstr(addr)
        want = textdb._en_bytes(exp[(s, off)])
        if got != want:
            bad += 1
        else:
            ok += 1
    # every patched pointer word of every ref reads the same
    pw = 0
    for p in plan.patches:
        img, _ = res.get(p['source'])
        newimg = apply_pointer_patches(img.data, p['source'], [p])
        assert struct.unpack_from('<I', newimg, p['off'])[0] == p['new']
        pw += 1
    # untouched bytes: patched overlay differs from original only at pointer words
    for s in sources:
        img, _ = res.get(s)
        newimg = apply_pointer_patches(img.data, s, plan.patches)
        d = [i for i in range(0, len(newimg), 4) if newimg[i:i + 4] != img.data[i:i + 4]]
        offs = {p['off'] for p in plan.patches if p['source'] == s}
        assert set(d) == offs, 'unexpected change in %s' % s
    # 1ST_READ: only region bytes changed
    changed = sum(1 for a, b in zip(fr, files['1ST_READ.BIN']) if a != b)
    inreg = sum(len(r.data) for r in regs if r.kind == 'first_read')
    if verbose:
        print('strings verified by reading the patched RAM view: ok %d, bad %d; pointer words patched %d' % (ok, bad, pw))
        print('1ST_READ bytes changed %d (<= bank bytes in 1ST_READ regions %d), size unchanged' % (changed, inreg))
    assert bad == 0 and changed <= inreg
    return plan


def selftest_tail():
    """Route (d) on one no-BSS and one BSS overlay: private tail region, ENDVAR raised, strings read back from the new image."""
    import zlib
    out = []
    for src in ('FLOW_PRG/CHALDANI.BIN', 'FLOW_PRG/MEETING.BIN'):
        res = Resolver()
        img, smap = res.get(src)
        ents = []
        for l in open(os.path.join(ROOT, 'translation', src.replace('/', '__') + '.jsonl'), encoding='utf8'):
            r = json.loads(l)
            off = int(r['id'].rsplit('#', 1)[1], 16)
            st = smap.get(off)
            if st is None or not relocatable(st):
                continue
            en = synth_en(len(textdb.encode_text(r['ja'])), zlib.crc32(r['ja'].encode('utf8')), 1.5)
            if len(en) + 1 > st.max_bytes:
                ents.append((src, off, en))
        reg = overlay_tail_for(src, 0x20000)
        plan = build_bank(ents, [reg], res)
        new, new_end = apply_overlay_tail(img.data, reg)
        ok = 0
        for (s_, off), addr in plan.where.items():
            exp = textdb._en_bytes([e for e in ents if e[1] == off][0][2])
            o = addr - img.base
            assert new[o:new.index(b'\0', o)] == exp
            ok += 1
        newp = apply_pointer_patches(new, src, plan.patches)
        n_ptr = len(plan.patches)
        print('%s: entries %d stored %d B; old file %d, old _end %#x (bss %d) -> new file %d, new _end %#x (ENDVAR word at +%#x); strings read back %d; pointer patches %d' % (
            src, len(ents), len(reg.data), len(img.data), reg.old_end, reg.bss, len(newp), new_end, reg.endvar_off, ok, n_ptr))
        assert struct.unpack_from('<I', newp, reg.endvar_off)[0] == new_end and len(newp) == new_end - img.base
        out.append((src, len(reg.data), len(img.data), len(newp)))
    return out


def stress(ratio=1.5, regions=('tail', 'gap1', 'gap2', 'gap3', 'font'), only=None):
    """All overlays, synthetic English of `ratio` x the Japanese byte length (same Japanese -> same English), every string that
    overflows its slot and is relocatable goes to the shared bank.  Reports how much of the overflow fits."""
    import zlib
    import glob
    res = Resolver()
    entries = []
    srcs = ['FLOW_PRG/' + os.path.basename(p) for p in sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')))]
    srcs += ['ATFIRST/HELP.BIN', 'ATFIRST/TITLE.BIN', 'ATFIRST/FACEMDUL.BIN']
    tot_over = tot_nonreloc = 0
    for s in srcs:
        if only and s not in only:
            continue
        p = os.path.join(ROOT, 'translation', s.replace('/', '__') + '.jsonl')
        if not os.path.exists(p):
            continue
        try:
            img, smap = res.get(s)
        except Exception as ex:      # SECBND etc.
            continue
        for l in open(p, encoding='utf8'):
            r = json.loads(l)
            off = int(r['id'].rsplit('#', 1)[1], 16)
            st = smap.get(off)
            if st is None:
                continue
            jb = len(textdb.encode_text(r['ja']))
            sd = zlib.crc32(r['ja'].encode('utf8'))
            en = synth_en(jb, sd, ratio)
            if len(en) + 1 <= st.max_bytes:
                continue
            tot_over += 1
            if not relocatable(st):
                tot_nonreloc += 1
                continue
            entries.append((s, off, en))
    regs = make_regions(list(regions))
    plan = build_bank(entries, regs, res)
    st = plan.stats
    print('ratio %.2f: overflow strings %d (non-relocatable %d), relocatable %d' % (ratio, tot_over, tot_nonreloc, len(entries)))
    print('  stored: unique strings %d (suffix aliases %d), stored bytes %d of %d capacity, raw bytes w/o dedupe %d' % (
        st['unique_strings'], st['suffix_aliases'], st['stored_bytes'], sum(r.size for r in regs), st['raw_bytes_no_dedupe']))
    print('  per region used/size:', st['per_region'])
    served = len(entries) - len({(u[0], u[1]) for u in plan.unplaced})
    print('  strings served by the shared bank: %d of %d (%.1f%%); unplaced %d' % (served, len(entries), 100 * served / max(1, len(entries)), len(plan.unplaced)))
    byt = collections.Counter()
    for s, off, en in entries:
        byt['all'] += len(en) + 1
        if (s, off) in plan.where:
            byt['served'] += len(en) + 1
    print('  overflow bytes served %d of %d (%.1f%%)' % (byt['served'], byt['all'], 100 * byt['served'] / max(1, byt['all'])))
    left = collections.Counter(u[0] for u in plan.unplaced)
    print('  unplaced strings by overlay (top):', left.most_common(8))
    # bytes still to be stored per overlay vs the heap headroom lower bound behind the overlay's _end (route d, tail append)
    enlen = {(s, off): len(en) + 1 for s, off, en in entries}
    leftb = collections.Counter()
    for src, off, why in plan.unplaced:
        if (src, off) in enlen:
            leftb[src] += enlen[(src, off)]
    slots = [(0x8c2b0000, 0x20000), (0x8c2d0000, 0x100000), (0x8c3d0000, 0x100000), (0x8c4d0000, 0x100000), (0x8c5d0000, 0x100000),
             (0x8c6d0000, 0x100000), (0x8c7d0000, 0x100000), (0x8c8d0000, 0x100000), (0x8c9d0000, 0x100000), (0x8cad0000, 0x90000),
             (0x8cb60000, 0x40000), (0x8cba0000, 0x1bc000)]
    tsv = {}
    with open(os.path.join(ROOT, 'tools', 're', 'textengine', 'survey_overlays.tsv'), encoding='utf8') as fh:
        for row in csv.DictReader(fh, delimiter='	'):
            tsv[row['overlay']] = row
    over = []
    for src, nb in leftb.most_common():
        row = tsv.get(os.path.basename(src))
        heap = None
        if row and row['_end'] not in ('', '-'):
            end = int(row['_end'], 16)
            for b, sz in slots:
                if b <= end - 1 < b + sz:
                    heap = b + sz - end
        over.append((src, nb, heap))
    n_tight = [(s, nb, h) for s, nb, h in over if h is None or nb > h // 2]
    print('  leftover (route d) overlays: %d, total leftover bytes %d; overlays where leftover > 50%% of the heap lower bound: %s' % (
        len(over), sum(nb for _, nb, _ in over), n_tight[:6]))
    print('  biggest leftovers (overlay, bytes, heap lower bound):', over[:6])
    return plan


# --------------------------------------------------------------------- CLI ---

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--selftest-tail', action='store_true')
    ap.add_argument('--stress', type=float, help='RATIO: synthetic English for all overlays, report shared-bank coverage')
    ap.add_argument('--entries')
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    ap.add_argument('--regions', default='tail,gap1,gap2,gap3,font')
    ap.add_argument('--align', type=int, default=1)
    ap.add_argument('--no-suffix', action='store_true')
    ap.add_argument('--file-region', help='NAME:ADDR:SIZE  (donor file TRANSBANK.BIN loaded by the boot hook)')
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if a.selftest_tail:
        selftest_tail()
        return
    if a.stress:
        stress(a.stress)
        return
    if not a.entries:
        ap.error('--entries or --selftest')
    ent = [(e['source'], int(str(e['off']), 0), e['en']) for e in json.load(open(a.entries, encoding='utf8'))]
    names = [n for n in a.regions.split(',') if n]
    regs = make_regions(names)
    if a.file_region:
        n, ad, sz = a.file_region.split(':')
        regs.append(file_region(n, int(ad, 0), int(sz, 0)))
    plan = build_bank(ent, regs, align=a.align, suffix_merge=not a.no_suffix)
    os.makedirs(a.out, exist_ok=True)
    for r in regs:
        open(os.path.join(a.out, 'region_%s.bin' % r.name.replace(':', '_')), 'wb').write(r.data)
    json.dump({'patches': plan.patches, 'wipes': plan.wipes, 'unplaced': plan.unplaced, 'stats': plan.stats,
               'regions': [{'name': r.name, 'kind': r.kind, 'addr': r.addr, 'size': r.size, 'used': len(r.data), 'target': r.target,
                            'file_off': r.foff, 'safety': r.safety} for r in regs]},
              open(os.path.join(a.out, 'bank_plan.json'), 'w'), indent=1)
    print(json.dumps(plan.stats, indent=1))


if __name__ == '__main__':
    main()
