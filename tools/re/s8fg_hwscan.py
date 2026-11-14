"""s8fg: find hwptr records that are really the FIRST ELEMENT of a stride-S record array (array base pointer mistaken for a string pointer),
and check whether prop10c / hsk_full1 relocated them (pointer word changed vs the original file).
Needs build/s8fg/<disc>/<file> copies (s8fg_extract.py); files that are missing are fetched here.
usage: s8fg_hwscan.py [FILE_SUBSTR]
Read-only on the project (writes only build/s8fg).
"""
import glob
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D  # noqa: E402

DISCS = {'orig': (ROOT, None), 'hsk_full1': (os.path.join(ROOT, 'build', 'trial', 'hsk_full1'), 'hsk_full1'),
         'prop10c': (os.path.join(ROOT, 'build', 'trial'), 'prop10c')}


def main(argv):
    sub = argv[1].upper() if len(argv) > 1 else ''
    srcs = {k: D.Source(d, n) for k, (d, n) in DISCS.items()}
    fsys = {}
    for k, s in srcs.items():
        _p, _rl, _rs, recs = D.read_filesystem(s)
        fsys[k] = {r.path.upper(): r for r in recs if not r.isdir}

    def get(k, rel):
        r = fsys[k]['/' + rel.upper()]
        return srcs[k].read(r.lba, r.size)

    tot = 0
    for jp in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        bn = os.path.basename(jp)
        if not bn.startswith('FLOW_PRG__') and not bn.startswith('ATFIRST__'):
            continue
        rel = bn[:-6].replace('__', '/')
        if sub and sub not in rel.upper():
            continue
        recs = [json.loads(l) for l in open(jp, encoding='utf-8') if l.strip()]
        arr = {}   # stride -> set of offsets
        for r in recs:
            if r.get('fmt') == 'recarr':
                m = re.search(r'S=(\d+)', r.get('ctx', ''))
                if m:
                    arr.setdefault(int(m.group(1)), set()).add(int(r['id'].split('#')[1], 16))
        hits = []
        for r in recs:
            if r.get('fmt') != 'hwptr' or not r.get('refs'):
                continue
            off = int(r['id'].split('#')[1], 16)
            for S, offs in arr.items():
                if off + S in offs or off - S in offs:
                    hits.append((r, off, S))
                    break
        if not hits:
            continue
        try:
            o = get('orig', rel)
            p = get('prop10c', rel)
            h = get('hsk_full1', rel)
        except KeyError:
            print('missing', rel)
            continue
        for r, off, S in hits:
            m = re.search(r'ptr@([0-9a-f]+)', r.get('ctx', ''))
            tbl = re.search(r'tbl@([0-9a-f]+)', r.get('ctx', ''))
            w = None
            if m:
                po = int(m.group(1), 16)
                wo = struct.unpack_from('<I', o, po)[0]
                wp = struct.unpack_from('<I', p, po)[0]
                wh = struct.unpack_from('<I', h, po)[0]
                w = 'ptr@%x orig=%08x hsk=%08x p10c=%08x %s' % (po, wo, wh, wp, 'RELOCATED' if wo != wp else 'same')
            print('%-26s %-8x S=%-3d refs=%-3s en=%r ja=%r %s %s' % (rel, off, S, r.get('refs'), r.get('en'), r.get('ja'), w or '', 'tbl' if tbl else ''))
            tot += 1
    print('total', tot)


main(sys.argv)
