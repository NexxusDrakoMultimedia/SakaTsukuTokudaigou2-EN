"""tx5: byte-length distribution of the Japanese subtitle segments in BCAST.BIN (by folder).  python -I -X utf8 tools/re/tx5_bcast_lens.py"""
import os, sys, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textfmt_bcast as B

rows = B.read_headers()
by = collections.defaultdict(list)
for sec, h in rows:
    name, segs = B.header_segments(h)
    f = name.split('\\')[0]
    for k, (o, slot, raw) in enumerate(segs):
        by[f].append((len(raw), slot, len(segs), k, raw))
for f, v in sorted(by.items()):
    L = sorted(x[0] for x in v)
    n = len(L)
    print(f, n, 'median', L[n // 2], 'p90', L[int(n * .9)], 'p99', L[int(n * .99)], 'max', L[-1],
          '>56:', sum(1 for x in L if x > 56), '>64:', sum(1 for x in L if x > 64), '>80:', sum(1 for x in L if x > 80))
# slot vs text: how often is the text longer than 64 in a single-segment clip
big = [x for f in by for x in by[f] if x[0] > 64]
print('segments > 64 bytes:', len(big), 'of which slot sizes', collections.Counter(x[1] for x in big))
# non-last segment slot minus text length
gaps = collections.Counter()
for f in by:
    for ln, slot, ns, k, raw in by[f]:
        if k < ns - 1:
            gaps[slot - ln] += 1
print('slack of non-last segments (slot - len):', sorted(gaps.items())[:12])
ex = [x for f in by for x in by[f] if x[0] > 100][:3]
for x in ex:
    print(x[0], x[1], x[4].decode('cp932'))
