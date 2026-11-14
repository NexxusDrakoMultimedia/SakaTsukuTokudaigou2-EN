"""l10 survey 2: serialisation style and key order per translation/*.jsonl line (read-only)."""
import collections
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STY = {'compact': (',', ':'), 'spaced': (', ', ': ')}
allorders = collections.Counter()
nonjp_ctx = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')) + glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl'))):
    raw = open(p, 'rb').read()
    crlf = b'\r\n' in raw
    endnl = raw.endswith(b'\n')
    st = collections.Counter()
    orders = collections.Counter()
    bad = 0
    ctxjp = 0
    for line in raw.decode('utf-8').split('\n'):
        if not line:
            continue
        r = json.loads(line)
        orders[tuple(r)] += 1
        allorders[tuple(r)] += 1
        m = [k for k, s in STY.items() if json.dumps(r, ensure_ascii=False, separators=s) == line]
        if not m:
            bad += 1
        else:
            st[m[0]] += 1
        c = r.get('ctx') or ''
        if any(ord(ch) > 0x7f for ch in c):
            ctxjp += 1
    nonjp_ctx += ctxjp
    print('%-45s crlf=%s endnl=%s styles=%s bad=%d orders=%d ctxjp=%d' % (os.path.relpath(p, ROOT), crlf, endnl, dict(st), bad, len(orders), ctxjp))
print('ctx with non-ascii total', nonjp_ctx)
for k, v in allorders.most_common():
    print(v, k)
