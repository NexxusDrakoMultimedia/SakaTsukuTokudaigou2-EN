"""Second analysis pass: optimal-repack model, shortening sensitivity, name ladder, headline table.
python -I -X utf8 tools/re/capacity/ratio/analyze2.py > tools/re/capacity/ratio/analyze2_out.txt"""
import os, sys, json, random, collections, re
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, 'tools/re/capacity/ratio')
from common import *

rows = [r for r in load() if is_ov(r)]
byid = {r['id']: r for r in rows}
sample = [json.loads(l) for l in open('tools/re/capacity/ratio/sample.jsonl', encoding='utf8') if json.loads(l)['skip'] is False]
CATS = ['prose_meeting', 'prose_news', 'prose_event', 'prose_training', 'prose_other', 'help', 'label', 'name', 'place', 'numunit']
for s in sample:
    r = byid[s['id']]
    s['jb'] = jb(s['ja']); s['eb'] = eb(s['en']); s['mov'] = movable(r)
pop = {}
for c in CATS:
    P = [r for r in rows if category(r) == c]
    M = [r for r in P if movable(r)]
    pop[c] = dict(n=len(P), jb=sum(jb(r['ja']) for r in P), mov_n=len(M), mov_jb=sum(jb(r['ja']) for r in M),
                  mov_maxb=sum(r['max_bytes'] for r in M), pin_n=len(P) - len(M), pin_jb=sum(jb(r['ja']) for r in P if not movable(r)))


def repack(X, pad_rate, scale=1.0, extra_budget=0.0):
    """X: sampled movable strings of one category.  pad_rate = (sum max_bytes - sum jb)/sum jb of the category's
    movable POPULATION.  Switch strings JP->EN in ascending cost (eb*scale - jb) while the free pool
    (pad_rate * sum jb + savings) is not exhausted.  Returns (fraction of strings, fraction of JP bytes) translatable."""
    free = pad_rate * sum(s['jb'] for s in X) + extra_budget * sum(s['jb'] for s in X)
    items = sorted(X, key=lambda s: s['eb'] * scale - s['jb'])
    n = b = 0
    for s in items:
        cost = s['eb'] * scale - s['jb']
        if free - cost >= 0:
            free -= cost; n += 1; b += s['jb']
        else:
            break   # sorted ascending: nothing later is cheaper
    return n / len(X), b / sum(s['jb'] for s in X)


def inplace(X, scale=1.0):
    return sum(1 for s in X if s['eb'] * scale <= s['max_bytes']) / len(X), sum(s['jb'] for s in X if s['eb'] * scale <= s['max_bytes']) / sum(s['jb'] for s in X)


print('REPACK MODEL (best case: perfect packing of all movable strings of a category into their own pooled slots, strings translated greedily cheapest-first).')
print('scale = factor applied to my English bytes (1.00 = my natural translations; <1 = editing/abbreviating harder)')
print('%-15s %5s | pad%%  |' % ('category', 'mov n') + '  '.join('s=%.2f in-place / repacked (rec%%)' % s for s in (1.0, 0.9, 0.8, 0.7)))
tab = {}
for c in CATS:
    Xm = [s for s in sample if s['cat'] == c and s['mov']]
    Xp = [s for s in sample if s['cat'] == c and not s['mov']]
    p = pop[c]
    pad_rate = (p['mov_maxb'] - p['mov_jb']) / p['mov_jb'] if p['mov_jb'] else 0
    line = '%-15s %5d | %5.1f |' % (c, len(Xm), 100 * pad_rate)
    for sc in (1.0, 0.9, 0.8, 0.7):
        if Xm:
            ip = inplace(Xm, sc)[0]; rp = repack(Xm, pad_rate, sc)[0]
        else:
            ip = rp = 0
        tab[(c, sc)] = (ip, rp)
        line += '  %5.1f / %5.1f           ' % (100 * ip, 100 * rp)
    print(line)

print()
print('POPULATION-WEIGHTED HEADLINE (all FLOW_PRG + ATFIRST overlay records = %d, JP bytes %d)' % (sum(p['n'] for p in pop.values()), sum(p['jb'] for p in pop.values())))
print('classes: A = fits in own slot; B = fits only if repacked (movable strings, ideal packing); C = needs extra memory / shortening / stays Japanese')
for sc in (1.0, 0.9, 0.8, 0.7):
    A = B = C = 0.0
    Ab = Bb = Cb = 0.0
    for c in CATS:
        p = pop[c]
        Xm = [s for s in sample if s['cat'] == c and s['mov']]
        Xp = [s for s in sample if s['cat'] == c and not s['mov']]
        # movable
        if p['mov_n'] and Xm:
            pad_rate = (p['mov_maxb'] - p['mov_jb']) / p['mov_jb']
            ipn, ipb = inplace(Xm, sc); rpn, rpb = repack(Xm, pad_rate, sc)
            rpn = max(rpn, ipn); rpb = max(rpb, ipb)
            A += p['mov_n'] * ipn; B += p['mov_n'] * (rpn - ipn); C += p['mov_n'] * (1 - rpn)
            Ab += p['mov_jb'] * ipb; Bb += p['mov_jb'] * (rpb - ipb); Cb += p['mov_jb'] * (1 - rpb)
        elif p['mov_n']:   # no movable sample in category: assume category-wide rates
            Xa = [s for s in sample if s['cat'] == c]
            ipn, ipb = inplace(Xa, sc)
            A += p['mov_n'] * ipn; C += p['mov_n'] * (1 - ipn); Ab += p['mov_jb'] * ipb; Cb += p['mov_jb'] * (1 - ipb)
        # pinned: in place only
        if p['pin_n']:
            Xq = Xp if Xp else [s for s in sample if s['cat'] == c]
            ipn, ipb = inplace(Xq, sc)
            A += p['pin_n'] * ipn; C += p['pin_n'] * (1 - ipn); Ab += p['pin_jb'] * ipb; Cb += p['pin_jb'] * (1 - ipb)
    N = sum(p['n'] for p in pop.values()); Bt = sum(p['jb'] for p in pop.values())
    print('scale %.2f: records A %.1f%% B %.1f%% C %.1f%% | JP-byte-weighted A %.1f%% B %.1f%% C %.1f%%' % (sc, 100 * A / N, 100 * B / N, 100 * C / N, 100 * Ab / Bt, 100 * Bb / Bt, 100 * Cb / Bt))

