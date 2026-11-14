# SPDX-License-Identifier: GPL-3.0-or-later
"""skl_scan DIR: look for Japanese / original bytes in a committed-form tree (l10n/).  Read only.
Reports every non-ASCII character by Unicode block (with counts and a sample record id), runs of <XX> byte tokens with
high bytes in en/why/ctx, hex runs longer than 32 digits outside jah, and long base64-like runs."""
import json
import os
import re
import sys
import unicodedata

root = sys.argv[1]
chars = {}
hi_tok = []
longhex = []
b64 = []
files = 0
TOK = re.compile(r'(?:<[89A-F][0-9A-F]>){2,}')
HEX = re.compile(r'[0-9a-fA-F]{33,}')
B64 = re.compile(r'[A-Za-z0-9+/=]{40,}')
fieldlen = {}
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        if not f.endswith('.jsonl'):
            continue
        files += 1
        raw = open(p, 'rb').read()
        try:
            txt = raw.decode('utf-8')
        except UnicodeDecodeError as e:
            print('NOT UTF-8:', p, e)
            continue
        if b'\r' in raw:
            print('CR in', p)
        for ln, line in enumerate(txt.split('\n'), 1):
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                print('non-json line', p, ln, line[:60])
                continue
            for ch in set(line):
                if ord(ch) > 0x7e or (ord(ch) < 0x20):
                    try:
                        nm = unicodedata.name(ch)
                    except ValueError:
                        nm = '?'
                    e = chars.setdefault(ch, [0, nm, '%s:%d' % (os.path.basename(p), ln)])
                    e[0] += 1
            if not isinstance(o, dict):
                continue
            for k, v in o.items():
                if not isinstance(v, (str, list)):
                    continue
                vs = v if isinstance(v, list) else [v]
                for s in vs:
                    if not isinstance(s, str):
                        continue
                    fieldlen[k] = max(fieldlen.get(k, 0), len(s))
                    if k != 'jah' and HEX.search(s):
                        longhex.append((p, ln, k, s[:60]))
                    if TOK.search(s):
                        hi_tok.append((os.path.basename(p), ln, k, s[:60]))
                    if k not in ('jah',) and B64.search(s):
                        b64.append((os.path.basename(p), ln, k, s[:60]))
print('files', files)
print('distinct non-ASCII/control chars:', len(chars))
for ch, (n, nm, where) in sorted(chars.items(), key=lambda x: ord(x[0])):
    print('  U+%04X %-8s lines=%-6d %s  e.g. %s' % (ord(ch), repr(ch), n, nm, where))
print('high-byte <XX> runs:', len(hi_tok), hi_tok[:5])
print('long hex outside jah:', len(longhex), longhex[:5])
print('base64-like:', len(b64), b64[:5])
print('max field lengths:', {k: v for k, v in sorted(fieldlen.items(), key=lambda x: -x[1])[:10]})
