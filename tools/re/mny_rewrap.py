"""mny_rewrap.py : re-wrap the English texts that contain `%m` so that they fit their window with the jp money style.

    python -I -X utf8 tools/re/mny_rewrap.py            # dry run: print every record that changes (and the ones that cannot be fixed)
    python -I -X utf8 tools/re/mny_rewrap.py --apply    # write the changed `en` fields into translation/*.jsonl (atomic per file)

The jp money text is up to 16 glyphs for every amount below 1000 Oku ('999 Oku 9999 Man'; the old validator budget for `%m` was 8).
A record is checked with `%m` replaced by that worst case (cells AND pixels of the proportional font, tools/pixelwidth.py).  Only
the LINE BREAKS of a failing record change, never a word: lines that fit are kept, an overflowing line pushes its last words to the
front of the next line (a new last line if there is none), colour spans `@X/...@` and the `=X/ ... =` wrappers are never split.
A record that would need more rows than its window has is reported and left alone.  Only records whose English contains `%m` are
considered; nothing else in translation/ is touched.  Exit 1 when a record could not be fixed.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import translib as T          # noqa: E402
import winwidth as WW         # noqa: E402
import pixelwidth as PX       # noqa: E402

WORST = '999 Oku 9999 Man'    # 16 glyphs: every amount below 1000 Oku


def atoms(line):
    """split a line into (word + trailing space) atoms; `@X/ ... @` spans are never split."""
    out, cur, in_span, i = [], '', False, 0
    while i < len(line):
        c = line[i]
        if not in_span and c == '@' and re.match(r'@[A-Z]+/', line[i:]):
            in_span = True
        elif in_span and c == '@':
            in_span = False
        if c == ' ' and not in_span:
            cur += c
            out.append(cur)
            cur = ''
            i += 1
            continue
        cur += c
        i += 1
    if cur:
        out.append(cur)
    return out


def fits(line, lim, table):
    s = line.rstrip(' ').replace('%m', WORST)
    if T.cells_of_line(s) > lim.max_cells:
        return False
    return PX.check_line(s, lim.max_cells, table)['ok']


def rewrap(en, lim, table):
    """-> new en, or None when it needs more rows than the window has."""
    lines = en.split('\n')
    trail = ''
    if lines and lines[-1] == '':
        lines.pop()
        trail = '\n'
    out = []
    carry = []
    queue = list(lines)
    while queue or carry:
        ln = queue.pop(0) if queue else ''
        words = carry + atoms(ln)
        carry = []
        cur = ''
        k = 0
        while k < len(words):
            if cur and not fits(cur + words[k], lim, table):
                break
            cur += words[k]
            k += 1
        if not cur:                                  # a single atom that does not fit: give up
            return None
        out.append(cur.rstrip(' '))
        carry = words[k:]
        if carry and not carry[-1].endswith(' '):
            carry[-1] += ' '                       # the join with the next line is a space
        if not queue and not carry:
            break
    # a last line of one word ('right?') looks bad: pull the last word of the line above down with it when both lines still fit
    if len(out) >= 2 and len(atoms(out[-1])) == 1 and len(atoms(out[-2])) >= 3:
        up = atoms(out[-2])
        cand_prev, cand_last = ''.join(up[:-1]).rstrip(' '), up[-1].rstrip(' ') + ' ' + out[-1]
        if fits(cand_last, lim, table) and fits(cand_prev, lim, table):
            out[-2], out[-1] = cand_prev, cand_last
    if len(out) > lim.max_rows:
        return None
    return '\n'.join(out) + trail


REWORD = {      # id -> new en (the money text of these three-row windows does not fit by moving line breaks; wording shortened)
    'FLOW_PRG/DRAFT.BIN#3db6c': "=W/Congratulations!\nYour contract with @Y/%s@ is agreed.\nDeal: @G/%m@ over @K/%d@ years.=",
    'FLOW_PRG/DRAFT.BIN#3dbc9': "On these terms, a @Y/%d-year@\ndeal with the transfer fee costs\n@Y/%m@ in total. Is that OK?",
    'FLOW_PRG/DRAFT.BIN#3dc7d': "From July on, half a year is added.\nA %d-year deal with the transfer fee\ncomes to @Y/%m@. Is that OK?",
    'FLOW_PRG/GETREP.BIN#2568c': "Upkeep plus club and Supporters' Club\nrunning costs for the month come to\n@Y/%m@, deducted from funds.",
    'FLOW_PRG/SPONSOR.BIN#2c7e1': "=K/As per the conditions, the sponsor fee\n@P/%m@ will be recovered.\nLet's not lose any more trust.=",
    'FLOW_PRG/SPONSOR2.BIN#2c825': "=K/As per the conditions, the sponsor fee\n@P/%m@ will be recovered.\nLet's not lose any more trust.=",
    'FLOW_PRG/SPT_CLUB.BIN#bf87': "Please set this year's annual running\ncosts. @Y/%m@ is suitable.\nOne twelfth is deducted every month.",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tdb', default='translation')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    db = T.load_db(T.resolve_path(a.tdb))
    import transwork as W
    items = W.build_items(db, W.aggregate(db))
    cat_of = {it['ja']: it['_cat'] for it in items}
    table = PX.get_table('on')
    changes = {}                      # file index -> {line index: new en}
    bad = []
    n_check = 0
    for fi, li, r in db.records():
        en = r.get('en') or ''
        if '%m' not in en or r.get('skip'):
            continue
        lim = WW.limits(r['ja'], cat_of.get(r['ja'], 'dialogue'), T.source_of(r['id']), r.get('ctx') or '')
        if lim.max_cells is None:
            continue
        n_check += 1
        if all(fits(l, lim, table) for l in en.split('\n')):
            continue
        new = REWORD.get(r['id']) or rewrap(en, lim, table)
        if new is None or not all(fits(l, lim, table) for l in new.split('\n')):
            bad.append((r['id'], en))
            continue
        if r['id'] not in REWORD:
            assert new.replace('\n', ' ').split() == en.replace('\n', ' ').split(), (en, new)       # words unchanged
        changes.setdefault(fi, {})[li] = new
        print('%s  (%s, %d rows max)\n    - %s\n    + %s' % (r['id'], lim.cls, lim.max_rows, en.replace('\n', '|'), new.replace('\n', '|')))
    nchg = sum(len(v) for v in changes.values())
    print('%d %%m records checked, %d to re-wrap, %d cannot be fixed' % (n_check, nchg, len(bad)))
    for rid, en in bad:
        print('UNFIXED', rid, en.replace('\n', '|'))
    if a.apply and changes:
        for fi, edits in changes.items():
            f = db.files[fi]
            # re-read right before writing: keep every other edit made meanwhile
            cur = T.load_db(T.resolve_path(a.tdb))
            cf = [x for x in cur.files if x.name == f.name][0]
            if not cf.plain or len(cf.recs) != len(f.recs):
                print('SKIP %s: file changed or not plain' % f.name)
                continue
            for li, new in edits.items():
                if cf.recs[li]['id'] != f.recs[li]['id'] or cf.recs[li].get('en') != f.recs[li].get('en'):
                    print('SKIP record %s: changed meanwhile' % f.recs[li]['id'])
                    continue
                cf.recs[li]['en'] = new
                cf.lines[li] = T.dump_record(cf.recs[li], cf.compact)
            T.write_atomic(cf.path, '\n'.join(cf.lines) + '\n')
            print('wrote', cf.path)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
