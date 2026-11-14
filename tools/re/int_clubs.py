"""int: stage-3 integrator check of the club-name guard on the REAL overlays of a built dump.
usage: int_clubs.py DUMPDIR     (DUMPDIR/FLOW_PRG/BPMATCH.BIN and HOMETOWN.BIN from build_patch.py --dump)
Runs the patched composer of BPMATCH in the SH-4 simulator for all 1248 x 55 town + word pairs (modes 0/1) and 49 x 55 prefecture
pairs (modes 2/3), HOMETOWN's popup join for the same pairs in both orders, and prints: problems (must be 0), length distribution,
cut statistics, and 20 examples chosen to include long town + long word."""
import os
import sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ovf_sim as OVF  # noqa: E402


def show(title, r):
    towns, pool = r['towns'], r['pool']
    print('==', title)
    print('runs %d, problems %d %s' % (r['runs'], len(r['problems']), r['problems'][:2] or ''))
    n = len(towns) * len(pool)
    cut = r['cut']['town']
    print('town+word pairs %d: cut %d (%.1f%%), unchanged %d' % (n, cut, 100.0 * cut / n, n - cut))
    lens = r['lens']
    print('result length distribution (town pairs, mode 0):', dict(sorted(lens.items())), 'max', max(lens))
    print('cut share by word length:', {L: '%.1f%%' % (100.0 * sum(v for w, v in r['cut_by_word'].items() if len(w) == L) /
                                                       (len(towns) * sum(1 for w in pool if len(w) == L))) for L in sorted({len(w) for w in pool})})
    if 'pref' in r:
        print('prefecture + word (mode 2): %d pairs, cut %d' % (r['pref']['pairs'], r['pref']['cut']))
    if 'pref_pairs' in r['cut']:
        print('prefecture + word (popup): %d pairs, cut %d' % (r['cut']['pref_pairs'], r['cut']['pref']))


def examples(r):
    towns, pool = r['towns'], r['pool']
    out = []
    # all cut examples are only the first 400 collected; rebuild a spread from the full set via the reference rule
    cand = []
    for t in towns:
        for w in pool:
            res = OVF.reference(t, w, False, True)
            if res != t + b' ' + w:
                cand.append((len(t) + len(w), len(t), len(w), t, w, res))
    cand.sort(reverse=True)
    pick = cand[:8]                                    # longest town + longest word
    step = max(1, (len(cand) - 8) // 12)
    pick += cand[8::step][:12]
    for c in pick[:20]:
        out.append('%-14s + %-9s -> %s' % (c[3].decode('ascii', 'replace'), c[4].decode('ascii', 'replace'), c[5].decode('ascii', 'replace')))
    return out


def main():
    dump = sys.argv[1]
    first = open(os.path.join(OVF.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    im = open(os.path.join(dump, 'FLOW_PRG', 'BPMATCH.BIN'), 'rb').read()
    comp = OVF.Composer(im, first)
    r = OVF.run_all(comp, True)
    show('BPMATCH composer (real overlay of %s)' % dump, r)
    print('robustness problems:', len(OVF.robustness(comp)))
    im2 = open(os.path.join(dump, 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
    pj = OVF.popup_mode(im2)
    if pj is None:
        print('HOMETOWN: popup join is NOT on the composer address: guard missing')
        return 1
    r2 = OVF.run_all_popup(pj, True)
    show('HOMETOWN popup join', r2)
    print('20 examples (town + word -> composed name):')
    for e in examples(r):
        print('  ' + e)
    return 1 if r['problems'] or r2['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
