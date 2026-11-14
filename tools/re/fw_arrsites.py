"""fw_arrsites.py : for every fixed-stride record array found by textfmt_recarray (translation/*.jsonl, fmt recarr) count the code sites
that load a pointer into the array (aligned u32 words that point at or up to 0x80 bytes before the array's first name field and the
`mov.l @(disp,PC),Rn` instructions that load such a word).  Gives, per stride, the number of overlays / arrays / loader sites = a lower
bound of the code that has to change when the stride (field width) changes.  Read-only helper of the field-width study.
Bases: overlays load at the base listed in tools/re/capacity (taken from textdb.load_image)."""
import collections
import glob
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import textdb as T  # noqa: E402

groups = collections.OrderedDict()
for p in sorted(glob.glob('translation/*.jsonl')):
    for ln in open(p, encoding='utf8'):
        if '"recarr"' not in ln:
            continue
        r = json.loads(ln)
        m = re.search(r'S=(\d+) n=(\d+) W=(\d+)', r.get('ctx') or '')
        if not m:
            continue
        src, off = r['id'].split('#')
        k = (src, int(m.group(1)), int(m.group(2)), int(m.group(3)))
        groups.setdefault(k, []).append(int(off, 16))

per_stride = collections.defaultdict(lambda: {'arrays': 0, 'files': set(), 'sites': 0, 'words': 0, 'noptr': 0})
cache = {}
rows = []
for (src, S, n, W), offs in groups.items():
    if src not in cache:
        img = T.load_image(src)
        d = img.data
        nw = len(d) // 4
        cache[src] = (img.base, d, struct.unpack('<%dI' % nw, d[:nw * 4]))
    base, d, words = cache[src]
    offs.sort()
    # split into arrays by S spacing (several arrays of the same (S, n) may live in one file)
    arrays = []
    cur = [offs[0]]
    for o in offs[1:]:
        if o - cur[-1] == S:
            cur.append(o)
        else:
            arrays.append(cur)
            cur = [o]
    arrays.append(cur)
    for a in arrays:
        start = a[0]
        lo, hi = base + start - 0x80, base + start
        sites = 0
        wl = 0
        for i, w in enumerate(words):
            if lo <= w <= hi:
                wl += 1
                L = i * 4
                for A in range(max(0, L - 1024 - 8), L, 2):
                    x = d[A] | d[A + 1] << 8
                    if x >> 12 == 0xD and (A & ~3) + 4 + 4 * (x & 0xFF) == L:
                        sites += 1
        ps = per_stride[(S, W)]
        ps['arrays'] += 1
        ps['files'].add(src)
        ps['sites'] += sites
        ps['words'] += wl
        if wl == 0:
            ps['noptr'] += 1
        rows.append((src, S, W, len(a), start, wl, sites))
for r in rows:
    print('%-30s S=%-4d W=%-3d n=%-5d start=%#07x literal_words=%-2d loader_sites=%d' % r)
print()
for (S, W), ps in sorted(per_stride.items()):
    print('S=%-4d W=%-3d arrays=%-3d files=%-3d literal_words=%-4d loader_sites=%-4d arrays_without_pointer=%d' % (S, W, ps['arrays'], len(ps['files']), ps['words'], ps['sites'], ps['noptr']))
