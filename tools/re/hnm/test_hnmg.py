"""Tests of the -gun removal (data only, ~1 s):  python -I -X utf8 tools/re/hnm/test_hnmg.py

Rule under test (docs: the documented split of "one ja has one en"): the municipality POINTER-TABLE records (ctx tbl@<hex>[i/N]; read by
the club-name composer / #to# expander) carry the gun-less COMPOSITION form; the 126-byte HOMETOWN name fields (max_bytes 35, list and
header) keep the full 'X-gun'.  The simulator check on a built image is tools/re/hnm/hnmg_verify.py.
"""
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hnmg_apply as A  # noqa: E402

ROOT = A.ROOT
TBL = re.compile(r'^tbl@[0-9a-f]+\[\d+/(1270|1268)\]')    # the municipality tables (CSAVE3 has 1268 entries)
# ja with two en inside the pointer tables: records pinned in place by an interior pointer keep a 7/8-byte cut (hnm_apply_names.py)
PINNED_SPLIT = {'奥尻郡': {'Okushiri', 'Okushi.'}, '八戸市': {'Hachinohe', 'Hachin.'}}
fails = []


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        fails.append(msg)


def records():
    for f in sorted(glob.glob(os.path.join(ROOT, 'translation', 'FLOW_PRG__*.jsonl'))):
        for line in open(f, encoding='utf-8'):
            if line.strip():
                yield os.path.basename(f), json.loads(line)


def main():
    tbl = [(f, r) for f, r in records() if TBL.match(r.get('ctx') or '')]
    check(len(tbl) > 39000, 'pointer-table records found: %d in %d files' % (len(tbl), len({f for f, _ in tbl})))
    check(not [1 for _, r in tbl if '-gun' in r['en']], 'no pointer-table record contains -gun')
    check(sum(1 for _, r in tbl if r['ja'][-1:] in '郡群') > 15000, 'district records are still present (not deleted)')
    check(not [1 for _, r in tbl if A.is_target(r)], 'hnmg_apply finds nothing left to change (idempotent)')
    check(A.is_target({'ctx': 'tbl@43858[7/1270]', 'en': 'Miura-gun', 'ja': '三浦郡'}), 'is_target: table record with -gun')
    check(not A.is_target({'ctx': 'recarray S=126 n=1270 W=35', 'en': 'Miura-gun', 'ja': '三浦郡'}), 'is_target: 126-byte name field is never a target')
    check(not A.is_target({'ctx': 'orphan (no pointer) stride-table(in-place only)', 'en': 'Aba-gun', 'ja': '網走郡'}), 'is_target: orphan stride record is not a target')
    # one ja -> one en inside the pointer tables, except the documented pinned records
    en = collections.defaultdict(set)
    for _, r in tbl:
        en[r['ja']].add(r['en'])
    multi = {j: e for j, e in en.items() if len(e) > 1}
    check(all(j in PINNED_SPLIT and e == PINNED_SPLIT[j] for j, e in multi.items()), 'one ja has one en in the pointer tables (exceptions: %s)' % ', '.join(sorted(multi)))
    # the Hometown list / header name fields keep the full name
    ht = [r for f, r in records() if f == 'FLOW_PRG__HOMETOWN.BIN.jsonl' and r.get('max_bytes') == 35 and r['ja'][-1:] in '郡群']
    guns = [r for r in ht if r['en'].endswith('-gun')]
    check(len(guns) >= 100, 'HOMETOWN 126-byte name fields keep the full -gun form (%d of %d districts)' % (len(guns), len(ht)))
    # the documented split: a name field is the table form or table form + -gun, never anything else (when the table has that ja)
    tab = {j: next(iter(e - {x for x in e if x.endswith('.')} or e)) for j, e in en.items()}
    odd = [(r['ja'], r['en'], tab[r['ja']]) for r in ht if r['ja'] in tab and r['en'] not in (tab[r['ja']], tab[r['ja']] + '-gun')]
    check(not odd, 'name field = table form or table form + -gun for every district (%d differing: %s)' % (len(odd), odd[:3]))
    check(all(len(r['en'].encode('cp932')) < 35 for r in ht), 'name fields fit max_bytes 35')
    print('FAILED %d' % len(fails) if fails else 'ALL OK')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
