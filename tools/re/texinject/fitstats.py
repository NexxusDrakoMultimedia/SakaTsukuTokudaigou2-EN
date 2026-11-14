"""How often does an UNCHANGED compressed texture re-encode into its original slot (zero-slack packing)?

    python -I -X utf8 tools/re/texinject/fitstats.py [--step K] [--max-plain N]

Walks the whole disc like texinject.list_textures, takes every K-th compressed texture (-bz-- / -bzw-) of the PVR members of
ZSARC containers, the TBD records of ZSARC members, whole-file TBD bundles and TBD tails (embedded tables too), and
compares the packed size of the original stream with bzlib's greedy encoder and with texinject's optimal parse.
Result lines: kind, n, greedy-fits, optimal-fits, mean ratio optimal/original, worst ratio."""
import os
import sys
import time
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bzlib      # noqa: E402
import texinject as T  # noqa: E402

step = int(sys.argv[sys.argv.index('--step') + 1]) if '--step' in sys.argv else 8
maxplain = int(sys.argv[sys.argv.index('--max-plain') + 1]) if '--max-plain' in sys.argv else 140000
stats = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0.0])
counter = 0
t0 = time.time()


def account(kind, plain, method, slot):
    global counter
    counter += 1
    if counter % step:
        return
    if len(plain) > maxplain:
        return
    g = bzlib.compress(plain, method)
    o = T.compress_bz_opt(plain) if method == '-bz--' else T.compress_bzw_opt(plain)
    o = o if len(o) < len(g) else g
    s = stats[kind]
    s[0] += 1
    s[1] += len(g) <= slot
    s[2] += len(o) <= slot
    r = len(o) / float(slot)
    s[3] += r
    s[4] = max(s[4], r)


ext = os.path.join(ROOT, 'extracted')
for root, dirs, files in os.walk(ext):
    dirs.sort()
    for fn in sorted(files):
        if fn in ('BCAST.BIN', '_filelist.tsv'):
            continue
        path = os.path.join(root, fn)
        rel = os.path.relpath(path, ext).replace('\\', '/')
        if rel.split('/')[0] in ('SSONG', 'SOUND', 'DPSS', 'DPWWW', 'BCAST'):
            continue
        d = open(path, 'rb').read()
        if bzlib.parse_member(d, 0, with_data=False) is not None:
            ms, tail = T.zs_members(d)
            for m in ms:
                if m.method != '-nc--' and m.orig_size >= 16:
                    plain = T.zs_plain(d, m)
                    if plain[:4] in (b'GBIX', b'PVRT'):
                        account('zs-pvr member ' + m.method, plain, m.method, m.packed_size)
                        continue
                    tab = T.read_table(plain, 0, 'file', True)
                    if tab is None:
                        continue
                if m.method == '-nc--':
                    plain = T.zs_plain(d, m)
                    tab = T.read_table(plain, 0, 'file', True)
                    if tab is None:
                        continue
                else:
                    tab = T.read_table(plain, 0, 'file', True)
                    if tab is None:
                        continue
                for i, r in enumerate(tab.recs):
                    if r['comp'] in (1, 2):
                        s, e = T._rec_slot(plain, tab, i)
                        account('zs-tbd record', T.tbd_plain(plain, tab, i), '-bzw-' if r['comp'] == 1 else '-bz--', e - s)
            tabs = T.scan_tables(d, tail, 'tail') if tail != len(d) else []
        else:
            tab0 = T.read_table(d, 0, 'file', True)
            tabs = [tab0] if tab0 else (T.scan_tables(d, 4, 'embedded') if len(d) < 8000000 else [])
        for tab in tabs:
            for i, r in enumerate(tab.recs):
                if r['comp'] in (1, 2):
                    s, e = T._rec_slot(d, tab, i)
                    account('tbd-' + tab.kind + ' record', T.tbd_plain(d, tab, i), '-bzw-' if r['comp'] == 1 else '-bz--', e - s)
print('step %d, plain <= %d bytes, %.0fs' % (step, maxplain, time.time() - t0))
print('%-26s %6s %12s %12s %9s %9s' % ('kind', 'n', 'greedy fits', 'optimal fits', 'mean o/orig', 'worst'))
for k in sorted(stats):
    n, g, o, sr, mx = stats[k]
    print('%-26s %6d %6d %4.0f%% %6d %4.0f%% %9.4f %9.4f' % (k, n, g, 100.0 * g / n, o, 100.0 * o / n, sr / n, mx))
