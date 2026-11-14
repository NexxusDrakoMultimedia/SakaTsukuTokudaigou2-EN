"""mn6_db_case.py [--apply]: the money words of the English texts in lower case: `9 Oku` -> `9 oku`, `9 Man` -> `9 man` (a digit, one space, the word).
Names and football words stay (`Target Man`, `Man of the Match`, the surname Oku, `Wild Man` ...: no digit in front).  Idempotent, writes only the records that
change, each file read-modify-written once (mn6_db.apply: expected old text is checked at write time)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mn6_db  # noqa: E402

PAT = re.compile(r'(?<=[0-9]) (Oku|Man)(?![A-Za-z])')


def lower(m):
    return ' ' + m.group(1).lower()


def main(argv):
    ch = {}
    for rid, r in mn6_db.records(lambda r: bool(PAT.search(r.get('en') or ''))):
        new = PAT.sub(lower, r['en'])
        if new != r['en']:
            ch[rid] = (r['en'], new)
    print('%d records' % len(ch))
    changed, skipped, missing = mn6_db.apply(ch, dry='--apply' not in argv)
    print('changed %d, skipped %s, missing %s' % (len(changed), skipped, missing))
    for rid in sorted(changed)[:400]:
        print('  ', rid, '|', ch[rid][1].replace('\n', '\\n')[:90])


if __name__ == '__main__':
    main(sys.argv)
