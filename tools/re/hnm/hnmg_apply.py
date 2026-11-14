"""Remove '-gun' from the municipality POINTER-TABLE records (composition form), atomic rewrite.

    python -I -X utf8 tools/re/hnm/hnmg_apply.py [--dry]

Club names are composed at run time from the pointer-table string (town_short, no truncation after the layout patch), so the
district name must be the gun-less form ('Miura-gun' -> 'Miura': club 'Miura Mythos', not 'Miura-gun Mythos').  The Hometown list and
header use the separate 126-byte records (FLOW_PRG__HOMETOWN.BIN.jsonl, max_bytes 35) and keep the full 'Miura-gun'.  This is the one
documented exception to "one ja has one en".  Only records whose ctx is `tbl@<hex>[i/N]` (any suffix) and whose en ends with '-gun'
change; max_bytes and every other field/line stay byte for byte.  The NENREP / HOMETOWN / AUTOSAVE 'orphan' stride-table records are
not pointer-table records and are not touched.
"""
import glob
import json
import os
import re
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DRY = '--dry' in sys.argv
TBL = re.compile(r'^tbl@[0-9a-f]+\[\d+/(1270|1268)\]')    # the municipality tables (CSAVE3 has 1268 entries)


def is_target(rec):
    return bool(TBL.match(rec.get('ctx') or '')) and rec['en'].endswith('-gun') and rec['ja'][-1:] in '郡群'


def main():
    total = 0
    for path in sorted(glob.glob(os.path.join(ROOT, 'translation', 'FLOW_PRG__*.jsonl'))):
        lines = open(path, 'rb').read().decode('utf-8').split('\n')
        out = []
        n = 0
        for ln in lines:
            if ln.strip():
                rec = json.loads(ln)
                if is_target(rec):
                    rec['en'] = rec['en'][:-4]
                    ln = json.dumps(rec, ensure_ascii=False, separators=(',', ':'))
                    n += 1
            out.append(ln)
        if n:
            total += n
            print('%-46s %d records' % (os.path.basename(path), n))
            if not DRY:
                tmp = path + '.gun.tmp'
                open(tmp, 'wb').write('\n'.join(out).encode('utf-8'))
                for _ in range(20):
                    try:
                        os.replace(tmp, path)
                        break
                    except PermissionError:
                        time.sleep(0.5)
                else:
                    raise SystemExit('cannot replace ' + path)
    print('total', total, '(dry run)' if DRY else '')


if __name__ == '__main__':
    main()
