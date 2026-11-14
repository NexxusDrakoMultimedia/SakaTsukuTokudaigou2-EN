"""rfit_flag: flag hwptr English forms that look cut to fit a slot (names owner helper, read-only).

    python -I -X utf8 tools/re/rfit_flag.py IN.tsv(from rfit_scan.py --fmt hwptr) OUT.txt

Heuristics: ends with '.', 4+ consonants in a row, no vowel, or the form fills the slot while a naive romanisation of the
half-width kana is clearly longer.
"""
import csv
import re
import sys

KANA = {
    'ｱ': 'a', 'ｲ': 'i', 'ｳ': 'u', 'ｴ': 'e', 'ｵ': 'o', 'ｶ': 'ka', 'ｷ': 'ki', 'ｸ': 'ku', 'ｹ': 'ke', 'ｺ': 'ko',
    'ｻ': 'sa', 'ｼ': 'shi', 'ｽ': 'su', 'ｾ': 'se', 'ｿ': 'so', 'ﾀ': 'ta', 'ﾁ': 'chi', 'ﾂ': 'tsu', 'ﾃ': 'te', 'ﾄ': 'to',
    'ﾅ': 'na', 'ﾆ': 'ni', 'ﾇ': 'nu', 'ﾈ': 'ne', 'ﾉ': 'no', 'ﾊ': 'ha', 'ﾋ': 'hi', 'ﾌ': 'fu', 'ﾍ': 'he', 'ﾎ': 'ho',
    'ﾏ': 'ma', 'ﾐ': 'mi', 'ﾑ': 'mu', 'ﾒ': 'me', 'ﾓ': 'mo', 'ﾔ': 'ya', 'ﾕ': 'yu', 'ﾖ': 'yo',
    'ﾗ': 'ra', 'ﾘ': 'ri', 'ﾙ': 'ru', 'ﾚ': 're', 'ﾛ': 'ro', 'ﾜ': 'wa', 'ｦ': 'o', 'ﾝ': 'n',
    'ｧ': 'a', 'ｨ': 'i', 'ｩ': 'u', 'ｪ': 'e', 'ｫ': 'o', 'ｬ': 'ya', 'ｭ': 'yu', 'ｮ': 'yo', 'ｯ': '', 'ｰ': '',
}


def naive(ja):
    return len(''.join(KANA.get(c, c) for c in ja if c not in 'ﾞﾟ'))


def main(argv):
    inp, out = argv[0], argv[1]
    n = 0
    with open(inp, encoding='utf-8', newline='') as fh, open(out, 'w', encoding='utf-8') as fo:
        rd = csv.reader(fh, delimiter='\t', quoting=csv.QUOTE_NONE)
        next(rd)
        for row in rd:
            if len(row) < 10:
                continue
            fmt, ja, en, ln, cnt, ov, lo, hi, full, hwp = row[:10]
            lo = int(lo)
            why = []
            if en.endswith('.'):
                why.append('dot')
            if re.search(r'[bcdfghjklmnpqrstvwxz]{4,}', en, re.I):
                why.append('cons4')
            if not re.search(r'[aeiouy]', en, re.I) and len(en) > 1:
                why.append('novowel')
            if int(full) and naive(ja) > len(en) + 2 and len(en) + 1 >= lo:
                why.append('cut?%d' % naive(ja))
            if why:
                n += 1
                fo.write('%s\t%s\t%s\tn=%s\tov=%s\tslot=%d-%s\t%s\n' % (ja, en, '', cnt, ov, lo, hi, ','.join(why)))
    print(n, 'flagged ->', out)


if __name__ == '__main__':
    main(sys.argv[1:])
