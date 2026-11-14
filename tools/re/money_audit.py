"""List every translation record whose text uses money / number tokens, for auditing (docs/number-formats.md).

    python -I -X utf8 tools/re/money_audit.py [--out build/trans/money_records.tsv]

Writes a TSV (one record per line, tabs and newlines inside the texts escaped as \\t and \\n) and prints a summary.
Columns: id, family, formatter, ja_tokens, en_tokens, tokens_equal, flags, ja, en
  family     PIECE       the four unit strings of the money function (億 万円 円 0円) - dead with --money-format on, kept Japanese
             M           text with %m    (money function: Y150M / Y1.315bn, tools/moneypatch.py)
             D           text with %D    (full-width digits in the original, ASCII with --money-format on)
             SPRINTF_YEN printf format + a yen unit (億 万 円 兆): arguments are computed by game code, see docs/number-formats.md s5
             LIT_YEN     literal amount in the Japanese text (3億円, 1000万円)
             S_MONEY     %s argument that is (probably) a money string built by the money function
             NUM         other numeric printf formats (%d %2d %04d %f %x ...)
  formatter  expander (the tsString window: %s %d %D %m only; widths like %2d print literally!), sprintf (libc: widths work),
             either (plain %d / %s: both possible)
  flags      UNIT_WORD (oku / man / yen left in English), PIECE_ARTIFACT (00M, 0,000 Y ...), NO_EN, TOKEN_MISMATCH,
             FULLWIDTH_WITHOUT_PATCH (%D), WIDTH_ON_EXPANDER (a width format in a string that may go through the expander)
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

PRINTF = re.compile(r'%%|%[-0-9.]*[sdDmfxXc]')
MONEY_WORD = re.compile(r'(資金|契約金|移籍金|違約金|賞金|年俸|年棒|収入|支出|費用|維持費|運営費|金額|予算|[^\w]金[^\w]|報酬|出資|投資|赤字|黒字)')
UNIT_JA = re.compile(r'[兆億万円]')


def load():
    for f in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(f, encoding='utf8') as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def main(argv):
    out = os.path.join(ROOT, 'build', 'trans', 'money_records.tsv')
    if '--out' in argv:
        out = argv[argv.index('--out') + 1]
        if not os.path.isabs(out):
            out = os.path.join(os.getcwd(), out)
    try:
        import moneypatch as MPT
        pieces = MPT.piece_ids()
    except Exception as e:                      # pragma: no cover
        print('warning: piece ids unavailable (%s)' % e)
        pieces = {}
    rows = []
    for r in load():
        ja, en, rid = r['ja'], r.get('en') or '', r['id']
        tj = [t for t in PRINTF.findall(ja) if t != '%%']
        te = [t for t in PRINTF.findall(en) if t != '%%']
        has_unit = bool(UNIT_JA.search(ja)) and (bool(tj) or re.search(r'[0-9０-９][^\n]{0,3}[兆億万円]|[兆億万]円|^[億万円]|^0円', ja))
        fam = None
        if rid in pieces:
            fam = 'PIECE'
        elif '%m' in ja:
            fam = 'M'
        elif '%D' in ja:
            fam = 'D'
        elif tj and has_unit and re.search(r'[兆億万円]', ja):
            fam = 'SPRINTF_YEN'
        elif not tj and has_unit and re.search(r'[0-9０-９]+(?:[,.][0-9]+)?[兆億万]?円|[0-9０-９]+[兆億万]', ja):
            fam = 'LIT_YEN'
        elif '%s' in tj and MONEY_WORD.search(ja) and not re.search(r'選手|人$', ja):
            fam = 'S_MONEY'
        elif any(re.match(r'%[-0-9.]*[dDfxX]', t) for t in tj):
            fam = 'NUM'
        if fam is None:
            continue
        if fam == 'NUM' and rid.startswith(('DPETC', '2_DP')):
            continue
        widthy = any(re.match(r'%[-0-9.]+[dsfxX]', t) for t in tj)
        formatter = 'sprintf' if widthy else ('expander' if ('%m' in ja or '%D' in ja) else 'either')
        flags = []
        if not en:
            flags.append('NO_EN')
        if re.search(r'\b(oku|man|yen)\b', en) or re.search(r'\bYen\b', en):
            flags.append('UNIT_WORD')
        if re.search(r'00M|0,000|0K\b', en) and fam not in ('SPRINTF_YEN', 'LIT_YEN'):
            flags.append('PIECE_ARTIFACT')
        if en and tj != te:
            flags.append('TOKEN_MISMATCH')
        if '%D' in ja:
            flags.append('FULLWIDTH_WITHOUT_PATCH')
        if widthy and formatter == 'sprintf' and re.search(r'[\n]', ja) and r.get('ctx', '').startswith('ptr@'):
            pass
        rows.append((rid, fam, formatter, ' '.join(tj), ' '.join(te), 'Y' if tj == te else 'N', ','.join(flags), ja, en))
    os.makedirs(os.path.dirname(out), exist_ok=True)

    def esc(s):
        return s.replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')
    with open(out, 'w', encoding='utf8', newline='\n') as f:
        f.write('\t'.join(('id', 'family', 'formatter', 'ja_tokens', 'en_tokens', 'tokens_equal', 'flags', 'ja', 'en')) + '\n')
        for row in rows:
            f.write('\t'.join(esc(x) for x in row) + '\n')
    from collections import Counter
    c = Counter(x[1] for x in rows)
    fl = Counter(t for x in rows for t in x[6].split(',') if t)
    print('%d records -> %s' % (len(rows), out))
    print('families:', dict(sorted(c.items())))
    print('flags:', dict(sorted(fl.items())))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
