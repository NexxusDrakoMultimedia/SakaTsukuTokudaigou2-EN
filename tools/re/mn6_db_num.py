"""mn6_db_num.py [--apply]: English formats of the numeric money formats (libn, tools/moneypatch.py LIBN_SITES) and the dead GAME pieces.

    ABROAD FIRE PLNUMSET SELNAT   `%2d億%02d00万円` -> `%2d oku %02d00m`    `%6d00万円` -> `%6d00 man`
    INVEST                        `%d兆%04d億%02d00万円` -> `%d cho%04d oku%02d00m`   `    %4d億%02d00万円` -> `    %4d oku %02d00m`   `          %4d万円` -> `          %4d man`
    G_INCOME                      `%d円` -> `%d Yen`
    GAME                          `0万円` `%d億` `%d万` `%s円`: dead since GAME's money text function jumps to the money cave -> cleared (en "", skip) like the unit pieces
Idempotent; only records whose current `en` is a known earlier translation are touched."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mn6_db                # noqa: E402

NEW_BY_JA = {'%2d億%02d00万円': '%2d oku %02d00m', '%6d00万円': '%6d00 man'}
SETS = ('ABROAD', 'FIRE', 'PLNUMSET', 'SELNAT')
BY_ID = {'FLOW_PRG/INVEST.BIN#110ac': '%d cho%04d oku%02d00m', 'FLOW_PRG/INVEST.BIN#110c4': '    %4d oku %02d00m', 'FLOW_PRG/INVEST.BIN#110d8': '          %4d man',
         'FLOW_PRG/G_INCOME.BIN#266dc': '%d Yen'}
CLEAR = ('FLOW_PRG/GAME.BIN#1a9b88', 'FLOW_PRG/GAME.BIN#1a9b90', 'FLOW_PRG/GAME.BIN#1a9b98', 'FLOW_PRG/GAME.BIN#1a9ba0')
OLD_OK = {'Y%2d%02dM', '%6d00 Man', '%2d oku %02d00m', '%6d00 man', 'Y%d.%04d%02dT', 'Y          %4d%02dM', 'Y           %4d0k', '%d cho%04d oku%02d00m',
          '    %4d oku %02d00m', '          %4d man', 'Y%d', '%d Yen', 'Y0', '%d00M', '%d0K', 'Y%s', ''}


def main(argv):
    ch = {}
    for rid, r in mn6_db.records(lambda r: r['id'].split('#')[0].split('/')[-1].replace('.BIN', '') in SETS + ('INVEST', 'G_INCOME', 'GAME')):
        if r['id'] in BY_ID and r.get('en') in OLD_OK:
            ch[rid] = (None, BY_ID[rid])
        elif r['id'] in CLEAR and r.get('en') in OLD_OK:
            ch[rid] = (None, '', {'skip': True})
        elif r['ja'] in NEW_BY_JA and r['id'].split('#')[0].split('/')[-1].replace('.BIN', '') in SETS and r.get('en') in OLD_OK:
            ch[rid] = (None, NEW_BY_JA[r['ja']])
    print('%d records' % len(ch))
    changed, skipped, missing = mn6_db.apply(ch, dry='--apply' not in argv)
    print('changed %d, skipped %s, missing %s' % (len(changed), skipped, missing))
    for rid in sorted(changed):
        print('  ', rid, '->', repr(ch[rid][1]))


if __name__ == '__main__':
    main(sys.argv)
