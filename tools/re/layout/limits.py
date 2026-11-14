"""Derive per-record layout limits (docs/layout-issues.md section 6) and write build/trans/layout_limits.tsv.

    python -I -X utf8 tools/re/layout/limits.py [--out build/trans/layout_limits.tsv]

Three kinds of rows (column `basis`):
  rule    a class limit measured / proven for one screen (hometown lists, person names, sponsor names)
  design  the Japanese string of the same fixed cell / label sets the budget: the English must not be wider (in half-width
          cells, token widths of translib.WIDTH_SUBST) than the Japanese it replaces, because the surrounding panel, column
          pitch and neighbouring cells were laid out for the Japanese.  Only table cells (ctx tbl@) and one-line labels
          (ctx ptr@) up to 24 cells are listed, and only those whose CURRENT English is wider.
Columns: scope, id, ja, en_now, ja_cells, en_cells, max_cells_plain, max_px_prop, max_chars_prop_est, basis, note.
max_px_prop = max_cells_plain * 12 (the pixel budget does not change with the font); max_chars_prop_est = max_px / 10.0
(weighted mean advance of English text with the proportional font, docs/font-widths.md).  A proportional-font validator should
use the real width table and compare against max_px_prop.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import translib as T  # noqa: E402


def row(scope, rid, ja, en, jc, ec, maxc, basis, note=''):
    return [scope, rid, ja.replace('\n', '\\n').replace('\t', ' '), en.replace('\n', '\\n').replace('\t', ' '),
            str(jc), str(ec), str(maxc), str(maxc * 12), '%.0f' % (maxc * 12 / 10.0), basis, note]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'trans', 'layout_limits.tsv'))
    a = ap.parse_args()
    rows = []
    # ---- class rules (evidence in docs/layout-issues.md)
    rules = [
        ('hometown.region', 'HOMETOWN.BIN region list (12 text objects, 20-cell windows, leading blank added by the builder)', 38,
         'plain: 38 chars; the builder (FUN 0x8c2d2a50) cuts 4- and 6-byte strings into pairs unless tools/layoutpatch.py is applied'),
        ('hometown.prefecture', 'HOMETOWN.BIN prefecture list (50 text objects, tbl@42200 slots 8/12 bytes)', 11,
         'slot 8 bytes = 7 chars, 12 bytes = 11 chars (budget_fixed); same spacer caveat'),
        ('hometown.town', 'HOMETOWN.BIN town list: 126-byte records, name field 35 bytes; short table tbl@43858 slots 8 bytes', 7,
         'short table 7 chars; record name 34 chars; same spacer caveat'),
        ('person.name', 'player / staff names in list and card panels (BPINFO 14-byte field)', 12,
         'observed: a 13-char name is cut to 12 in the Event list and the player card; ladder Given Family -> G. Family -> Family'),
        ('sponsor.suffix', 'sponsor name = #to# (town, up to 7 chars) + suffix: whole name <= 16 cells', 9,
         'suffix incl. its leading space <= 9 chars; estimate from the reported overflow of "Aogashi Steamship" (17)'),
    ]
    for scope, what, maxc, note in rules:
        rows.append(row(scope, '*', what, '', 0, 0, maxc, 'rule', note))
    # ---- person names
    recs = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(f, encoding='utf8') as fh:
            for line in fh:
                if line.strip():
                    recs.append(json.loads(line))
    n_names = 0
    seen_ja = set()
    for r in recs:
        if r['id'].startswith('ETC_DATA/BPINFO.BIN#') and r.get('en') and len(r['en']) > 12 and r['ja'] not in seen_ja:
            seen_ja.add(r['ja'])
            rows.append(row('person.name', r['id'], r['ja'], r['en'], T.cells_of_line(r['ja']), len(r['en']), 12, 'rule',
                            'over the 12-char panel limit'))
            n_names += 1
    # ---- sponsor suffixes
    for r in recs:
        ja = r['ja']
        if ja.startswith('#to#') and '\n' not in ja and len(ja) < 12 and r.get('en') and r['id'].startswith('FLOW_PRG/OFFICE.BIN#'):
            suf = r['en'][4:]
            rows.append(row('sponsor.suffix', r['id'], ja, r['en'], T.cells_of_line(ja[4:]), len(suf), 9, 'rule',
                            'suffix incl. leading space; ok' if len(suf) <= 9 else 'over'))
    # ---- design-derived: table cells / short labels wider than the Japanese
    over = collections.Counter()
    seen = set()
    for r in recs:
        en = r.get('en') or ''
        ja = r['ja']
        ctx = r.get('ctx') or ''
        if not en or '\n' in ja or r.get('orphan'):
            continue
        if not (ctx.startswith('tbl@') or ctx.startswith('ptr@')):
            continue
        if r['id'].startswith(('ETC_DATA/', 'FLOW_PRG/HOMETOWN.BIN')):
            continue
        jc = T.cells_of_line(ja)
        ec = T.cells_of_line(en)
        if jc == 0 or jc > 24 or ec <= jc:
            continue
        key = (ja, en)
        if key in seen:
            continue
        seen.add(key)
        src = r['id'].split('#')[0]
        over[src] += 1
        rows.append(row('cell.table' if ctx.startswith('tbl@') else 'cell.label', r['id'], ja, en, jc, ec, jc, 'design',
                        'wider than the Japanese by %d cells' % (ec - jc)))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    hdr = ['scope', 'id', 'ja', 'en_now', 'ja_cells', 'en_cells', 'max_cells_plain', 'max_px_prop', 'max_chars_prop_est', 'basis', 'note']
    with open(a.out, 'w', encoding='utf8', newline='') as f:
        f.write('\t'.join(hdr) + '\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    print('wrote %s: %d rows (%d person names over 12, %d design-derived cells over their Japanese width in %d sources)' % (
        a.out, len(rows), n_names, sum(over.values()), len(over)))
    for s, n in over.most_common(15):
        print('  %-34s %d' % (s, n))


if __name__ == '__main__':
    main()
