"""ovf: the club-name inputs of an overlay image: town short table (1-based, 1248), prefecture table (50), club-word pool (55).
usage: ovf_pairs.py [IMAGE]   (default: the built dump build/ovf_dump/FLOW_PRG/HOMETOWN.BIN)  -> length distribution of town + ' ' + word"""
import os, struct, sys
from collections import Counter
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BASE = 0x8c2d0000
TOWN_TBL, N_TOWN = 0x43854, 1248
PREF_TBL, N_PREF = 0x42200, 50
POOL_TBL, N_POOL = 0x422c8, 55


def cstr(d, off):
    e = d.index(b'\0', off)
    return bytes(d[off:e])


def tables(d):
    def tab(t, n, first):
        out = []
        for k in range(first, first + n):
            p = struct.unpack_from('<I', d, t + 4 * k)[0] - BASE
            out.append(cstr(d, p))
        return out
    towns = tab(TOWN_TBL, N_TOWN, 1)
    prefs = tab(PREF_TBL, N_PREF, 0)
    pool = tab(POOL_TBL, N_POOL, 0)
    return towns, prefs, pool


def main():
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'build', 'ovf_dump', 'FLOW_PRG', 'HOMETOWN.BIN')
    d = open(p, 'rb').read()
    towns, prefs, pool = tables(d)
    print(len(towns), len(prefs), len(pool))
    print('pool words:', [w.decode('cp932', 'replace') for w in pool])
    print('towns sample:', [t.decode('cp932', 'replace') for t in towns[:5]], [t.decode('cp932', 'replace') for t in towns[-5:]])
    print('prefs:', [t.decode('cp932', 'replace') for t in prefs])
    lw = Counter(len(w) for w in pool)
    lt = Counter(len(t) for t in towns)
    print('word byte lengths', sorted(lw.items()))
    print('town byte lengths', sorted(lt.items()))
    tot = Counter()
    for t in towns:
        for w in pool:
            tot[len(t) + 1 + len(w)] += 1
    over = sum(v for k, v in tot.items() if k > 13)
    print('pairs', sum(tot.values()), 'over 13:', over)
    print(sorted(tot.items()))


if __name__ == "__main__":
    main()
