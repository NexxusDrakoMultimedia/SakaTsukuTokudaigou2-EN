"""memmap: RAM map of the Dreamcast game from RAM dumps + overlay loader facts.

Everything here is computed from (a) the four 16 MB RAM dumps in build/emu/ (base 0x8C000000),
(b) the extracted overlays/1ST_READ, (c) the loader/allocator layout reverse engineered in
docs/memory-map.md (slot table 0x8c16bf9c, slot structs at 0x8c228384 stride 0x60, malloc block
header = size,tag,prev,next,guard).  Output goes to build/memmap/.

    python -I -X utf8 tools/memmap.py all          # everything
    python -I -X utf8 tools/memmap.py overlays     # build/memmap/overlays.tsv
    python -I -X utf8 tools/memmap.py maps         # page maps + class totals + diffs
    python -I -X utf8 tools/memmap.py heaps        # per-dump slot/heap walk
    python -I -X utf8 tools/memmap.py free         # globally free RAM candidates + pointer scan
"""
import array
import glob
import hashlib
import os
import struct
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from sh4stub import run_stub, StubError  # noqa: E402

BASE = 0x8C000000
RAMSZ = 0x1000000
PAGE = 4096
CH = 32                                   # chunk size for content matching
EXT = os.path.join(ROOT, 'extracted')
OUT = os.path.join(ROOT, 'build', 'memmap')
DUMPS = ['ram_2400', 'ram_5400', 'live1_ram', 'live3_ram']
DUMP_DESC = {
    'ram_2400': 'title screen (~40 s)', 'ram_5400': 'title attract loop',
    'live1_ram': 'Club Edit > Name Entry (N_ENTRY active)',
    'live3_ram': 'Club Edit > Name&Mascot Select (CLUBEDIT active)',
}
FEED, DEAD = 0xFEEDFEED, 0xDEADDEAD
SLOT_TABLE_VA = 0x8C16BF9C                # (base,size) x 12 then 0,0
SLOT_ARRAY_PTR_VA = 0x8C230804            # u32 -> slot struct array
SLOT_STRIDE = 0x60
R1ST = 0x8C010000


def u32(buf, off):
    return struct.unpack_from('<I', buf, off)[0]


def rd(path):
    with open(path, 'rb') as f:
        return f.read()


def load_dump(name):
    d = rd(os.path.join(ROOT, 'build', 'emu', name + '.bin'))
    assert len(d) == RAMSZ, name
    return d


def r1st():
    return rd(os.path.join(EXT, '1ST_READ.BIN'))


def slot_table():
    f = r1st()
    t = []
    o = SLOT_TABLE_VA - R1ST
    while True:
        b, s = struct.unpack_from('<II', f, o)
        if b == 0:
            break
        t.append((b, s))
        o += 8
    return t


# ----------------------------------------------------------------------------------------------
# overlay table
# ----------------------------------------------------------------------------------------------
def overlay_paths():
    ps = [(p, 'FLOW_PRG') for p in sorted(glob.glob(os.path.join(EXT, 'FLOW_PRG', '*.BIN')))]
    ps += [(p, 'ATFIRST') for p in sorted(glob.glob(os.path.join(EXT, 'ATFIRST', '*.BIN')))]
    return ps


def run_overlay_stub(d, slots):
    """Find load base + run entry stub.  Returns dict or None."""
    f1 = r1st()
    reg = [(R1ST, bytearray(f1))]
    cands = []
    for w in struct.unpack_from('<64I', d, 0):
        if BASE + 0x2B0000 <= w < BASE + 0xD00000:
            cands.append(w & ~0xFFFF)
    cands = sorted(set(cands))
    slot_bases = [b for b, _ in slots]
    # 1) hook-type stubs: r5 equals the candidate base
    for c in cands:
        try:
            r = run_stub(d, c, reg)
        except StubError:
            continue
        if r.get('target') == 0x8C163194 and r['r5'] == c:
            r['kind'] = 'hook'
            r['base'] = c
            return r
    # 2) direct stubs (GETREP/NENREP/LOADBAR): write rounded end into descriptor+4 and return descriptor
    for c in sorted(set(cands) | set(slot_bases)):
        try:
            r = run_stub(d, c, reg)
        except StubError:
            continue
        if r.get('ret') and r['writes']:
            (wa, wv), = list(r['writes'].items())[:1]
            if c <= wa < c + len(d) and c <= wv < c + len(d) + 0x1000000 and wv >= c + len(d) * 0.9:
                r['kind'] = 'direct'
                r['base'] = c
                r['desc'] = wa - 4
                r['end'] = wv
                return r
    return None


