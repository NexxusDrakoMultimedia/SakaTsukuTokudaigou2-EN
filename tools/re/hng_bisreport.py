"""hng: one table of the bisect discs from their build logs (flags, applied/failed, files changed, verify_disc, digest).
usage: hng_bisreport.py [--md]"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FLAGS = {
 'prop7': 'standard (all on)', 'bis_a': 'prop7 + --money-format off', 'bis_b': 'prop7 + --club-guard off', 'bis_c': 'prop7 + empty textures dir',
 'bis_d': 'prop7 + --proportional-font off', 'bis_e': 'money off + guard off + no textures (near baseline)',
 'bis_f': 'bis_e + jp money ON', 'bis_g': 'bis_e + club guard ON', 'bis_h': 'bis_e + all 235 textures ON',
 'bis_i': 'bis_e but --money-style western (the money code of prop4)', 'bis_j': 'bis_e + 7 overlay-embedded textures (FLOW_PRG/*.BIN)',
 'bis_k': 'bis_e + EVENT/ textures (E003.DAT, REPORT.DAT)', 'bis_l': 'bis_e + ETC_DATA/ + ATFIRST/ textures (195)',
 'bis_m': 'bis_e + GAME2/, TRAINING/, FLOW_PRG/*.ZAR textures (22)', 'bis_n': 'bis_e + --proportional-font off (text + layout patches only)'}
rows = []
for n in FLAGS:
    p = os.path.join(ROOT, 'build', 'trial', n + '.log')
    if not os.path.isfile(p):
        rows.append((n, FLAGS[n], 'no log', '', '', '', '')); continue
    t = open(p, encoding='utf-8', errors='replace').read()
    m = re.search(r'applied (\d+) strings .*failed (\d+), skipped (\d+)', t)
    f = re.search(r'files changed: (\d+)', t)
    v = re.search(r'verify_disc \S+: (OK|FAIL)[^\n]*', t)
    dg = re.search(r'patch digest (\w{40})', t)
    mo = re.search(r'money format[^\n]*?(\(\w+ style\))?: (\d+) overlays hooked[^\n]*\((\d+) bytes\)', t)
    rows.append((n, FLAGS[n], '%s applied, %s failed, %s skipped' % m.groups() if m else '?', f.group(1) if f else '?',
                 v.group(0).split(': ', 1)[1] if v else '?', dg.group(1)[:10] if dg else '?', 'cave %s B' % mo.group(3) if mo else 'no money cave'))
for r in rows:
    print(' | '.join(str(x) for x in r))
