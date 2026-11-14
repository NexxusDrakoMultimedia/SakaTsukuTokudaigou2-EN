"""skh: run the club-name composer EXACTLY as built in a trial disc, for every overlay that carries one (EVENT first).

usage: skh_evclubs.py DISC [OVERLAY ...]       (default EVENT BPMATCH HOMETOWN)
fin_clubs.py only ran BPMATCH and HOMETOWN; EVENT (the overlay of the hang screen) has its own copy of the composer at a
different address.  This reads the overlay from the disc and runs ovf_sim.Composer + run_all on it.
Read-only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import discbuild as D            # noqa: E402
import ovf_sim as OVF            # noqa: E402


def main(argv):
    name = argv[1]
    names = argv[2:] or ['EVENT', 'BPMATCH', 'HOMETOWN']
    src = D.Source(os.path.join(ROOT, 'build', 'trial', name), name)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    first = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    rc = 0
    for n in names:
        r = files['/FLOW_PRG/%s.BIN' % n]
        im = src.read(r.lba, r.size)
        try:
            comp = OVF.Composer(im, first)
        except Exception as e:
            print('%s: Composer() failed: %r' % (n, e))
            rc = 1
            continue
        res = OVF.run_all(comp, True)
        print('%s: runs %d problems %d %s  max len %s' % (n, res['runs'], len(res['problems']), res['problems'][:3], max(res['lens'])))
        rob = OVF.robustness(comp)
        print('%s: robustness problems %d %s' % (n, len(rob), rob[:3]))
        rc |= 1 if res['problems'] or rob else 0
    src.close()
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
