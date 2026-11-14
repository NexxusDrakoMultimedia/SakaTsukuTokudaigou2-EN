"""skh: records that WRITE into an overlay without being text: orphans ('orphan (no pointer)') with a non-empty en that are not skip.

usage: skh_orphans.py [FILE-substring] [--code]
For each such record: file, offset, ja, en, max_bytes, and the SH-4 decoding of the ORIGINAL bytes around the offset (capstone) so that
machine code is easy to tell from data.  --code prints only records whose original bytes (offset-8 .. offset+12) decode, as 2-byte
words, to at least 7 of 10 'plausible' SH-4 instructions with no .word left-over (heuristic).  Read-only.
"""
import glob
import json
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
import capstone as cs            # noqa: E402

md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)


def dis(d, a, b):
    out = []
    a &= ~1
    ok = 0
    for o in range(a, b, 2):
        i = list(md.disasm(d[o:o + 2], 0))
        if i:
            out.append('%x: %s %s' % (o, i[0].mnemonic, i[0].op_str))
            ok += 1
        else:
            out.append('%x: .word %04x' % (o, struct.unpack_from('<H', d, o)[0]))
    return out, ok


def main(argv):
    pat = ''
    for a in argv[1:]:
        if not a.startswith('--'):
            pat = a
    only_code = '--code' in argv
    cnt = Counter()
    n = 0
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        if pat not in p:
            continue
        rel = os.path.basename(p)[:-6].replace('__', '/')
        fp = os.path.join(ROOT, 'extracted', rel)
        if not os.path.exists(fp):
            continue
        d = open(fp, 'rb').read()
        for ln in open(p, encoding='utf-8'):
            r = json.loads(ln)
            if not r.get('orphan') or r.get('skip') or not (r.get('en') or '').strip():
                continue
            off = int(r['id'].split('#')[1], 16)
            lines, ok = dis(d, max(0, off - 8), off + 12)
            if only_code and ok < 10:
                continue
            n += 1
            cnt[rel] += 1
            print('%s #%x ja=%r en=%r max=%s  decodable %d/10' % (rel, off, r['ja'][:10], r['en'][:12], r.get('max_bytes'), ok))
            if pat:
                for l in lines:
                    print('      ' + l)
    print('records', n)
    print(cnt.most_common(12))


if __name__ == '__main__':
    main(sys.argv)
