"""s7r_art4 JOB [--write] [--scale N] : run an art4 job (tools/re/art4_specs*.py) with the s7r refit overrides applied (OVR below).
Scratch output goes to build/s7/r/a4 (not build/art4)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art4_run, art4_specs, art4_specs_b  # noqa
J = art4_specs.JOBS
art4_run.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'build', 's7', 'r', 'a4')


def setreg(job, rid, **kw):
    for r in J[job]['spec']['regions']:
        if r['id'] == rid:
            r.update(kw); return r
    raise KeyError(rid)


# ---- RECON 07589: bottom row 'Do Not Renew' / 'Finish Renewals' touched -> 'No Renewal' | 'Finish'
if 'recon' in J:
    setreg('recon', 'dontrenew', text='No Renewal', w=132, erase_rect=[2, 100, 144, 27])
    setreg('recon', 'finish', text='Finish', x=148, w=104, size=21, erase_rect=[146, 100, 110, 27])

# ---- YOUTH 10471: left column words must end before the right column starts (x 95..97)
if 'youth1' in J:
    setreg('youth1', 'midd', text='Mid Def.', w=88, erase_rect=[2, 66, 94, 32])
    setreg('youth1', 'dft', w=88, erase_rect=[2, 95, 94, 35])
    setreg('youth1', 'tactics', erase_rect=[1, 33, 94, 33])
    setreg('youth1', 'c_Policy', erase_rect=[95, 34, 99, 32])
    setreg('youth1', 'c_Pick Coach', x=99, w=94, erase_rect=[95, 67, 99, 32])
    setreg('youth1', 'c_Coach Check', x=99, w=94, size=19, erase_rect=[95, 96, 99, 34])

# ---- SS_PR1 hobby line 03836 / 03838 / 03840: keep it inside the plate (right line ends x 249)
for _n in ('pr2', 'pr4', 'pr6'):
    if _n in J:
        setreg(_n, 'val3', w=148)
if 'pr2' in J:
    setreg('pr2', 'val3', text='Snowboard, Marathon')

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    sc = 3
    if '--scale' in sys.argv:
        sc = int(sys.argv[sys.argv.index('--scale') + 1]); a = [x for x in a if x != str(sc)]
    for n in a:
        art4_run.run(n, sc, '--write' in sys.argv)
