"""Zero holes of the 1ST_READ image that are (a) zero in the file, (b) zero in all four RAM dumps and
(c) not the target of any 0x8c../0xac../0x0c.. word in 1ST_READ itself (code literal pools + data), with
a one-page margin on each side.  Output: build/memmap/holes.tsv (+ stdout).
Run: python -I -X utf8 tools/re/capacity/memmap/holes.py"""
import array
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import memmap as m  # noqa: E402

PAGE = 4096
f1 = m.r1st()
dumps = [m.load_dump(n) for n in m.DUMPS]
npg = m.RAMSZ // PAGE
refpages = [0] * npg           # count of 1ST_READ words pointing into each page
w = array.array('I')
w.frombytes(f1[:len(f1) // 4 * 4])
for x in w:
    hi = x >> 24
    if hi in (0x8C, 0xAC, 0x0C):
        a = 0x8C000000 | (x & 0xFFFFFF)
        if m.BASE <= a < m.BASE + m.RAMSZ:
            refpages[(a - m.BASE) // PAGE] += 1


# literal (start,end) descriptors found in 1ST_READ: memory pools, never free (see docs/memory-map.md section 5)
POOLS = [(0x8C227000, 0x8C239000), (0x8C239000, 0x8C299400), (0x8C299400, 0x8C2E0000)]


def in_pool(p):
    a = m.BASE + p * PAGE
    return any(lo <= a < hi for lo, hi in POOLS)


def zero_everywhere(p):
    if in_pool(p):
        return False
    lo = p * PAGE
    if lo >= m.R1ST - m.BASE and lo + PAGE <= m.R1ST - m.BASE + len(f1):
        if f1[lo - (m.R1ST - m.BASE):lo - (m.R1ST - m.BASE) + PAGE].count(0) != PAGE:
            return False
    else:
        return False
    return all(d[lo:lo + PAGE].count(0) == PAGE for d in dumps)


z = [zero_everywhere(p) for p in range(npg)]
runs = []
p = 0
while p < npg:
    if z[p]:
        q = p
        while q < npg and z[q]:
            q += 1
        runs.append((p, q))
        p = q
    else:
        p += 1
out = []
for p, q in runs:
    # shrink so that no page in the run, nor the page just before, nor the page just after is referenced
    lo, hi = p, q
    while lo < hi and (refpages[lo] or (lo > 0 and refpages[lo - 1])):
        lo += 1
    while hi > lo and (refpages[hi - 1] or (hi < npg and refpages[hi])):
        hi -= 1
    # split on referenced pages inside
    cur = lo
    segs = []
    for k in range(lo, hi + 1):
        if k == hi or refpages[k]:
            if k - cur > 0:
                segs.append((cur, k))
            cur = k + 1
    for a, b in segs:
        out.append((a, b, p, q))


def dist_prev(a):
    k = a - 1
    while k >= 0 and not refpages[k]:
        k -= 1
    return (a - k) * PAGE if k >= 0 else -1


def dist_next(b):
    k = b
    while k < npg and not refpages[k]:
        k += 1
    return (k - b) * PAGE
tot = 0
with open(os.path.join(ROOT, 'build', 'memmap', 'holes.tsv'), 'w', encoding='utf-8', newline='\n') as fo:
    fo.write('start\tend\tbytes\tparent_zero_run\tdist_to_prev_ref_page\tdist_to_next_ref_page\n')
    for a, b, p, q in sorted(out, key=lambda t: -(t[1] - t[0])):
        sz = (b - a) * PAGE
        tot += sz
        dp, dn = dist_prev(a), dist_next(b)
        fo.write('0x%08x\t0x%08x\t%d\t0x%08x-0x%08x\t%d\t%d\n' % (m.BASE + a * PAGE, m.BASE + b * PAGE, sz, m.BASE + p * PAGE, m.BASE + q * PAGE, dp, dn))
        print('0x%08x-0x%08x %7d bytes (parent zero run %08x-%08x) nearest referenced page: %d B before, %d B after' % (
            m.BASE + a * PAGE, m.BASE + b * PAGE, sz, m.BASE + p * PAGE, m.BASE + q * PAGE, dp, dn))
print('total clean 1ST_READ holes (>=1 page, 1-page margin, no 1ST_READ pointer): %d bytes in %d segments' % (tot, len(out)))
print('sum of all file-zero & dump-zero runs (no margin/ref filter): %d bytes' % sum((q - p) * PAGE for p, q in runs))
