"""Timing / ratio check of texinject's optimal-parse encoders against the original stream and bzlib greedy.
python -I -X utf8 tools/re/texinject/opt_timing.py"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bzlib      # noqa: E402
import texinject as T  # noqa: E402

cases = [('ATFIRST/BAR.TBD', '#0'), ('ATFIRST/BAR.TBD', '#1'), ('ATFIRST/LOGO.DAT', '#0'), ('ATFIRST/TITLE.DAT', '#9'),
         ('ATFIRST/TITLE.DAT', '#3'), ('ETC_DATA/HELP.DAT', '#0')]
for f, tid in cases:
    d = T._as_bytes(f)
    t = T.resolve(d, tid)
    tab, i = t['table'], t['index']
    plain = T.tbd_plain(d, tab, i)
    s, e = T._rec_slot(d, tab, i)
    r = tab.recs[i]
    comp = r['comp']
    if comp == 0:
        continue
    m = '-bz--' if comp == 2 else '-bzw-'
    t0 = time.time()
    g = bzlib.compress(plain, m)
    t1 = time.time()
    o = T.compress_bz_opt(plain) if comp == 2 else T.compress_bzw_opt(plain)
    t2 = time.time()
    print('%-22s %-3s %s plain=%-7d slot=%-6d greedy=%-6d (%.1fs) optimal=%-6d (%.1fs) fits: greedy=%s opt=%s' % (
        f, tid, m, len(plain), e - s, len(g), t1 - t0, len(o), t2 - t1, len(g) <= e - s, len(o) <= e - s))
