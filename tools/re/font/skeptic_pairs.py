"""Bigram clearances (blank columns between any-ink of neighbours) at the live-test pitch, for lower-case pairs and ambiguous bigrams."""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import font as F  # noqa: E402
import numpy as np  # noqa: E402

lua = open(os.path.join(ROOT, 'tools', 'emu', 'fonttest.lua'), encoding='utf8').read()
TABLE = bytes.fromhex(re.search(r'local TABLE_HEX = "([0-9a-f]+)"', lua).group(1))
i0, i1, i2 = lua.index('local GLYPH_NEW'), lua.index('local GLYPH_OLD'), lua.index('local VARIANTS')
NEW = {int(k): bytes.fromhex(v) for k, v in re.findall(r'\[(\d+)\]="([0-9a-f]+)"', lua[i0:i1])}
half = F.Font.load(os.path.join(ROOT, 'extracted', 'FONT.BIN')).half()


def g(b):
    return NEW.get(b, half[F.half_index(b)])


def span(b, thr=1):
    c = (15 - np.array(F.nibbles(g(b)), dtype=np.int32).reshape(24, 12)).max(axis=0)
    nz = np.nonzero(c >= thr)[0]
    return int(nz[0]), int(nz[-1])


def gap(a, b, thr=1):
    return TABLE[ord(a)] - (span(ord(a), thr)[1] + 1) + span(ord(b), thr)[0]


lo = [chr(c) for c in range(0x61, 0x7B)]
z = [a + b for a in lo for b in lo if gap(a, b) == 0]
print('lower-case pairs with 0 blank columns (any ink):', len(z))
print(' '.join(z))
print('ambiguous bigrams (any-ink gap / strong-ink gap):')
for bg in ('cl', 'rn', 'ri', 'vv', 'll', 'il', 'li', 'ij', 'nn', 'rr', 'tt', 'fi', 'ft', 'ec', 'oo', 'ae', 'ou', 'wo', 'ww', 'mm', 'Il', 'II', 'lI', 'I,', 'l.', 'i.', 'W.', 'T.', 'y,', 'ky'):
    print('  %s %d / %d' % (bg, gap(bg[0], bg[1]), gap(bg[0], bg[1], 4)))
# worst case word frequency check: how often do 0-gap lower-case pairs occur in the real sample
import json  # noqa: E402
tot = zero = 0
from collections import Counter  # noqa: E402
cnt = Counter()
for l in open(os.path.join(ROOT, 'tools', 're', 'capacity', 'ratio', 'sample.jsonl'), encoding='utf8'):
    r = json.loads(l)
    if r['skip']:
        continue
    t = r['en_flat']
    for a, b in zip(t, t[1:]):
        if a in lo and b in lo:
            tot += 1
            if gap(a, b) == 0:
                zero += 1
                cnt[a + b] += 1
print('in the 605-string sample: %d lower-case letter pairs, %d (%.1f%%) have 0 blank columns; most common:' % (tot, zero, 100.0 * zero / tot), cnt.most_common(12))
# same under the ORIGINAL fixed 12 px pitch and unshifted glyphs
def gap0(a, b):
    sa, sb = [(lambda c: (lambda nz: (int(nz[0]), int(nz[-1])))(np.nonzero((15 - np.array(F.nibbles(half[F.half_index(ord(x))]), dtype=np.int32).reshape(24, 12)).max(axis=0) >= 1)[0]))(x) for x in (a, b)]
    return 12 - (sa[1] + 1) + sb[0]


zero0 = tot0 = 0
for l in open(os.path.join(ROOT, 'tools', 're', 'capacity', 'ratio', 'sample.jsonl'), encoding='utf8'):
    r = json.loads(l)
    if r['skip']:
        continue
    t = r['en_flat']
    for a, b in zip(t, t[1:]):
        if a in lo and b in lo:
            tot0 += 1
            if gap0(a, b) == 0:
                zero0 += 1
print('original fixed pitch, same pairs: %d (%.1f%%) with 0 blank columns' % (zero0, 100.0 * zero0 / tot0))

allc = [chr(c) for c in range(0x21, 0x7F)]
sg = {(a, b): gap(a, b, 4) for a in allc for b in allc}
print('strong-ink (coverage>=4) gap over all 94x94 pairs: min %d, pairs with gap 0: %d, gap 1: %d' % (min(sg.values()), sum(1 for v in sg.values() if v == 0), sum(1 for v in sg.values() if v == 1)))
print('  gap-0 strong pairs:', [a + b for (a, b), v in sg.items() if v == 0][:30])
z0 = [a + b for (a, b), v in sg.items() if v == 0]
print('  all strong gap-0 pairs have left glyph:', sorted(set(p[0] for p in z0)), 'count', len(z0))
print('  those whose left glyph is not 4:', [p for p in z0 if p[0] != '4'])
