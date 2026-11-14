# SPDX-License-Identifier: GPL-3.0-or-later
"""skl_fixjp: rewrite the JP_RE line of tools/l10n.py with a wider range (ASCII source, backslash-u escapes)."""
import os

BS = chr(92)
p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'l10n.py')
lines = open(p, encoding='utf-8', newline='').read().split('\n')
rng = ['2e80-33ff', '3400-4dbf', '4e00-9fff', 'ac00-d7af', 'f900-faff', 'fe30-fe4f', 'ff00-ffef']
rng2 = ['1b000-1b16f', '1f200-1f2ff', '20000-2ffff']


def esc(a, w):
    return BS + 'u' + a.rjust(4, '0') if w == 4 else BS + 'U' + a.rjust(8, '0')


body = ''
for r in rng:
    a, b = r.split('-')
    body += esc(a, 4) + '-' + esc(b, 4)
for r in rng2:
    a, b = r.split('-')
    body += esc(a, 8) + '-' + esc(b, 8)
for i, ln in enumerate(lines):
    if ln.startswith('JP_RE = '):
        lines[i] = "JP_RE = re.compile('[" + body + "]')"
        break
else:
    raise SystemExit('JP_RE not found')
open(p, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
print(lines[i])
