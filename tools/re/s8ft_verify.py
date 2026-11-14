"""s8ft: for every array-head hwptr record (build_patch.hw_array_heads rules) compare the pointer word named in ctx `ptr@HEX`
(the first pointer) and the string bytes in DISC vs the original.   usage: s8ft_verify.py DISC [DISC ...]
Prints per disc: heads checked, pointer word moved (bad), string bytes at the original offset.   Read-only.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_patch as B  # noqa: E402
import discbuild as D  # noqa: E402

BASES = (0x8c2d0000, 0x8c4d0000, 0x8c8d0000)

for disc in sys.argv[1:]:
    d = os.path.join(ROOT, 'build', 'trial')
    if os.path.isdir(os.path.join(d, disc)):
        d = os.path.join(d, disc)
    src = D.Source(d, disc)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    chk = bad = nostr = 0
    for fn in sorted(os.listdir(os.path.join(ROOT, 'translation'))):
        if not fn.endswith('.jsonl') or fn.startswith('BCAST'):
            continue
        path = fn[:-6].replace('__', '/')
        db = [json.loads(l) for l in open(os.path.join(ROOT, 'translation', fn), encoding='utf-8') if l.strip()]
        ex = [r for r in db if r.get('fmt') in ('hwptr', 'recarr', 'gap')]
        heads = B.hw_array_heads(ex)
        if not heads:
            continue
        orig = open(os.path.join(ROOT, 'extracted', path), 'rb').read()
        fr = files['/' + path.upper()]
        new = src.read(fr.lba, fr.size)
        for r in ex:
            off = int(r['id'].rsplit('#', 1)[1], 16)
            if r.get('fmt') != 'hwptr' or off not in heads:
                continue
            ctx = r.get('ctx') or ''
            if 'ptr@' not in ctx:
                continue
            p = int(ctx.split('ptr@')[1].split()[0], 16)
            if p + 4 > len(orig):
                continue
            wo = struct.unpack_from('<I', orig, p)[0]
            wn = struct.unpack_from('<I', new, p)[0]
            chk += 1
            if wo != wn:
                # a false reference (cp932 bytes read as a pointer: the word is not base+off in the original either)
                if wo - off in BASES:
                    bad += 1
                    print('  MOVED %s#%x ptr@%x %#x -> %#x' % (path, off, p, wo, wn))
            tail = new[off:off + len(r['en']) + 1]
            if tail != r['en'].encode('cp932') + b'\0':
                nostr += 1
                print('  string differs %s#%x %r vs %r' % (path, off, new[off:off + 16], r['en']))
    print('%-12s heads checked %d, pointer moved %d, string not in place %d' % (disc, chk, bad, nostr))
    src.close()
