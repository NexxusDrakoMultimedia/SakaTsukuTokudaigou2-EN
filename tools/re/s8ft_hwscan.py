"""s8ft: find hwptr records that the build RELOCATED although they are the head of a fixed-stride record array.

usage: s8ft_hwscan.py DISC [FILE ...]
For every translation/<file>.jsonl overlay with hwptr records (refs > 0, English present) compare the aligned words == base+off in the
ORIGINAL (extracted/) and in the built DISC.  A record is RELOCATED when the original pointers are gone in the disc.  It is an ARRAY HEAD
suspect when other records of the same file sit at off + k*S (k = 1..2, S 8..128) and are stride-table / recarr records without pointers
(the record is the first field of a struct array, e.g. SCDRF 0x37df0 stride 56).  Read-only.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D  # noqa: E402

BASES = (0x8c2d0000, 0x8c4d0000, 0x8c8d0000, 0x8c010000)


def words(b):
    n = len(b) // 4
    return struct.unpack_from('<%dI' % n, b, 0)


def main(argv):
    disc = argv[1]
    only = [a.upper() for a in argv[2:]]
    d = os.path.join(ROOT, 'build', 'trial')
    if os.path.isdir(os.path.join(d, disc)):
        d = os.path.join(d, disc)
    src = D.Source(d, disc)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    tot_rel = 0
    for fn in sorted(os.listdir(os.path.join(ROOT, 'translation'))):
        if not fn.endswith('.jsonl') or fn.startswith('BCAST'):
            continue
        path = fn[:-6].replace('__', '/')
        if only and not any(o in path.upper() for o in only):
            continue
        key = '/' + path.upper()
        if key not in files or not os.path.isfile(os.path.join(ROOT, 'extracted', path)):
            continue
        db = [json.loads(l) for l in open(os.path.join(ROOT, 'translation', fn), encoding='utf-8') if l.strip()]
        hw = [r for r in db if r.get('fmt') == 'hwptr' and r.get('refs') and r.get('en')]
        if not hw:
            continue
        orig = open(os.path.join(ROOT, 'extracted', path), 'rb').read()
        fr = files[key]
        new = src.read(fr.lba, fr.size)
        if len(new) != len(orig):
            continue
        wo = words(orig)
        wn = words(new)
        co = {}
        cn = {}
        for w in wo:
            co[w] = co.get(w, 0) + 1
        for w in wn:
            cn[w] = cn.get(w, 0) + 1
        best = max(BASES, key=lambda b: sum(co.get(b + int(r['id'].split('#')[1], 16), 0) for r in hw))
        offs = {int(r['id'].split('#')[1], 16): r for r in db}
        rel = []
        for r in hw:
            off = int(r['id'].split('#')[1], 16)
            a = co.get(best + off, 0)
            b = cn.get(best + off, 0)
            if a and b < a:
                rel.append((off, r))
        heads = []
        for off, r in rel:
            for S in range(8, 129):
                hit = 0
                for k in (1, 2):
                    o2 = offs.get(off + k * S)
                    if o2 and ('stride-table' in (o2.get('ctx') or '') and not o2.get('refs')):
                        hit += 1
                if hit == 2:
                    heads.append((off, S, r))
                    break
        tot_rel += len(rel)
        print('%-28s base %#x hwptr %d relocated %d  array-head suspects %d' % (path, best, len(hw), len(rel), len(heads)))
        for off, S, r in heads[:20]:
            print('    HEAD %#x stride %d refs %s ja=%r en=%r ctx=%s' % (off, S, r.get('refs'), r['ja'], r['en'], r.get('ctx')))
    print('total relocated', tot_rel)


main(sys.argv)
