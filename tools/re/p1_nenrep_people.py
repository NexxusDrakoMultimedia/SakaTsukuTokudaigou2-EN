"""p1_nenrep_people.py: the annual report's people formats (FLOW_PRG/NENREP.BIN 0x24f34..0x24f8b) as gap records, English text set.

The number function of NENREP (0xe3cc; callers at 0x514, 0x582, 0x5158, 0x51b0, mode 3 / 4) prints a head count V in people:
    hi = V / 10000 (space padded to `mode` characters), lo = V % 10000 (4 digits, zero padded);
    V >= 0, hi > 0   real('%s万%s人', hi, lo)           V < 0, hi > 0   real('@R/%s万%s人@', hi, lo)     (red, no sign)
    V >= 0, hi == 0  real('%s人', lo)                   V < 0, hi == 0  real('@R/%s人@', lo)             (lo space padded to 4)
and, behind each, a call of the debug printf 0x8c0111b4 (flag byte 0x8c230bd6 = 0) with the formats that end in `@` but have no `@R/`.
English keeps the Japanese quirk (man = 10,000, like `%soku %sman` of the money formats) and uses `ppl` for 人 so that every format fits its slot
(slots: the string + NUL + the zero bytes behind it up to the next string).

    python -I -X utf8 tools/re/p1_nenrep_people.py [--dry]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import textfmt_gap as G          # noqa: E402
import s8i_text_edit as S        # noqa: E402

SRC = 'FLOW_PRG/NENREP.BIN'
GAP_EN = {
    SRC + '#24f34': '@R/%sman %sppl@',     # slot 16
    SRC + '#24f44': '-%sman %sp@',         # slot 12, debug printf only
    SRC + '#24f50': '%sman %sppl',         # slot 12
    SRC + '#24f5c': '%sman %sp@',          # slot 12, debug printf only
    SRC + '#24f68': '@R/%sppl@',           # slot 12
    SRC + '#24f74': '-%sppl@',             # slot 8, debug printf only
    SRC + '#24f7c': '%sppl',               # slot 8
    SRC + '#24f84': '%sppl@',              # slot 8, debug printf only
}


def main():
    dry = '--dry' in sys.argv
    with open(os.path.join(ROOT, 'extracted', *SRC.split('/')), 'rb') as f:
        data = f.read()
    recs = [r for r in G.extract(data, SRC) if r['id'] in GAP_EN]
    if len(recs) != len(GAP_EN):
        raise SystemExit('textfmt_gap.GAPS does not hold the eight NENREP people entries (%d found)' % len(recs))
    for r in recs:
        r['en'] = GAP_EN[r['id']]
        if len(r['en'].encode('cp932')) > r['max_bytes'] - 1:
            raise SystemExit('%s: %r does not fit %d bytes' % (r['id'], r['en'], r['max_bytes'] - 1))
    path = os.path.join(ROOT, 'translation', SRC.replace('/', '__') + '.jsonl')
    n = S.edit_file(path, {}, recs, dry)
    print('%s: %d gap record(s) inserted%s' % (SRC, len(recs), ' (dry)' if dry else ''))


if __name__ == '__main__':
    main()
