"""mn6_libscan.py: find, in every overlay, the call sites of the shared money number library (`%s億%s万円` family) and the literal-pool word
of the callee (the stack-argument printf `sprintf_alloc`, 0x8c2e1130 in GETREP) that those calls use.  Read only.

    python -I -X utf8 tools/re/mn6_libscan.py [--all]

A call site = a code word `mov.l @(d,pc),rF` that loads the address of one of the library format strings, followed (within 8 words) by
`jsr @rX` whose delay slot is `mov.l rF,@-r15`; rX is traced back to its own `mov.l @(d,pc),rX` and that pool word is reported."""
import glob
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

MONEY_JA = {'%s億%s万円', '@R/%s億%s万円@', '%s万円', '@R/%s万円@', '%s円'}


def hw(d, o):
    return d[o] | d[o + 1] << 8


def pool_target(d, o):
    w = hw(d, o)
    return ((o + 4) & ~3) + (w & 0xFF) * 4


def scan(rel, recs, base=None):
    if base is None:
        import textdb
        base = textdb.load_image(rel).base
    p = os.path.join(ROOT, 'extracted', *rel.split('/'))
    d = open(p, 'rb').read()
    out = []
    fmt = {}
    for rid, ja in recs:
        off = int(rid.split('#')[1], 16)
        fmt[base + off] = ja
    for o in range(0, len(d) - 2, 2):
        w = hw(d, o)
        if (w >> 12) != 0xD:
            continue
        t = pool_target(d, o)
        if t + 4 > len(d):
            continue
        va = struct.unpack_from('<I', d, t)[0]
        if va not in fmt:
            continue
        rf = (w >> 8) & 15
        # find jsr @rX within 10 words with delay slot mov.l rF,@-r15  (0x2F f6 : mov.l rF,@-r15 = 0x2FF6 | rF<<4)
        for k in range(o + 2, o + 24, 2):
            wk = hw(d, k)
            if (wk & 0xF0FF) == 0x400B and hw(d, k + 2) == (0x2F06 | (rf << 4)):
                rx = (wk >> 8) & 15
                # trace rX back to a pool load
                src = None
                for j in range(k - 2, max(0, k - 700), -2):
                    wj = hw(d, j)
                    if (wj >> 12) == 0xD and ((wj >> 8) & 15) == rx:
                        src = j
                        break
                if src is None:
                    out.append((rel, fmt[va], o, k, None, None))
                else:
                    pt = pool_target(d, src)
                    out.append((rel, fmt[va], o, k, pt, struct.unpack_from('<I', d, pt)[0]))
                break
        else:
            out.append((rel, fmt[va], o, None, None, None))
    return out


def main(argv):
    by = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get('ja') in MONEY_JA or (r.get('ja', '').endswith('億%s万円@') and '%s' in r['ja']):
                by.setdefault(r['id'].split('#')[0], []).append((r['id'], r['ja']))
    for rel in sorted(by):
        for row in scan(rel, by[rel]):
            print('%-24s %-18s ld@%05x jsr@%s  pool@%s -> %s' % (row[0].split('/')[-1], row[1], row[2], '%05x' % row[3] if row[3] else '-',
                                                              '%05x' % row[4] if row[4] else '-', '%08x' % row[5] if row[5] else '-'))


if __name__ == '__main__':
    main(sys.argv)
