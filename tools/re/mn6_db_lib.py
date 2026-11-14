"""mn6_db_lib.py [--apply]: the English formats of the shared number library (9 overlays, docs/number-formats.md s5) for the oku / man wrapper.

    ja `%s億%s万円` -> `%s %s man`   `@R/%s億%s万円@` -> `@R/%s %s man@`   `%s万円` -> `%s man`   `@R/%s万円@` -> `@R/%s man@`   `%s円` -> `%s Yen`
    GETREP `0円` (the no-argument zero of the library) -> cleared (+ skip): its literal-pool word is repointed to a `0 Yen` string of the wrapper cave (4 bytes are too few)
Only records of the LIB overlays whose current `en` is one of the earlier translations are touched.  Idempotent."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mn6_db                # noqa: E402
import moneypatch as MP      # noqa: E402

NEW = {'%s億%s万円': '%s %s man', '@R/%s億%s万円@': '@R/%s %s man@', '%s万円': '%s man', '@R/%s万円@': '@R/%s man@', '%s円': '%s Yen'}
OLD_OK = {'Y%s%s0000', '@R/Y%s%s0000@', '%s Man', '@R/%s Man@', 'Y%s', '%s %s man', '@R/%s %s man@', '%s man', '@R/%s man@', '%s Yen',
          '%s Oku %s Man', '@R/%s Oku %s Man@'}


def main(argv):
    libs = set(MP.LIB_SITES)
    ch = {}
    for rid, r in mn6_db.records(lambda r: r['id'].split('#')[0] in libs):
        ja = r['ja']
        if ja in NEW and r.get('en') in OLD_OK:
            ch[rid] = (None, NEW[ja])
        elif ja == '0円' and rid.startswith('FLOW_PRG/GETREP.BIN#') and r.get('en') in ('Y0', '0 Yen', ''):
            ch[rid] = (None, '', {'skip': True})
    print('%d records' % len(ch))
    changed, skipped, missing = mn6_db.apply(ch, dry='--apply' not in argv)
    print('changed %d, skipped %s, missing %s' % (len(changed), skipped, missing))
    for rid in sorted(changed)[:80]:
        print('  ', rid, '->', ch[rid][1])


if __name__ == '__main__':
    main(sys.argv)
