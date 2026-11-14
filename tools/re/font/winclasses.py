"""Write the two static-evidence tables that tools/winwidth.py reads.

    python -I -X utf8 tools/re/font/winclasses.py            (after wresolve_all.py has written build/trans/width_refs.json)

  tools/winwidth_overlays.tsv   one row per overlay: which text-window factories (constructors that store a window geometry:
                                cells +0x3c, rows +0x3d, advance +0x3e, line height +0x3f) the overlay code contains.
                                bubble = a 17-cell / 2-row factory exists (the face "speech bubble" window, 33 half-width cells);
                                msg = a 20-cell / 3-row factory exists (39 cells); others = every other immediate cell count.
  tools/winwidth_tables.tsv     pointer tables / pointer slots whose loading function reaches factories of ONE window class only
                                (verdict msg or bubble), with the evidence addresses.

Both are derived from the overlay code images (extracted/ is only read).  Static call-graph evidence, see docs/window-widths.md s3 for its limits."""
import os, sys, json, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
from winmap import Overlay
from wresolve import cls_name

OUT_OV = os.path.join(ROOT, 'tools', 'winwidth_overlays.tsv')
OUT_TB = os.path.join(ROOT, 'tools', 'winwidth_tables.tsv')


def kind_of(cls):
    cells, rows = cls.split('/')[:2]
    if cells == '17' and rows == '2':
        return 'bubble'
    if cells == '20' and rows == '3':
        return 'msg'
    return 'other'


def main():
    surv = {}
    for r in csv.DictReader(open(os.path.join(HERE, 'layoutsurvey.tsv')), delimiter='\t'):
        surv[r['overlay']] = r
    rows = []
    tsv = csv.DictReader(open(os.path.join(ROOT, 'build', 'memmap', 'overlays.tsv')), delimiter='\t')
    for r in tsv:
        n = r['overlay']
        if r['dir'] not in ('FLOW_PRG', 'ATFIRST'):
            continue
        try:
            ov = Overlay(n)
        except (SystemExit, Exception):
            continue
        facs = []
        for key, lst in ov.factories.items():
            for site, cells, nrows, adv, lineh in lst:
                if cells is not None:
                    facs.append((cells, nrows, adv, lineh, site))
        bubble = sorted({(c, rw, a, l) for c, rw, a, l, s in facs if c == 17 and rw == 2})
        msg = sorted({(c, rw, a, l) for c, rw, a, l, s in facs if c == 20 and rw == 3}, key=str)
        other = sorted({c for c, rw, a, l, s in facs} - {17, 20})
        s = surv.get(n)
        lib = 'yes' if s and s['head'] != '-' else 'no'
        font = 'yes' if s and (s['s3b4'] != '0' or s['s3ac'] != '0' or s['s3d0'] != '0') else 'no'
        rows.append([r['dir'] + '/' + n, lib, font, 'yes' if bubble else 'no', 'yes' if msg else 'no',
                     ' '.join(str(c) for c in other),
                     ' '.join('%x' % s2 for c, rw, a, l, s2 in sorted(facs, key=lambda x: x[4]) if c == 17 and rw == 2)])
    with open(OUT_OV, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('source\twindow_lib\tfont_slots\tbubble_17x2\tmsg_20x3\tother_cells\tbubble_ctor_sites\n')
        for r in sorted(rows):
            fh.write('\t'.join(r) + '\n')
    refs = json.load(open(os.path.join(ROOT, 'build', 'trans', 'width_refs.json')))
    out = []
    for src, o in sorted(refs.items()):
        for key, e in sorted(o['tabs'].items()):
            kinds = collections.Counter()
            evid = []
            for rf in e['refs']:
                ks = {kind_of(c) for c in rf['closure']}
                for k in ks:
                    kinds[k] += 1
                if rf['closure']:
                    evid.append('%s>%s' % (rf['site'], ','.join(rf['closure'])))
            if not kinds:
                continue
            ks = set(kinds)
            if ks == {'msg'}:
                verdict = 'msg'
            elif ks == {'bubble'}:
                verdict = 'bubble'
            else:
                verdict = 'mixed'
            out.append([src, key, str(e['n']), str(e['recs']), verdict, ';'.join(evid[:4])])
    with open(OUT_TB, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('source\tkey\tn\trecs\tverdict\tevidence_site>classes\n')
        for r in out:
            fh.write('\t'.join(r) + '\n')
    print('overlays', len(rows), 'tables with evidence', len(out), collections.Counter(r[4] for r in out))


if __name__ == '__main__':
    main()
