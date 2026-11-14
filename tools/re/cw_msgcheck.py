"""transcheck (cells and pixels) over the 54 Name&Mascot Select explanation messages + the club-word records.
usage: python -I -X utf8 tools/re/cw_msgcheck.py"""
import json, os, struct, sys, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import transcheck as TC
import pixelwidth as PX

recs = {}
for l in open('translation/FLOW_PRG__CLUBEDIT.BIN.jsonl', encoding='utf8'):
    r = json.loads(l); recs[int(r['id'].split('#')[1], 16)] = r
d = open('extracted/FLOW_PRG/CLUBEDIT.BIN', 'rb').read()
bad = 0
for k in range(1, 55):
    v = struct.unpack_from('<I', d, 0x1eb8c + 4 * k)[0] - 0x8c2d0000
    r = recs[v]
    item = {'ja': r['ja'], 'kind': 'overlay', 'lines': len(r['ja'].split('\n'))}
    for mode in ('cells', 'pixels'):
        errs, warns = TC.check_text(item, r['en'], width_mode=mode)
        for e in errs:
            bad += 1
            print('ERR', k, mode, e.get('code'), str(e.get('message'))[:140])
        for w in warns:
            if mode == 'cells':
                print('warn', k, w.get('code'), str(w.get('message'))[:100])
    m = re.match(r'@Y/(.+?)@', r['en'])
    print(k, m.group(1) if m else None, 'lines', len(r['en'].split('\n')), 'maxline', max(len(re.sub(r'@./', '', x)) for x in r['en'].split('\n')))
print('errors', bad)
