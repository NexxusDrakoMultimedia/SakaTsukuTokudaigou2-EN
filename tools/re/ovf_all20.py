"""ovf: run the bounded composer of every one of the 20 overlays of a built dump in the simulator.
usage: ovf_all20.py DUMPDIR [N]    DUMPDIR/FLOW_PRG/<NAME>.BIN (e.g. build/ovf_dump2 from build_patch.py --dry-run --dump); N random runs per overlay (default 4000)
Each overlay: random town / prefecture + word pairs in all four modes against the reference rule (write watching, canary, NUL, <= 13),
plus the out-of-range argument sweep; prints one line per overlay."""
import os
import random
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ovf_sim as OVF  # noqa: E402

LP = OVF.LP


def main():
    dump = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    first = open(os.path.join(OVF.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    bad_total = 0
    for name in LP.CLUB_OVERLAYS:
        im = open(os.path.join(dump, 'FLOW_PRG', name + '.BIN'), 'rb').read()
        pj = OVF.popup_mode(im)
        if pj:                                    # HOMETOWN: its composer copy is dead code, replaced by the popup join (sprintf convention)
            towns, prefs, pool = pj.tables()
            rnd = random.Random(7)
            problems = []
            for _ in range(n):
                t = rnd.randrange(1, len(towns) + 1)
                w = rnd.randrange(len(pool))
                wf = rnd.random() < 0.5
                r = pj.join(pool[w], towns[t - 1], 'a') if wf else pj.join(towns[t - 1], pool[w], 'b')
                want = OVF.reference(towns[t - 1], pool[w], wf, True)
                if r[0] != want or r[2] or r[3] or not r[5] or len(r[0]) > 13:
                    problems.append((t, w, wf, r[0], want))
            bad_total += len(problems)
            print('%-9s base %#x popup join %#x: %d runs, problems %d  %s' % (name, pj.base, pj.comp, n, len(problems), problems[:1] or ''))
            continue
        comp = OVF.Composer(im, first)
        towns, prefs, pool = comp.tables()
        rnd = random.Random(7)
        problems = []
        cut = 0
        for _ in range(n):
            w = rnd.randrange(len(pool))
            if rnd.random() < 0.7:
                _o, tr = OVF.check_one(comp, 'town', rnd.randrange(1, len(towns) + 1), w, rnd.choice([0, 1]), towns, prefs, pool, True, problems)
            else:
                _o, tr = OVF.check_one(comp, 'pref', rnd.randrange(0, 49), w, rnd.choice([2, 3]), towns, prefs, pool, True, problems)
            cut += tr
        pr = OVF.robustness(comp)
        bad_total += len(problems) + len(pr)
        print('%-9s base %#x composer %#x: %d runs, %d cut, problems %d, robustness problems %d  %s' % (
            name, comp.base, comp.comp, n, cut, len(problems), len(pr), problems[:1] or pr[:1] or ''))
    print('TOTAL PROBLEMS', bad_total)
    return 1 if bad_total else 0


if __name__ == '__main__':
    sys.exit(main())
