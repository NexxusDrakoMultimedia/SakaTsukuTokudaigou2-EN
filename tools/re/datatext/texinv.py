"""Texture inventory: counts of textures per container/category (header parse only).
Output: tools/re/datatext/texinv.tsv (source, kind, index, fmt, datatype, w, h, comp, sha1-of-raw)
Run from repo root: python -I -X utf8 tools/re/datatext/texinv.py
"""
import os
import sys
import hashlib
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr

rows = []


def add(src, kind, i, t):
    rows.append((src, kind, i, t['fmt'], t['dt'], t['w'], t['h'], t.get('comp', ''), hashlib.sha1(t.get('raw', t.get('data', b''))).hexdigest()[:12]))


def visit(path, rel):
    d = open(path, 'rb').read()
    if d[:4] == b'GBIX' or d[:4] == b'PVRT':
        t = pvr.parse_pvr(d)
        if t:
            t['raw'] = t['data']
            add(rel, 'pvr', 0, t)
        return
    recs = pvr.parse_tbd(d)
    if recs:
        for i, r in enumerate(recs):
            add(rel, 'tbd', i, r)


for root in ('extracted', 'build/unpacked'):
    for dp, _, fns in os.walk(root):
        for fn in sorted(fns):
            p = os.path.join(dp, fn).replace(chr(92), '/')
            if 'BCAST' in p or fn.startswith('_') or p.startswith('extracted/FLOW_PRG') or p.startswith('extracted/SSONG'):
                continue
            if os.path.getsize(p) > 20_000_000:
                continue
            visit(p, p)
with open('tools/re/datatext/texinv.tsv', 'w', encoding='utf8') as f:
    for r in rows:
        f.write('\t'.join(map(str, r)) + '\n')
print(len(rows), 'textures;', len({r[-1] for r in rows}), 'unique raw payloads')
