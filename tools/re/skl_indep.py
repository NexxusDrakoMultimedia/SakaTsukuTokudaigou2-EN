# SPDX-License-Identifier: GPL-3.0-or-later
"""skl_indep L10N_DIR EXTRACTED_DIR: independent re-check of jah (own code, not l10n.raw_of): for every record of the
FLOW_PRG/ATFIRST/1ST_READ/2_DP main files without fmt bcast/ini/bpinfo/gap, sha256(bytes to first NUL)[:16] == jah.
Also reports the distribution of how many records share a jah (dictionary-attack surface) and the number of short raw strings."""
import hashlib
import json
import os
import sys

l10n, ext = sys.argv[1], sys.argv[2]
ok = bad = skipped = 0
badl = []
short = 0
jahcount = {}
cache = {}
for fn in sorted(os.listdir(l10n)):
    if not fn.endswith('.jsonl'):
        continue
    lines = open(os.path.join(l10n, fn), encoding='utf-8').read().split('\n')
    head = json.loads(lines[0])
    if head['kind'] != 'main':
        continue
    for ln in lines[1:]:
        if not ln:
            continue
        o = json.loads(ln)
        jahcount[o['jah']] = jahcount.get(o['jah'], 0) + 1
        rid = o['id']
        if '#' not in rid:
            rid = head['src'] + '#' + rid
        src, off = rid.split('#')
        off = int(off, 16)
        fmt = o.get('fmt')
        if src == 'BCAST/BCAST.BIN' or src == 'DPETC/MESSAGE.INI' or src.endswith('BPINFO.BIN') or fmt == 'gap':
            skipped += 1
            continue
        if src not in cache:
            cache = {src: open(os.path.join(ext, *src.split('/')), 'rb').read()}
        d = cache[src]
        e = d.find(b'\0', off)
        raw = d[off:] if e < 0 else d[off:e]
        if len(raw) <= 4:
            short += 1
        if hashlib.sha256(raw).hexdigest()[:32] == o['jah']:
            ok += 1
        else:
            bad += 1
            if len(badl) < 10:
                badl.append(rid)
print('independent ok', ok, 'bad', bad, 'skipped', skipped, badl)
print('records', sum(jahcount.values()), 'distinct jah', len(jahcount), 'raw strings <=4 bytes', short)
