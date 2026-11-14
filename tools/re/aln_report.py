"""aln: numbers quoted in docs/layout-issues.md s10 (digit x per name with / without the fix; panel overflow per string).

    python -I -X utf8 tools/re/aln_report.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import test_alignfix as T  # noqa: E402

t = T.table()
c = T.ShirtNumberColumn()
for align in (True, False):
    xs = c.run_rows(align)
    print('align' if align else 'control', xs, 'distinct', sorted(set(xs.values())))
anchor = 612
rows = []
for s in ('Tokyo', 'Season', 'Average', 'Age 25', '1/2 yrs', '3100 man', 'DF', '0 apps', '0 goals', '0.00 pts', 'Isao Nakagawa', 'Hokkaido',
          'Kanagawa', '12 oku 3400 man', 'Yamanashi', 'GK', '2 yrs'):
    P = T.pen_of(t, s)
    old_over = P - 12 * len(s)
    len3 = (P + 2) // 3
    print('%-16s P=%3d plain=%3d old overflow %+d   new end offset %+d' % (s, P, 12 * len(s), old_over, 3 * len3 - P and (P - 3 * len3)))
print('overflowing strings:', sum(1 for s in ('Tokyo', 'Season', 'Average', 'Age 25', '1/2 yrs', '3100 man', 'DF', '0 apps', '0 goals', '0.00 pts', 'Isao Nakagawa', 'Hokkaido',
          'Kanagawa', '12 oku 3400 man', 'Yamanashi', 'GK', '2 yrs') if T.pen_of(t, s) > 12 * len(s)))
