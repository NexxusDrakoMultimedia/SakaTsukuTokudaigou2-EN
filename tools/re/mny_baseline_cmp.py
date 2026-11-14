"""mny_baseline_cmp.py : the western money style must stay byte-compatible with the output recorded BEFORE the jp style existed.

    python -I -X utf8 tools/re/mny_baseline_cmp.py FILE.json
FILE.json was written by tools/re/pe_baseline.py `record` with the old moneypatch.  This script runs pe_baseline.collect() with
moneypatch's default style forced to 'western' and compares (the font entries are unchanged and compared too).  Exit 1 on a diff.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import moneypatch as MP      # noqa: E402
import pe_baseline as PB     # noqa: E402

_mk, _cb = MP.make_patches, MP.cave_bytes
MP.make_patches = lambda *a, **k: _mk(*a, style='western', **k)
MP.cave_bytes = lambda addr=MP.CAVE_ADDR, style='western': _cb(addr, style)

cur = json.loads(json.dumps(PB.collect(), default=str))
with open(sys.argv[1]) as f:
    old = json.load(f)
bad = [k for k in sorted(set(old) | set(cur)) if old.get(k) != cur.get(k)]
for k in bad:
    print('DIFF', k)
print('western identical to the old output' if not bad else '%d differences' % len(bad), '(%d entries)' % len(cur))
sys.exit(1 if bad else 0)
