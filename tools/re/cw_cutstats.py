"""Composed club-name cut statistics (town short + ' ' + club word) with the club-name guard rule (tools/re/ovf_sim.reference).
Two pools: the one inside the built HOMETOWN.BIN image (plain build: slot-fit forms) and the art spellings of
translation/clubwords_art.tsv (the pool of a `--refit on` build).  usage: python -I -X utf8 tools/re/cw_cutstats.py HOMETOWN.BIN"""
import csv, os, sys
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))
import ovf_pairs as OP
import ovf_sim as OS

d = open(sys.argv[1], 'rb').read()
towns, prefs, pool = OP.tables(d)
art = [w for w in pool]
for row in csv.reader(open(os.path.join(ROOT, 'translation', 'clubwords_art.tsv'), encoding='utf8'), delimiter='\t'):
    if row[0].isdigit():
        art[int(row[0])] = row[3].encode('ascii')
print('pool of the image :', [w.decode('cp932') for w in pool[1:]])
print('pool of the art   :', [w.decode('cp932') for w in art[1:]])


def stats(label, words):
    tot = cut = wcut = 0
    bylen = Counter(); bycut = Counter(); res = Counter(); wlist = Counter()
    for t in towns:
        for w in words[1:]:
            r = OS.reference(t, w, False)
            tot += 1
            bylen[len(w)] += 1
            if not r.startswith(t + b' ' + w):
                pass
            if t + b' ' + w != r:
                cut += 1; bycut[len(w)] += 1
            if not r.endswith(b' ' + w):
                wcut += 1; wlist[w] += 1
            res[len(r)] += 1
    print('\n== %s: %d pairs, cut %d (%.1f %%), word itself cut %d, longest %d' % (label, tot, cut, 100.0 * cut / tot, wcut, max(res)))
    print('   cut share by word length:', ', '.join('%d: %.1f %%' % (l, 100.0 * bycut[l] / bylen[l]) for l in sorted(bylen)))
    print('   result lengths:', sorted(res.items()))
    print('   words that lose letters in a composed name:', {k.decode(): v for k, v in wlist.items()})


stats('image pool (plain build)', pool)
stats('art pool (refit build)', art)