# prose-only headline (what a reader actually reads), no names/places/labels
print()
pc = ['prose_meeting', 'prose_news', 'prose_event', 'prose_training', 'prose_other', 'help']
for sc in (1.0, 0.9, 0.8, 0.7):
    A = B = C = Ab = Bb = Cb = 0.0
    for c in pc:
        p = pop[c]
        Xm = [s for s in sample if s['cat'] == c and s['mov']]
        Xp = [s for s in sample if s['cat'] == c and not s['mov']]
        pad_rate = (p['mov_maxb'] - p['mov_jb']) / p['mov_jb']
        ipn, ipb = inplace(Xm, sc); rpn, rpb = repack(Xm, pad_rate, sc); rpn = max(rpn, ipn); rpb = max(rpb, ipb)
        A += p['mov_n'] * ipn; B += p['mov_n'] * (rpn - ipn); C += p['mov_n'] * (1 - rpn)
        Ab += p['mov_jb'] * ipb; Bb += p['mov_jb'] * (rpb - ipb); Cb += p['mov_jb'] * (1 - rpb)
        if p['pin_n']:
            ipn, ipb = inplace(Xp or [s for s in sample if s['cat'] == c], sc)
            A += p['pin_n'] * ipn; C += p['pin_n'] * (1 - ipn); Ab += p['pin_jb'] * ipb; Cb += p['pin_jb'] * (1 - ipb)
    N = sum(pop[c]['n'] for c in pc); Bt = sum(pop[c]['jb'] for c in pc)
    print('PROSE+HELP only, scale %.2f: (n=%d, %d JP bytes) records A %.1f%% B %.1f%% C %.1f%% | bytes A %.1f%% B %.1f%% C %.1f%%' % (sc, N, Bt, 100 * A / N, 100 * B / N, 100 * C / N, 100 * Ab / Bt, 100 * Bb / Bt, 100 * Cb / Bt))

# break-even scale per category (pooled ratio): EN must shrink to pool/JP
print()
print('BREAK-EVEN: scale at which pooled English == pooled capacity of the category (movable strings), and the required cut')
for c in CATS:
    X = [s for s in sample if s['cat'] == c and s['mov']]
    p = pop[c]
    if not X:
        continue
    ratio = sum(s['eb'] for s in X) / sum(s['jb'] for s in X)
    cap = p['mov_maxb'] / p['mov_jb']
    print('%-15s EN/JP=%.3f capacity/JP=%.3f -> scale %.3f (cut %.1f%%)' % (c, ratio, cap, cap / ratio, 100 * (1 - cap / ratio)))

# names ladder: Given Family -> G. Family -> Family
print()
nm = [s for s in sample if s['cat'] == 'name']
fit_full = sum(s['eb'] <= s['max_bytes'] for s in nm)
def ladder(s):
    en = s['en']
    if len(en) + 1 <= s['max_bytes']:
        return 0
    g, f = en.split(' ', 1)
    if len(g[0] + '. ' + f) + 1 <= s['max_bytes']:
        return 1
    if len(f) + 1 <= s['max_bytes']:
        return 2
    return 3
lv = collections.Counter(ladder(s) for s in nm)
print('NAMES (n=%d, 14-byte pinned fields): full "Given Family" fits %d (%.0f%%); with ladder -> "G. Family" %d more; -> "Family" only %d more; still too long %d' % (
    len(nm), fit_full, 100 * fit_full / len(nm), lv[1], lv[2], lv[3]))
print('   max_bytes values in name sample:', dict(collections.Counter(s['max_bytes'] for s in nm)))
pl = [s for s in sample if s['cat'] == 'place']
print('PLACES (n=%d): max_bytes values %s; fit %d' % (len(pl), dict(collections.Counter(s['max_bytes'] for s in pl)), sum(s['eb'] <= s['max_bytes'] for s in pl)))
# place without suffix
def nosuf(en):
    return re.sub(r'-(gun|cho|mura)$', '', en)
print('   places that fit if the -gun/-cho/-mura suffix were dropped: %d' % sum(len(nosuf(s['en'])) + 1 <= s['max_bytes'] for s in pl))
# chars per JP char
print()
print('EN bytes per JP character (visible chars): ' + ', '.join('%s %.2f' % (c, sum(s['eb'] for s in sample if s['cat'] == c) / sum(nchars(s['ja']) for s in sample if s['cat'] == c)) for c in CATS))