def load_text_stats():
    """translation/*.jsonl -> {'FLOW_PRG__X.BIN': (records, sum of max_bytes)}"""
    import json
    t = {}
    for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
        n = os.path.basename(p)[:-6]
        c = b = 0
        with open(p, encoding='utf-8') as f:
            for line in f:
                r = json.loads(line)
                c += 1
                b += r.get('max_bytes') or 0
        t[n] = (c, b)
    return t


TEXT = load_text_stats()


def build_overlay_rows():
    slots = slot_table()
    slot_idx = {b: i for i, (b, s) in enumerate(slots)}
    rows = []
    for p, dr in overlay_paths():
        d = rd(p)
        name = os.path.basename(p)
        row = dict(overlay=name, dir=dr, size=len(d))
        if name in ('BPINFO.BIN', 'FONT.BIN'):
            row.update(note='not an overlay (data file)')
            rows.append(row)
            continue
        if name == 'SECBND.BIN':
            row.update(note='not an SH-4 overlay (data, no stub)')
            rows.append(row)
            continue
        r = run_overlay_stub(d, slots)
        if r is None:
            row.update(note='stub not decoded')
            rows.append(row)
            continue
        base = r['base']
        if r['kind'] == 'hook':
            desc, end = r['r4'], r['r6']
        else:
            desc, end = r['desc'], r['end']
        row.update(base=base, kind=r['kind'], desc=desc, end_rounded=end)
        # raw _end word: the 32-bit indirect read performed by the stub whose value is an address in RAM
        rawv = None
        for a_, v_ in r.get('reads', []):
            if base <= a_ < base + len(d) and BASE <= v_ < BASE + RAMSZ:
                rawv = (a_, v_)
                break
        row['endvar_addr'] = rawv[0] if rawv else None
        row['end_value'] = rawv[1] if rawv else None
        do = desc - base
        dbytes = d[do:do + 8] if 0 <= do < len(d) - 8 else b'\0' * 8
        row['desc0'] = dbytes[0]
        row['desc1'] = dbytes[1]
        row['count'] = dbytes[1] & 0x7F
        row['dflag'] = dbytes[1] >> 7
        row['slot_aligned'] = base in slot_idx
        # ENDVAR raw value (hook stubs: word read by the stub; recompute from emulator memory when possible)
        file_end = base + len(d)
        row['file_end'] = file_end
        row['file_end_sector'] = base + ((len(d) + 0x7FF) // 0x800) * 0x800
        # raw _end value = what the stub started from: reverse the rounding
        # (end_rounded = ((v|0x80000000)&~0x1f)+0x20)
        row['end_hi'] = end
        if base in slot_idx:
            i0 = slot_idx[base]
            cnt = row['count']
            if cnt and i0 + cnt <= len(slots):
                slot_end = slots[i0][0] + sum(s for _, s in slots[i0:i0 + cnt])
            else:
                slot_end = None
            row['slot_index'] = i0
            row['slot_end'] = slot_end
            row['span_ok'] = (row['desc0'] == i0)
        else:
            row['slot_index'] = None
            row['slot_end'] = None
            row['span_ok'] = False
        rows.append(row)
    return rows


# ----------------------------------------------------------------------------------------------
# slot / heap walking on a dump
# ----------------------------------------------------------------------------------------------
def slot_array_va(dump):
    return u32(dump, SLOT_ARRAY_PTR_VA - BASE)


def walk_slots(dump):
    """Return list of slot dicts with heap blocks for slot structs of a dump."""
    sa = slot_array_va(dump)
    out = []
    for i in range(12):
        s = sa + i * SLOT_STRIDE
        o = s - BASE
        st = struct.unpack_from('<H', dump, o + 2)[0]
        info = dict(index=i, struct=s, state=st,
                    heap_size=u32(dump, o + 0x14), heap_start=u32(dump, o + 0x40),
                    desc=u32(dump, o + 0x44), base=u32(dump, o + 0x48), size=u32(dump, o + 0x4C),
                    owner=u32(dump, o + 0x50), blocks=[], bad=None)
        a = info['heap_start']
        end = a + info['heap_size']
        if info['heap_size']:
            while a < end:
                sz, tg = u32(dump, a - BASE), u32(dump, a - BASE + 4)
                if tg not in (FEED, DEAD) or sz == 0 or sz % 32 or a + sz > end:
                    info['bad'] = (a, sz, tg)
                    break
                info['blocks'].append((a, sz, tg == FEED))
                a += sz
        info['end'] = end
        out.append(info)
    return out


def nonzero_bytes(dump, lo, hi):
    seg = dump[lo - BASE:hi - BASE]
    return len(seg) - seg.count(0)


def zero_tail_run(dump, lo, hi):
    """(leading_zero_run_len, trailing_zero_run_len) of [lo,hi)."""
    seg = dump[lo - BASE:hi - BASE]
    n = len(seg)
    st = seg.lstrip(b'\0')
    lead = n - len(st)
    en = seg.rstrip(b'\0')
    trail = n - len(en)
    return lead, trail


def longest_zero_run(seg):
    best = cur = 0
    start = bstart = 0
    # fast path over 32-byte chunks
    z = bytes(32)
    i = 0
    n = len(seg)
    best_s = 0
    run_s = None
    for i in range(0, n, 32):
        if seg[i:i + 32] == z:
            if run_s is None:
                run_s = i
            if i + 32 - run_s > best:
                best = i + 32 - run_s
                best_s = run_s
        else:
            run_s = None
    return best_s, best


def heap_report(dump, slots):
    """per-slot summary rows"""
    rows = []
    for s in slots:
        if not s['heap_size']:
            continue
        used = sum(sz for a, sz, u in s['blocks'] if u)
        free = sum(sz for a, sz, u in s['blocks'] if not u)
        freeblocks = [(a, sz) for a, sz, u in s['blocks'] if not u]
        largest = max(freeblocks, key=lambda x: x[1]) if freeblocks else (0, 0)
        # dirty bytes in free blocks (payload beyond 0x20 header)
        dirty = 0
        for a, sz in freeblocks:
            dirty += nonzero_bytes(dump, a + 0x20, a + sz)
        # in the largest free block: zero extents
        lead = trail = 0
        zrun = (0, 0)
        if largest[1] > 0x20:
            lead, trail = zero_tail_run(dump, largest[0] + 0x20, largest[0] + largest[1])
            zrun = longest_zero_run(dump[largest[0] + 0x20 - BASE:largest[0] + largest[1] - BASE])
        rows.append(dict(slot=s, used=used, free=free, nblocks=len(s['blocks']), largest=largest,
                         dirty_free=dirty, lead=lead, trail=trail, zrun=zrun,
                         bad=s['bad']))
    return rows


# ----------------------------------------------------------------------------------------------
# known-file index and placement discovery
# ----------------------------------------------------------------------------------------------
def known_files():
    """name -> bytes for files worth matching against RAM."""
    files = {}
    files['1ST_READ.BIN'] = r1st()
    for sub in ('ATFIRST', 'FLOW_PRG', 'TRAINING', 'GAME2'):
        for p in sorted(glob.glob(os.path.join(EXT, sub, '**', '*'), recursive=True)):
            if os.path.isfile(p):
                files[sub + '/' + os.path.relpath(p, os.path.join(EXT, sub)).replace('\\', '/')] = rd(p)
    files['FONT.BIN(root)'] = rd(os.path.join(EXT, 'FONT.BIN'))
    return files


def group_identical(files):
    """collapse byte-identical files; returns (rep name -> bytes, rep -> [all names])"""
    byhash = {}
    for n, b in files.items():
        h = hashlib.md5(b).hexdigest()
        byhash.setdefault(h, []).append(n)
    reps, groups = {}, {}
    for h, names in byhash.items():
        names.sort()
        reps[names[0]] = files[names[0]]
        groups[names[0]] = names
    return reps, groups


def build_index(reps):
    """32-byte chunk (aligned in file) -> list of (fid, off).  Skips constant chunks."""
    idx = defaultdict(list)
    fids = list(reps)
    for fid, n in enumerate(fids):
        b = reps[n]
        for o in range(0, len(b) - CH + 1, CH):
            c = b[o:o + CH]
            if c.count(c[0]) == CH:
                continue
            idx[c].append((fid, o))
    return idx, fids


def find_placements(dump, idx, fids, reps, min_votes=24):
    votes = Counter()
    for a in range(0, RAMSZ - CH + 1, CH):
        c = dump[a:a + CH]
        hit = idx.get(c)
        if hit is None:
            continue
        if len(hit) > 40:                     # shared library code: skip (too ambiguous)
            continue
        for fid, off in hit:
            dest = a - off
            if dest >= 0 and dest % CH == 0:
                votes[(fid, dest)] += 1
    pl = []
    for (fid, dest), v in votes.items():
        if v < min_votes:
            continue
        b = reps[fids[fid]]
        if dest + len(b) > RAMSZ + 0x100000:
            continue
        # exact verification
        match = 0
        tot = 0
        for o in range(0, len(b) - CH + 1, CH):
            c = b[o:o + CH]
            if c.count(c[0]) == CH:
                continue
            tot += 1
            if dest + o + CH <= RAMSZ and dump[dest + o:dest + o + CH] == c:
                match += 1
        if tot and match / tot >= 0.30:
            pl.append(dict(fid=fid, name=fids[fid], dest=dest + BASE, size=len(b), match=match, tot=tot,
                           frac=match / tot))
    # resolve overlaps of identical regions: keep best frac per (dest range) loosely: sort by dest, frac desc
    pl.sort(key=lambda p: (-p['frac'], -p['match']))
    return pl


def classify_chunks(dump, placements, groups, slots, active_bss):
    """Return bytearray label per 32B chunk.  Labels: 0 zero, K 1ST_READ, F FONT, O overlay, Z other known,
    a heap-used, f heap-free(nonzero), b overlay BSS area, S slot struct/arena table, # other."""
    n = RAMSZ // CH
    lab = bytearray(n)                        # 0 = unclassified
    zero = bytes(CH)
    nz = bytearray(n)
    for i in range(n):
        if dump[i * CH:(i + 1) * CH] != zero:
            nz[i] = 1
    # known placements, best frac first, only chunks that actually match file bytes
    claimed = bytearray(n)
    for p in placements:
        b = p['_bytes']
        name = p['name']
        p['claimed'] = 0
        cls = ord('K') if name == '1ST_READ.BIN' else ord('F') if name.startswith('ATFIRST/FONT') or name.startswith('FONT.BIN') \
            else ord('O') if name.endswith('.BIN') else ord('Z')
        d0 = p['dest'] - BASE
        for o in range(0, len(b) - CH + 1, CH):
            a = d0 + o
            if a < 0 or a + CH > RAMSZ:
                continue
            ci = a // CH
            if claimed[ci] or not nz[ci]:
                continue
            if dump[a:a + CH] == b[o:o + CH]:
                lab[ci] = cls
                claimed[ci] = 1
                p['claimed'] += 1
    # heap blocks
    for s in slots:
        for a, sz, used in s['blocks']:
            c0 = (a - BASE) // CH
            c1 = (a - BASE + sz) // CH
            for ci in range(c0, c1):
                if nz[ci] and not claimed[ci]:
                    lab[ci] = ord('a') if used else ord('f')
                    claimed[ci] = 1
    for lo, hi in active_bss:
        for ci in range((lo - BASE) // CH, (hi - BASE + CH - 1) // CH):
            if 0 <= ci < n and nz[ci] and not claimed[ci]:
                lab[ci] = ord('b')
                claimed[ci] = 1
    # slot struct array
    sa = slot_array_va(dump)
    for ci in range((sa - BASE) // CH, (sa - BASE + 12 * SLOT_STRIDE + CH - 1) // CH):
        if nz[ci] and not claimed[ci]:
            lab[ci] = ord('S')
            claimed[ci] = 1
    for ci in range(n):
        if nz[ci] and not claimed[ci]:
            lab[ci] = ord('#')
    return lab, nz


def page_map(lab, nz):
    """one char per 4KB page: '.' zero, else majority class among non-zero chunks (uppercase=known
    placement, lowercase=heap, '#'=other), '*' if mixed (<60% majority)."""
    per = PAGE // CH
    rows = []
    chars = []
    for p in range(RAMSZ // PAGE):
        cnt = Counter()
        for ci in range(p * per, (p + 1) * per):
            if lab[ci]:
                cnt[chr(lab[ci])] += 1
        if not cnt:
            chars.append('.')
        else:
            c, v = cnt.most_common(1)[0]
            tot = sum(cnt.values())
            chars.append(c if v * 10 >= tot * 6 else '*')
    return chars


def write_map(path, title, chars, extra=''):
    per_row = 64                               # 64 pages = 256 KB
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# %s\n' % title)
        f.write('# one char = one 4 KB page. . zero | K 1ST_READ | F FONT.BIN | O overlay image | Z other known file\n')
        f.write('# a heap block in use (non-matching data) | f stale non-zero inside FREE heap block | b overlay BSS area\n')
        f.write('# S slot-struct table | # other non-zero (stack, system vars, unknown) | * mixed\n')
        if extra:
            f.write(extra)
        f.write('addr     ' + ''.join('%-8x' % (BASE + i * 0x10000)[-5:] if False else '' for i in range(0)) + '\n')
        for r in range(len(chars) // per_row):
            f.write('%08x ' % (BASE + r * per_row * PAGE))
            seg = ''.join(chars[r * per_row:(r + 1) * per_row])
            f.write(''.join(seg[i:i + 16] + ' ' for i in range(0, 64, 16)) + '\n')


def region_runs(chars):
    runs = []
    st = 0
    for i in range(1, len(chars) + 1):
        if i == len(chars) or chars[i] != chars[st]:
            runs.append((chars[st], BASE + st * PAGE, i - st))
            st = i
    return runs


# ----------------------------------------------------------------------------------------------
def cmd_overlays():
    os.makedirs(OUT, exist_ok=True)
    rows = build_overlay_rows()
    dumps = {n: load_dump(n) for n in DUMPS}
    dslots = {n: walk_slots(dumps[n]) for n in DUMPS}
    # measured heap per (dump, overlay) matched by (base, desc)
    meas = defaultdict(list)
    for n in DUMPS:
        for s in dslots[n]:
            if s['state'] in (4, 6) and s['desc']:
                hr = heap_report(dumps[n], [s])
                if hr:
                    meas[(s['base'], s['desc'], s['heap_start'])].append((n, hr[0]))
    cols = ['overlay', 'dir', 'file_size', 'stub', 'base', 'slot_aligned', 'desc', 'desc_count', 'file_end', 'file_end_sector',
            'end_value', 'end_rounded', 'bss_bytes', 'has_bss', 'slot_end', 'heap_bytes', 'tail_after_file',
            'append_hard', 'append_cons', 'cons_basis', 'bss_pad_cost', 'file_after_cons', 'text_records', 'text_ja_bytes',
            'append_cons_vs_text_x2',
            'measured_in', 'm_used', 'm_free', 'm_largest_free', 'm_dirty_free', 'm_touched', 'm_touched_pct', 'm_zero_run',
            'm_img_match_pct', 'm_tail_nz', 'm_bss_len', 'm_bss_nonzero', 'note']
    out = []
    flat = []
    for r in rows:
        o = dict.fromkeys(cols, '')
        o['overlay'] = r['overlay']
        o['dir'] = r['dir']
        o['file_size'] = r['size']
        if 'base' not in r:
            o['note'] = r.get('note', '')
            out.append(o)
            continue
        base = r['base']
        o['stub'] = r['kind']
        o['base'] = '0x%08x' % base
        o['slot_aligned'] = int(r['slot_aligned'])
        o['desc'] = '0x%08x' % r['desc']
        o['desc_count'] = r['count']
        o['file_end'] = '0x%08x' % r['file_end']
        o['file_end_sector'] = '0x%08x' % r['file_end_sector']
        er = r['end_rounded']
        o['end_rounded'] = '0x%08x' % er
        o['end_value'] = ('0x%08x' % r['end_value']) if r.get('end_value') else ''
        # end_value: undo +0x20 / mask -> report the pre-rounding value range by recomputing from image
        # (read the u32 the stub loaded: found by searching for value v with ((v|0x80000000)&~0x1f)+0x20 == er
        # among literals; we simply report rounded value; bss from rounded end)
        ev = r.get('end_value')
        bss = (ev - r['file_end']) if ev else (er - 0x20 - r['file_end'])
        o['bss_bytes'] = bss
        o['has_bss'] = 1 if bss > 0 else 0
        se = r['slot_end']
        if se:
            o['slot_end'] = '0x%08x' % se
            heap = se - er
            o['heap_bytes'] = heap
            o['tail_after_file'] = se - r['file_end']
            # append budget: new bytes X placed at [end_rounded, end_rounded+X); heap shrinks by X.
            hard = max(0, heap - 0x10000)
            # conservative policy (documented in docs/memory-map.md section 6):
            #   measured overlay : 0.5 x (free bytes in its heap at the dumped moment)
            #   not measured     : heap/8  (= half of the smallest free fraction observed, CLUBEDIT 25.4%)
            cons = (heap // 8) & ~0xFFF
            o['cons_basis'] = 'heap/8 (INFERRED)'
            o['append_hard'] = hard
            # file must grow to cover BSS zero-fill + X when appended past _end
            pad = max(0, (r.get('end_value') or r['file_end']) - r['file_end'])
            o['bss_pad_cost'] = pad
            tr = TEXT.get((r['dir'] + '__' + r['overlay']))
            if tr:
                o['text_records'], o['text_ja_bytes'] = tr
            o['_cons'] = cons
            o['_pad'] = pad
            o['_size'] = r['size']
        else:
            o['note'] = 'slot span unknown (base not slot aligned or count 0)'
        key = (base, r['desc'], er)
        if key in meas:
            ms = meas[key]
            o['measured_in'] = ','.join(sorted(set(m[0] for m in ms)))
            m = ms[-1][1]
            o['m_used'] = m['used']
            o['m_free'] = m['free']
            o['m_largest_free'] = m['largest'][1]
            o['m_dirty_free'] = m['dirty_free']
            o['m_zero_run'] = m['zrun'][1]
            o['m_touched'] = m['used'] + m['dirty_free']
            o['m_touched_pct'] = '%.1f' % (100.0 * (m['used'] + m['dirty_free']) / m['slot']['heap_size'])
            # image vs RAM (which copy of the file is the loaded one), sector tail and BSS contents
            dn = ms[-1][0]
            dd = dumps[dn]
            fb = rd(os.path.join(EXT, r['dir'], r['overlay']))
            tot = mt = 0
            for oo in range(0, len(fb) - CH + 1, CH):
                c = fb[oo:oo + CH]
                if c.count(c[0]) == CH:
                    continue
                tot += 1
                a_ = base - BASE + oo
                if dd[a_:a_ + CH] == c:
                    mt += 1
            o['m_img_match_pct'] = '%.1f' % (100.0 * mt / max(tot, 1))
            o['m_tail_nz'] = nonzero_bytes(dd, r['file_end'], r['file_end_sector']) if r['file_end_sector'] > r['file_end'] else 0
            bss_hi = max(er - 0x20, r['file_end_sector'])
            bl = bss_hi - r['file_end_sector']
            o['m_bss_len'] = max(bl, 0)
            o['m_bss_nonzero'] = nonzero_bytes(dd, r['file_end_sector'], bss_hi) if bl > 0 else 0
            if se and m['slot']['heap_size'] != heap:
                o['note'] = (o['note'] + ' HEAP_SIZE_MISMATCH(static %x measured %x)' % (heap, m['slot']['heap_size'])).strip()
            if mt / max(tot, 1) < 0.9:
                o['note'] = (o['note'] + ' NOT the copy loaded in RAM (%.0f%% chunk match; the other copy of this name is)'
                             % (100.0 * mt / max(tot, 1))).strip()
            elif se:
                o['_cons'] = (m['free'] // 2) & ~0xFFF
                o['cons_basis'] = '0.5 x measured free (%s)' % dn
        if se and r.get('end_value') and er - r['end_value'] > 0x100000:
            # ESTABLIS: the stub takes the heap start from the slot table (slot 3 base), not from _end.
            # Appending at the image end does NOT shift the heap; it lands in an overlay-private area of
            # unknown use ([file_end, heap start) = %d bytes), so no budget can be derived statically.
            o['_cons'] = None
            o['append_hard'] = ''
            o['bss_pad_cost'] = ''
            o['cons_basis'] = 'n/a (private area)'
            o['note'] = (o['note'] + ' heap start fixed at slot-3 base by stub; private area %08x..%08x (%d B) use UNKNOWN'
                         % (r['file_end'], er - 0x20, er - 0x20 - r['file_end'])).strip()
        if o.get('_cons') is not None and se:
            o['append_cons'] = o['_cons']
            o['file_after_cons'] = o['_size'] + o['_pad'] + o['_cons']
            if o['text_ja_bytes'] != '':
                o['append_cons_vs_text_x2'] = 'ok' if o['_cons'] >= 2 * o['text_ja_bytes'] else 'SHORT'
        out.append(o)
    with open(os.path.join(OUT, 'overlays.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\t'.join(cols) + '\n')
        for o in out:
            f.write('\t'.join(str(o[c]) for c in cols) + '\n')
    print('wrote overlays.tsv rows=%d' % len(out))
    return out


def cmd_heaps():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'heaps.txt'), 'w', encoding='utf-8', newline='\n') as f:
        for n in DUMPS:
            d = load_dump(n)
            sl = walk_slots(d)
            f.write('== %s : %s ; slot struct array @0x%08x\n' % (n, DUMP_DESC[n], slot_array_va(d)))
            for hr in heap_report(d, sl):
                s = hr['slot']
                f.write('slot %2d state %d base %08x size %06x | heap %08x..%08x (%x) desc %08x | blocks %3d used %7d free %7d '
                        'largest-free %08x+%x dirty-in-free %7d zero-run-in-largest %d bad %s\n' % (
                            s['index'], s['state'], s['base'], s['size'], s['heap_start'], s['end'], s['heap_size'], s['desc'],
                            hr['nblocks'], hr['used'], hr['free'], hr['largest'][0], hr['largest'][1], hr['dirty_free'],
                            hr['zrun'][1], hr['bad']))
            for s in sl:
                if not s['heap_size']:
                    continue
                f.write('  slot %d blocks:\n' % s['index'])
                for a, sz, u in s['blocks']:
                    f.write('    %08x %7d %s\n' % (a, sz, 'USED' if u else 'free'))
    print('wrote heaps.txt')


def cmd_maps():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    files = known_files()
    reps, groups = group_identical(files)
    idx, fids = build_index(reps)
    print('index: %d files (%d distinct), %d distinct chunks, %.1fs' % (len(files), len(reps), len(idx), time.time() - t0))
    ov = {r['overlay']: r for r in build_overlay_rows() if 'base' in r}
    allmaps = {}
    totals = {}
    with open(os.path.join(OUT, 'classes.txt'), 'w', encoding='utf-8', newline='\n') as ft:
        for n in DUMPS:
            d = load_dump(n)
            t0 = time.time()
            pl = find_placements(d, idx, fids, reps)
            for p in pl:
                p['_bytes'] = reps[p['name']]
                p['aliases'] = groups[p['name']]
            sl = walk_slots(d)
            # BSS areas of active overlays: [file_end, end_rounded)
            bss = []
            for s in sl:
                if s['state'] in (4, 6) and s['desc']:
                    bss.append((s['base'], s['heap_start']))
            lab, nz = classify_chunks(d, pl, groups, sl, [])
            chars = page_map(lab, nz)
            allmaps[n] = (chars, lab, nz, pl)
            cnt = Counter(chr(x) for x in lab if x)
            zero_pages = chars.count('.')
            totals[n] = (cnt, zero_pages)
            # placements listing
            ft.write('== %s : %s\n' % (n, DUMP_DESC[n]))
            ft.write('zero pages (4KB): %d (%.1f MB) | non-zero chunks(32B) by class: %s\n' % (
                zero_pages, zero_pages * PAGE / 1048576, ', '.join('%s=%d (%.2f MB)' % (k, v, v * CH / 1048576) for k, v in sorted(cnt.items()))))
            ft.write('placements (file @ dest, matched/non-constant 32B chunks):\n')
            for p in sorted(pl, key=lambda p: p['dest']):
                al = p['aliases']
                if p['claimed'] < 8:
                    continue                  # shadowed by a better placement (shared library code)
                ft.write('  %08x %-32s size %8d match %6d/%6d (%5.1f%%) claimed %6d chunks%s\n' % (
                    p['dest'], p['name'], p['size'], p['match'], p['tot'], 100 * p['frac'], p['claimed'],
                    ('  also=' + ','.join(a.split('/')[-1] for a in al[1:])) if len(al) > 1 else ''))
            ft.write('\n')
            extra = '# zero pages %d of 4096 | %s\n' % (zero_pages, ', '.join('%s=%d' % kv for kv in sorted(cnt.items())))
            write_map(os.path.join(OUT, 'map_%s.txt' % n), '%s - %s' % (n, DUMP_DESC[n]), chars, extra)
            print('%s: %d placements, %.1fs' % (n, len(pl), time.time() - t0))
    # diffs
    pairs = [('ram_2400', 'ram_5400'), ('ram_2400', 'live1_ram'), ('live1_ram', 'live3_ram'), ('ram_2400', 'live3_ram')]
    with open(os.path.join(OUT, 'diffs.txt'), 'w', encoding='utf-8', newline='\n') as f:
        for a, b in pairs:
            da, db = load_dump(a), load_dump(b)
            f.write('== diff %s -> %s  (per 64 KB block: number of 4 KB pages that differ, hex; . = none)\n' % (a, b))
            changed_pages = 0
            zero_to_nz = nz_to_zero = both = 0
            per = []
            for p in range(RAMSZ // PAGE):
                pa, pb = da[p * PAGE:(p + 1) * PAGE], db[p * PAGE:(p + 1) * PAGE]
                if pa != pb:
                    changed_pages += 1
                    za, zb = pa.count(0) == PAGE, pb.count(0) == PAGE
                    if za:
                        zero_to_nz += 1
                    elif zb:
                        nz_to_zero += 1
                    else:
                        both += 1
                    per.append(1)
                else:
                    per.append(0)
            f.write('pages differing %d of 4096 (%.1f MB): zero->data %d, data->zero %d, data->other data %d\n' % (
                changed_pages, changed_pages * PAGE / 1048576, zero_to_nz, nz_to_zero, both))
            for r in range(RAMSZ // 0x10000):
                seg = per[r * 16:(r + 1) * 16]
                c = sum(seg)
                if r % 4 == 0:
                    f.write('\n%08x ' % (BASE + r * 0x10000))
                f.write('%s' % ('.' if c == 0 else '%x' % (c if c < 16 else 15)))
                f.write(' ' if r % 4 != 3 else '')
            f.write('\n\n')
            # runs of differing pages
            runs = []
            st = None
            for i, v in enumerate(per + [0]):
                if v and st is None:
                    st = i
                if not v and st is not None:
                    runs.append((st, i))
                    st = None
            f.write('differing page runs >= 8 pages (32 KB):\n')
            for s0, s1 in runs:
                if s1 - s0 >= 8:
                    f.write('  %08x..%08x  %4d pages  state %s -> %s\n' % (
                        BASE + s0 * PAGE, BASE + s1 * PAGE, s1 - s0,
                        ''.join(sorted(set(allmaps[a][0][s0:s1]))), ''.join(sorted(set(allmaps[b][0][s0:s1])))))
            f.write('\n')
    print('wrote maps, classes, diffs')
    return allmaps


def zero_extents(chars_all, min_pages=4):
    """maximal runs of pages that are '.' in all dumps"""
    n = len(chars_all[0])
    z = [all(c[i] == '.' for c in chars_all) for i in range(n)]
    runs = []
    st = None
    for i, v in enumerate(z + [False]):
        if v and st is None:
            st = i
        if not v and st is not None:
            if i - st >= min_pages:
                runs.append((BASE + st * PAGE, (i - st) * PAGE))
            st = None
    return runs


def pointer_scan(regions):
    """For each region (lo,size): count 32-bit words that look like pointers into it.
    1ST_READ (code literal pools + data) is reported separately from the overlays.  Only the prefixes
    0x8c.. (cached) and 0xac.. (uncached mirror) are counted (0x0c.. physical words are mostly data noise).
    'below' = words pointing into the 4 KB just under the region (start of an array that may run into it)."""
    srcs = [('1ST_READ.BIN', R1ST, r1st())]
    slots = slot_table()
    for p, dr in overlay_paths():
        d = rd(p)
        n = os.path.basename(p)
        if n in ('SECBND.BIN', 'BPINFO.BIN', 'FONT.BIN'):
            continue
        r = run_overlay_stub(d, slots)
        base = r['base'] if r else 0x8C2D0000
        srcs.append((dr + '/' + n, base, d))
    res = {rg: dict(r1_in=0, r1_below=0, ov_in=0, ov_files=set(), ov_below=0, r1_first=[]) for rg in regions}
    for name, base, d in srcs:
        n4 = len(d) // 4
        words = array.array('I')
        words.frombytes(d[:n4 * 4])
        is1 = name == '1ST_READ.BIN'
        for i, w in enumerate(words):
            hi = w >> 24
            if hi == 0x8C:
                a = w
            elif hi == 0xAC:
                a = w & 0x8FFFFFFF
            else:
                continue
            for rg in regions:
                lo, sz = rg
                R = res[rg]
                if lo <= a < lo + sz:
                    if is1:
                        R['r1_in'] += 1
                        if len(R['r1_first']) < 4:
                            R['r1_first'].append((base + i * 4, w))
                    else:
                        if base <= a < base + len(d):
                            continue
                        R['ov_in'] += 1
                        R['ov_files'].add(name)
                elif lo - 0x1000 <= a < lo:
                    if is1:
                        R['r1_below'] += 1
                    else:
                        R['ov_below'] += 1
    return res


def cmd_free(allmaps=None):
    os.makedirs(OUT, exist_ok=True)
    if allmaps is None:
        chars_all = []
        for n in DUMPS:
            d = load_dump(n)
            chars_all.append(['.' if d[p * PAGE:(p + 1) * PAGE].count(0) == PAGE else '#' for p in range(RAMSZ // PAGE)])
    else:
        chars_all = [allmaps[n][0] for n in DUMPS]
    ext = zero_extents(chars_all, 4)
    f1 = r1st()
    slots_by_dump = {n: walk_slots(load_dump(n)) for n in DUMPS}
    ovrows = [r for r in build_overlay_rows() if r.get('slot_end')]
    rows = []
    for lo, sz in ext:
        hi = lo + sz
        notes = []
        if R1ST <= lo < R1ST + len(f1):
            e = min(hi, R1ST + len(f1))
            seg = f1[lo - R1ST:e - R1ST]
            notes.append('1ST_READ file bytes zero %d/%d' % (seg.count(0), len(seg)))
        st = set()
        for n in DUMPS:
            for s in slots_by_dump[n]:
                if s['base'] <= lo < s['base'] + s['size']:
                    st.add('slot%d:%s' % (s['index'], '/'.join(sorted(set('st%d' % x['state'] for dn in DUMPS for x in slots_by_dump[dn] if x['index'] == s['index'])))))
        notes.extend(sorted(st))
        cover = sorted(set(r['overlay'] for r in ovrows if r['base'] <= lo and hi <= r['slot_end'] and r['end_rounded'] <= lo))
        rows.append((lo, sz, notes, cover))
    regions = [(lo, sz) for lo, sz, _, _ in rows]
    res = pointer_scan(regions)
    with open(os.path.join(OUT, 'free_candidates.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('start\tend\tsize_bytes\tr1st_ptr_words_in\tr1st_ptr_words_just_below\tovl_ptr_words_in\tovl_files_with_ptr\t'
                'ovl_ptr_words_just_below\tn_overlays_whose_heap_covers\tr1st_first_refs\tnotes\n')
        for lo, sz, notes, cover in rows:
            R = res[(lo, sz)]
            refs = ';'.join('%08x->%08x' % a for a in R['r1_first'])
            f.write('0x%08x\t0x%08x\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%s\n' % (
                lo, lo + sz, sz, R['r1_in'], R['r1_below'], R['ov_in'], len(R['ov_files']), R['ov_below'], len(cover), refs,
                '; '.join(notes)))
    print('wrote free_candidates.tsv (%d regions)' % len(rows))
    return rows, res


def main(argv):
    cmd = argv[1] if len(argv) > 1 else 'all'
    if cmd == 'overlays':
        cmd_overlays()
    elif cmd == 'heaps':
        cmd_heaps()
    elif cmd == 'maps':
        cmd_maps()
    elif cmd == 'free':
        cmd_free()
    elif cmd == 'all':
        cmd_overlays()
        cmd_heaps()
        am = cmd_maps()
        cmd_free(am)
    else:
        print(__doc__)


if __name__ == '__main__':
    main(sys.argv)
