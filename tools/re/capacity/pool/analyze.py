"""Static pool survey: pool sizes, JP bytes, slack, duplicate/suffix sharing gains, dead-space candidates,
risk scans (relative-offset words, references from 1ST_READ).  -> results/pools.json + pools.tsv"""
import json, os, re, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import textrepack as R

ASCII_RUN = re.compile(rb'(?<![\x20-\x7e])[\x20-\x7e]{6,}(?=\x00)')

def suffix_gain(texts):
    """bytes saved if every text (with NUL) that is a proper byte-suffix of another distinct text shared it."""
    uniq = set(texts)
    covered = set()
    for h in uniq:
        for k in range(1, len(h)):
            if h[k:] in uniq:
                covered.add(h[k:])
    return sum(len(t) + 1 for t in covered), len(covered)

def main():
    t0 = time.time()
    imgs = load_all()
    f1 = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    w1 = {}
    for i in range(0, len(f1) - 3, 4):
        w = struct.unpack_from('<I', f1, i)[0]
        if 0x8c200000 <= w < 0x8d000000:
            w1.setdefault(w, []).append(i)
    rows = {}
    for source, img, strs, ptrs in imgs:
        d, base = img.data, img.base
        pools, where = R.find_pools(strs)
        mov = [s for s in strs if R.is_movable(s)]
        fix = [s for s in strs if not R.is_movable(s)]
        row = dict(size=len(d), base=hex(base), strings=len(strs), movable=len(mov), fixed=len(fix),
                   orphan=sum(1 for s in strs if s.orphan), pinned=sum(1 for s in strs if s.pinned and not s.orphan),
                   interior=sum(1 for s in strs if s.interior and not s.pinned and not s.orphan),
                   pools=len(pools), pool_cap=sum(p.cap for p in pools),
                   pool_max=max((p.cap for p in pools), default=0),
                   mov_jp=sum(len(s.raw) + 1 for s in mov), fix_jp=sum(len(s.raw) + 1 for s in fix),
                   fix_cap=sum(s.max_bytes for s in fix),
                   all_jp=sum(len(s.raw) + 1 for s in strs))
        row['pool_slack'] = row['pool_cap'] - row['mov_jp']
        row['fix_slack'] = row['fix_cap'] - row['fix_jp']
        # sharing gains (movable strings): identical text inside one pool / anywhere in the image
        dup_pool = 0
        suf_pool = 0
        suf_n = 0
        for p in pools:
            seen = {}
            for s in p.home:
                seen[s.raw] = seen.get(s.raw, 0) + 1
            dup_pool += sum((c - 1) * (len(t) + 1) for t, c in seen.items())
            g, n = suffix_gain(list(seen))
            suf_pool += g; suf_n += n
        seen = {}
        for s in mov:
            seen[s.raw] = seen.get(s.raw, 0) + 1
        row['dup_pool_bytes'] = dup_pool
        row['dup_img_bytes'] = sum((c - 1) * (len(t) + 1) for t, c in seen.items())
        row['dup_strings_extra'] = sum(c - 1 for c in seen.values())
        row['suffix_pool_bytes'] = suf_pool       # additional to dup (distinct texts only)
        row['suffix_pool_n'] = suf_n
        # dead space candidates
        covered = bytearray(len(d))
        for s in strs:
            for k in range(s.off, s.end + 1):
                covered[k] = 1
        asc = [m for m in ASCII_RUN.finditer(d) if not covered[m.start()]]
        tgt = set(ptrs.values())
        row['ascii_runs'] = len(asc)
        row['ascii_bytes'] = sum(m.end() - m.start() + 1 for m in asc)
        row['ascii_unref'] = sum(1 for m in asc if m.start() not in tgt)
        row['ascii_unref_bytes'] = sum(m.end() - m.start() + 1 for m in asc if m.start() not in tgt)
        row['orph_bytes'] = sum(len(s.raw) + 1 for s in strs if s.orphan)
        # risk scans (movable strings only)
        addrs = {base + s.off: s for s in mov}
        row['ref_words'] = sum(len(s.refs) for s in mov)
        row['multi_ref_strings'] = sum(1 for s in mov if len(s.refs) > 1)
        rel = 0
        words = set()
        rw = set(w for s in mov for w in s.refs)
        offs = {s.off for s in mov if s.off >= 0x10000}
        for i in range(0, len(d) - 3, 4):
            if i in rw:
                continue
            v = struct.unpack_from('<I', d, i)[0]
            if v in offs:
                rel += 1
        row['rel_offset_words'] = rel               # aligned u32 == a movable string's file offset (>=0x10000), not a ref
        row['first_read_hits'] = sum(len(w1[a]) for a in addrs if a in w1)
        rows[source] = row
        print(source, round(time.time() - t0), flush=True)
    out = os.path.join(HERE, 'results'); os.makedirs(out, exist_ok=True)
    json.dump(rows, open(os.path.join(out, 'pools.json'), 'w'), indent=0)

if __name__ == '__main__':
    main()
