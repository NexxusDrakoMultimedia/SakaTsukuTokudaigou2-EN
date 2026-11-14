"""Verify the gun-less composition names on built images (build_patch.py --dump DIR), composer executed in the SH-4 simulator.

    python -I -X utf8 tools/re/hnm/hnmg_verify.py DUMP_NEW [DUMP_BASELINE]

Checks on DUMP_NEW/FLOW_PRG/HOMETOWN.BIN: (1) no pointer-table town string ends with '-gun'; (2) every district's gun-less name is
what the composer outputs for all 4 modes (town+pool, pool+town) in the simulator, for all 1270 towns with 2 pool words, and the
simulator output equals the analytic 'town pool' / 'pool town' string; (3) the 126-byte record name fields still hold the full 'X-gun'
names; (4) composed-name length distribution (all 1270 towns x all 55 pool words, and prefecture clubs).  With DUMP_BASELINE it also
lists the files that differ and prints the baseline distribution.  Exit 1 on a failed check.
"""
import collections
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hnm_sim_club as C  # noqa: E402

ROOT = C.ROOT
FAIL = []
STEP = int(os.environ.get("HNMG_STEP", "6"))


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        FAIL.append(msg)


def cstr(img, off):
    return img[off:img.index(b'\0', off)]


def strings(img, tbl, n, first):
    return [cstr(img, struct.unpack_from('<I', img, tbl + 4 * (k + first))[0] - C.BASE).decode('cp932', 'replace') for k in range(n)]


def town_ja():
    """1-based town index -> Japanese name, read from the ORIGINAL overlay (the jsonl omits indices that share a string)"""
    orig = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
    return {k + 1: t for k, t in enumerate(strings(orig, C.TOWN_TBL, 1270, 1))}


def dist(towns, prefs, pool):
    d = collections.Counter()
    for t in towns:
        for w in pool:
            d[len(t) + 1 + len(w)] += 1
    p = collections.Counter()
    for t in prefs:
        for w in pool:
            p[len(t) + 1 + len(w)] += 1
    return d, p


def show(label, d):
    tot = sum(d.values())
    print('  %s: n=%d min=%d max=%d mean=%.2f  >24: %d  >20: %d  >16: %d' % (label, tot, min(d), max(d), sum(k * v for k, v in d.items()) / tot,
          sum(v for k, v in d.items() if k > 24), sum(v for k, v in d.items() if k > 20), sum(v for k, v in d.items() if k > 16)))
    print('    ' + ' '.join('%d:%d' % (k, d[k]) for k in sorted(d)))


def load(dump):
    img = open(os.path.join(dump, 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
    return img, strings(img, C.TOWN_TBL, 1270, 1), strings(img, C.PREF_TBL, 50, 0), strings(img, C.POOL_TBL, 55, 0)


def main():
    new = sys.argv[1]
    img, towns, prefs, pool = load(new)
    ja = town_ja()
    check(len(ja) == 1270, 'original HOMETOWN overlay has 1270 pointer-table town strings')
    check(not any(t.endswith('-gun') for t in towns), 'no pointer-table town string ends with -gun (%d towns)' % len(towns))
    nd = [i for i in range(1270) if ja.get(i + 1, '')[-1:] in '郡群']
    check(len(nd) == 509 or len(nd) > 400, '%d district (郡/群) towns in the table' % len(nd))
    print('  sample districts:', ', '.join('%s=%s' % (ja[i + 1], towns[i]) for i in nd[:6]))
    first = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    pi, pj = 0, 1
    wi = [i for i, w in enumerate(pool) if w.isascii()][:2]
    check(len(wi) == 2, 'pool words are English (%s)' % ', '.join(pool[i] for i in wi))
    bad = 0
    nsim = 0
    sample = sorted(set(nd[::STEP] + list(range(0, 1270, STEP * 5))))       # every STEP-th district + every 5*STEP-th town (sim is slow)
    for k in (i + 1 for i in sample):
        t = towns[k - 1]
        for w in wi[:1]:
            for mode, want in ((0, t + ' ' + pool[w]), (1, pool[w] + ' ' + t)):
                got = C.compose(img, first, k, pi, w, mode).decode('cp932', 'replace')
                nsim += 1
                if got != want:
                    bad += 1
                    if bad < 6:
                        print('   mismatch', k, ja.get(k), mode, repr(got), repr(want))
    check(bad == 0, 'simulator composer == analytic for %d runs (sampled towns x 1 pool word x modes 0/1)' % nsim)
    ok = 0
    nd = nd[::STEP]
    for i in nd:
        got = C.compose(img, first, i + 1, pi, wi[0], 0).decode('cp932', 'replace')
        ok += got == towns[i] + ' ' + pool[wi[0]] and '-gun' not in got
    check(ok == len(nd), 'composer output of %d sampled districts is gun-less (e.g. %s)' % (len(nd), C.compose(img, first, nd[0] + 1, pi, wi[0], 0).decode()))
    # the full names survive in the 126-byte records
    guns = len(re.findall(rb'[A-Za-z]-gun\0', img))
    check(guns >= len(nd) // 2, 'HOMETOWN image still holds %d full "X-gun" strings (126-byte list/header records)' % guns)
    d, p = dist(towns, prefs, pool)
    print('composed club-name lengths after (town+pool words):')
    show('town clubs', d)
    show('prefecture clubs (50 prefs)', p)
    if len(sys.argv) > 2:
        base = sys.argv[2]
        _, bt, bp, bpool = load(base)
        d0, p0 = dist(bt, bp, bpool)
        print('before:')
        show('town clubs', d0)
        show('prefecture clubs', p0)
        diffs = []
        for dp, _, fs in os.walk(new):
            for f in fs:
                a = os.path.join(dp, f)
                b = os.path.join(base, os.path.relpath(a, new))
                if not os.path.exists(b) or open(a, 'rb').read() != open(b, 'rb').read():
                    diffs.append(os.path.relpath(a, new).replace(os.sep, '/'))
        print('files differing from baseline: %d' % len(diffs))
        print('  ' + ' '.join(sorted(os.path.basename(x) for x in diffs)))
        print('  outside FLOW_PRG:', [x for x in diffs if not x.startswith('FLOW_PRG/')])
    print('FAILED %d' % len(FAIL) if FAIL else 'ALL OK')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
