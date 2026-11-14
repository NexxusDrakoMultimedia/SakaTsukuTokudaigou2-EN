"""l10 probe: hypothesis "raw = bytes from the id offset to the first NUL" vs encode(ja), per file and fmt (read-only).
Also: which codec (textdb / textfmt_common) reproduces ja from the raw bytes."""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textdb          # noqa: E402
import textfmt_common as C   # noqa: E402

EX = os.path.join(ROOT, 'extracted')
cache = {}


def data_of(src):
    if src not in cache:
        cache.clear()
        cache[src] = open(os.path.join(EX, *src.split('/')), 'rb').read()
    return cache[src]


stat = collections.Counter()
examples = collections.defaultdict(list)
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    base = os.path.basename(p)
    if base.startswith('BCAST'):
        continue
    for line in open(p, encoding='utf-8'):
        if not line.strip():
            continue
        r = json.loads(line)
        src, off = r['id'].rsplit('#', 1)
        off = int(off, 16)
        fmt = r.get('fmt', '')
        key = (base.split('__')[0] if base.startswith('ROOT') or base.startswith('DPETC') or base.startswith('ETC') else 'FLOW/ATFIRST', fmt)
        d = data_of(src)
        if src == 'DPETC/MESSAGE.INI':
            e = d.find(b'\n', off)
            e = len(d) if e < 0 else e
            if d[e - 1:e] == b'\r':
                e -= 1
            raw = d[off:e - 1]
            assert d[e - 1:e] == b'"'
        elif src.endswith('BPINFO.BIN'):
            raw = d[off:off + 14]
            z = raw.find(b'\0')
            raw = raw if z < 0 else raw[:z]
        else:
            e = d.find(b'\0', off)
            raw = d[off:e if e >= 0 else len(d)]
        try:
            enc_ja = textdb.encode_text(r['ja'])
        except Exception as ex:
            stat[key + ('encfail',)] += 1
            examples[key + ('encfail',)].append(r['id'])
            continue
        if enc_ja != raw:
            stat[key + ('RAWDIFF',)] += 1
            if len(examples[key + ('RAWDIFF',)]) < 5:
                examples[key + ('RAWDIFF',)].append((r['id'], enc_ja[:40], raw[:40], r.get('max_bytes')))
            continue
        a = textdb.decode_text(raw) == r['ja']
        b = C.decode_text(raw) == r['ja']
        stat[key + ('ok', 'tdb' if a else '', 'com' if b else '')] += 1
        if not a and not b:
            examples[key + ('nocodec',)].append(r['id'])
for k, v in sorted(stat.items()):
    print(v, k)
for k, v in examples.items():
    print(k, v[:5])
