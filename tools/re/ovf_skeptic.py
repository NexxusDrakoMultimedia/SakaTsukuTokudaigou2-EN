"""ovf_skeptic: independent property check of the bounded club-name composer over all pairs (does not use ovf_sim.reference).
usage: ovf_skeptic.py DUMPDIR   (DUMPDIR/FLOW_PRG/BPMATCH.BIN from build_patch.py --dry-run --dump)
Properties checked per run (modes 0/1 town+word, 2/3 prefecture+word):
  len <= 13, NUL after, caller canary untouched, word present in full (never lost), word at the front for odd modes and at the end for even ones,
  the town part is the town short (or a prefix of it, then ending in '.'), a cut town keeps >= 3 letters, the join is a single blank.
Then lists odd shapes: town part ending with '..', '-.', ' .', or with a dot right after a one-letter stub."""
import os
import sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ovf_sim as OVF  # noqa: E402


def check(out, town, word, word_first):
    errs = []
    if len(out) > 13:
        errs.append('len')
    if word_first:
        if not out.startswith(word + b' '):
            errs.append('word-not-first')
        part = out[len(word) + 1:]
    else:
        if not out.endswith(b' ' + word):
            errs.append('word-not-last')
        part = out[:-(len(word) + 1)] if out.endswith(b' ' + word) else out
    if part == town:
        kind = 'whole'
    elif part.endswith(b'.') and town.startswith(part[:-1]) and len(part) < len(town) + 1:
        kind = 'cut'
        if len(part) < 4:
            errs.append('stub<3')
    else:
        kind = 'bad'
        errs.append('town-part-not-prefix')
    return errs, kind, part


def main():
    dump = sys.argv[1]
    im = open(os.path.join(dump, 'FLOW_PRG', 'BPMATCH.BIN'), 'rb').read()
    comp = OVF.Composer(im)
    towns, prefs, pool = comp.tables()
    errs = Counter()
    kinds = Counter()
    odd = Counter()
    oddex = {}
    n = 0
    for kind, rng, modes in (('town', range(1, len(towns) + 1), (0, 1)), ('pref', range(0, 49), (2, 3))):
        for i in rng:
            short = towns[i - 1] if kind == 'town' else OVF.pref_short(i, prefs[i])
            for w, word in enumerate(pool):
                for mode in modes:
                    out, ret, bad, canary, steps, sp_ok = comp.compose(i if kind == 'town' else 0, i if kind == 'pref' else 0, w, mode)
                    n += 1
                    if bad or canary or not sp_ok or ret != len(out):
                        errs['mem/sp/ret'] += 1
                    e, k, part = check(out, short, word, bool(mode & 1))
                    for x in e:
                        errs[x] += 1
                        oddex.setdefault(x, (kind, i, short, word, out))
                    kinds[k] += 1
                    if k == 'cut':
                        for pat, nm in ((b'..', 'dotdot'), (b'-.', 'hyphen-dot'), (b' .', 'space-dot'), (b'/.', 'slash-dot')):
                            if pat in part:
                                odd[nm] += 1
                                oddex.setdefault(nm, (kind, i, short, word, out))
                    if k == 'whole' and short.endswith(b'.') is False and short[-1:] in (b' ', b'-'):
                        odd['whole-ends-sep'] += 1
    print('runs', n, 'errors', dict(errs), 'kinds', dict(kinds))
    print('odd shapes', dict(odd))
    for k, v in oddex.items():
        print(' ex', k, v)
    print('pool', [p.decode() for p in pool])
    print('max town short', max(len(t) for t in towns), 'town shorts containing space/hyphen/dot:',
          sum(1 for t in towns if any(c in t for c in b' -.')))
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
