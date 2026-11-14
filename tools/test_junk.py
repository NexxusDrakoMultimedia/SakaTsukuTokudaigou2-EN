"""Junk-orphan guard: no orphan record with placeholder English may be applied (docs/hang-investigation.md s0).
run: python -I -X utf8 tools/test_junk.py
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_patch  # noqa: E402

fails = 0


def check(name, cond):
    global fails
    print(('ok   ' if cond else 'FAIL ') + name)
    if not cond:
        fails += 1


check('placeholder "-" is junk', build_patch.is_junk_orphan({'orphan': True, 'en': '-'}))
check('placeholder "Bow" is junk', build_patch.is_junk_orphan({'orphan': True, 'en': 'Bow'}))
check('"????" is junk', build_patch.is_junk_orphan({'orphan': True, 'en': '????'}))
check('real word is not junk', not build_patch.is_junk_orphan({'orphan': True, 'en': 'Chat'}))
check('pointer record "-" is not junk', not build_patch.is_junk_orphan({'en': '-'}))
check('blank en is not junk', not build_patch.is_junk_orphan({'orphan': True, 'en': ''}))

bad = []
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        if build_patch.is_junk_orphan(r):
            bad.append(r['id'])
check('translation/*.jsonl has no junk orphan record (%d found)' % len(bad), not bad)
print('FAILED %d' % fails if fails else 'all passed')
sys.exit(1 if fails else 0)
