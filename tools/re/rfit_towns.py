"""rfit_towns: length statistics of the town short-name table (tbl@43858, HOMETOWN.BIN) and the club-word pool.

    python -I -X utf8 tools/re/rfit_towns.py

Prints the distribution of len(en) of the 1270 short names and, for each club word length, how many (town, word)
combinations would exceed the 13-character composed club name (`#sname#`, docs/expansion/field-widths.md 2.3) with and
without the 2-byte cut of the helper.  Read-only.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main():
    towns = []
    with open(os.path.join(ROOT, 'translation', 'FLOW_PRG__HOMETOWN.BIN.jsonl'), encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            if 'tbl@43858[' in (r.get('ctx') or ''):
                towns.append((r['ja'], r.get('en') or '', r.get('max_bytes')))
    c = Counter(len(en) for _, en, _ in towns)
    print('town short names: %d, with English %d' % (len(towns), sum(1 for t in towns if t[1])))
    print('len histogram', sorted(c.items()))
    words = []
    with open(os.path.join(ROOT, 'translation', 'FLOW_PRG__AUTOSAVE.BIN.jsonl'), encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            if 'tbl@247a8[' in (r.get('ctx') or ''):
                words.append(r.get('en') or '')
    print('club words', len(words), sorted(Counter(len(w) for w in words).items()))
    for cut in (0, 2):
        over = 0
        tot = 0
        for _, en, _ in towns:
            for w in words:
                tot += 1
                if len(en) - cut + len(w) > 13:
                    over += 1
        print('cut=%d: %d of %d combinations exceed 13 characters' % (cut, over, tot))
    print('longest short names:', sorted(((len(en), en) for _, en, _ in towns), reverse=True)[:12])


if __name__ == '__main__':
    main()
