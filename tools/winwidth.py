"""winwidth: text-window width classes (docs/window-widths.md).

    python -I -X utf8 tools/winwidth.py classes     [--tdb translation] [--out build/trans]   -> width_classes.tsv, width_tables.tsv
    python -I -X utf8 tools/winwidth.py violations  [--tdb translation] [--out build/trans]   -> width_violations.tsv (merged en over its window)
        [--width-mode cells|pixels|both] [--px-profile on|ideal|off]
        cells (default) writes width_violations.tsv; pixels writes width_violations_px.tsv (the texts that are still over their window
        when the line width is measured in pixels with the proportional font advance table, tools/pixelwidth.py, docs/pixel-widths.md);
        both writes both.  Every run prints how many cell-mode violations disappear / appear in pixel mode.
    python -I -X utf8 tools/winwidth.py show TEXT                                             -> the class of one Japanese text shape
    python -I -X utf8 tools/winwidth.py recheck LIST.tsv [--out-file F]  (default: LIST with _px.tsv)
        re-measure a cell-format violations list in pixels (needs no database), write what remains
    python -I -X utf8 tools/winwidth.py wrap TEXT CELLS [--width-mode cells|pixels]           -> word wrap of an English text (backslash n = newline)

Library:  limits(ja, cat, source, ctx) -> Limit(max_cells, max_rows, cls, basis)   (pure function of the Japanese text, its
category, its source overlay and table context: independent of `en`).  tools/transwork.py puts the minimum over the records of a
distinct text into every shard item (`max_cells`, `max_rows`, `wclass`); tools/transcheck.py enforces them.

Window geometry (docs/font-hook-notes.md s3.3): a window of W cells (obj+0x3c) takes 2W-1 half-width glyphs per line
(flag obj+0x45 = 1; 2W for full-width Japanese) and `rows` lines (obj+0x3d).  The two text windows every overlay builds:
    bubble   W=17 rows=2  -> 33 half-width cells   (the face "speech bubble": FIRE, CAP_SLCT, ...)
    msg      W=20 rows=3  -> 39 half-width cells   (secretary / bottom window; HELP, NEWS, EVENT ...)
Which of the two shows a given string is not recoverable from the code (the string -> window link goes through a script /
state machine), so the class is taken from the strongest evidence available, in this order (`basis`):
    tbl-msg / tbl-bubble   the function that loads the pointer table reaches factories of one class only (tools/winwidth_tables.tsv)
    ovl-no-bubble          the overlay contains no 17x2 factory at all (tools/winwidth_overlays.tsv): every text window is 20x3
    ja-3rows               the Japanese has >= 3 lines: only the 20x3 window has three rows
    ja-wide                a Japanese line is wider than 34 cells: the window is wider than 17 cells
    ja-fit                 <= 2 lines and every line <= 34 cells: bubble or msg cannot be told apart -> conservative 33 cells, 2 rows
    cell                   not prose (label / name / place / number / tactic): the cell is fixed by the screen layout, 39 default
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translib as T  # noqa: E402
import pixelwidth as PX  # noqa: E402

BUBBLE_CELLS, BUBBLE_ROWS = 33, 2       # W = 17: 2W-1 half-width glyphs
MSG_CELLS, MSG_ROWS = 39, 3             # W = 20
JA_BUBBLE_MAX = 34                      # 17 full-width characters: the widest Japanese line a W = 17 window holds
PROSE = frozenset(['dialogue', 'meeting', 'event', 'training', 'news', 'system', 'dataroom', 'help'])

OV_PATH = os.path.join(HERE, 'winwidth_overlays.tsv')
TB_PATH = os.path.join(HERE, 'winwidth_tables.tsv')


class Limit(collections.namedtuple('Limit', 'max_cells max_rows cls basis')):
    pass


_OV = None
_TB = None


def _load():
    global _OV, _TB
    if _OV is None:
        _OV = {}
        if os.path.exists(OV_PATH):
            with open(OV_PATH, encoding='utf-8', newline='') as fh:
                for r in csv.DictReader(fh, delimiter='\t'):
                    _OV[r['source']] = r
        _TB = {}
        if os.path.exists(TB_PATH):
            with open(TB_PATH, encoding='utf-8', newline='') as fh:
                for r in csv.DictReader(fh, delimiter='\t'):
                    _TB[(r['source'], r['key'])] = r['verdict']
    return _OV, _TB


def table_key(ctx):
    m = re.match(r'(tbl|ptr)@([0-9a-f]+)', ctx or '')
    return '%s@%s' % (m.group(1), m.group(2)) if m else None


def ja_shape(ja):
    """-> (lines, widest line in cells) of a Japanese text (token widths of translib)."""
    ls = ja.split('\n')
    return len(ls), max(T.cells_of_line(l) for l in ls)


def limits(ja, cat, source, ctx):
    ov, tb = _load()
    kind = T.record_kind(source)
    if kind in ('ini', 'ptrblob') and source != '1ST_READ.BIN':
        return Limit(None, None, 'BROWSER', 'browser')           # HTML text: no cell rule
    lines, w = ja_shape(ja)
    if cat not in PROSE:
        return Limit(T.MAX_CELLS, max(lines, 1), 'CELL', 'cell')
    row = ov.get(source)
    known = bool(row and row['window_lib'] == 'yes' and row['font_slots'] == 'yes')
    verdict = tb.get((source, table_key(ctx))) if table_key(ctx) else None
    if verdict == 'msg':
        return Limit(MSG_CELLS, max(lines, MSG_ROWS), 'MSG20x3', 'tbl-msg')
    if lines >= 3:
        return Limit(MSG_CELLS, max(lines, MSG_ROWS), 'MSG20x3', 'ja-3rows')
    if w > JA_BUBBLE_MAX:
        return Limit(MSG_CELLS, max(lines, MSG_ROWS), 'MSG20x3', 'ja-wide')
    if known and row['bubble_17x2'] == 'no':
        return Limit(MSG_CELLS, max(lines, MSG_ROWS), 'MSG20x3', 'ovl-no-bubble')
    if verdict == 'bubble':
        return Limit(BUBBLE_CELLS, BUBBLE_ROWS, 'BUBBLE17x2', 'tbl-bubble')
    return Limit(BUBBLE_CELLS, BUBBLE_ROWS, 'BUBBLE?', 'ja-fit')


def merge_limits(lims):
    """Strictest of the limits of all records of one distinct text -> Limit (None when no record has a cell rule)."""
    lims = [l for l in lims if l.max_cells is not None]
    if not lims:
        return Limit(None, None, 'BROWSER', 'browser')
    best = min(lims, key=lambda l: (l.max_cells, l.max_rows))
    rows = min(l.max_rows for l in lims if l.max_cells == best.max_cells)
    return Limit(best.max_cells, rows, best.cls, best.basis)


def check_en(en, lim, ja):
    """-> (n_lines, widths per line, over_cells (max), rows_over) of a candidate English text against a Limit."""
    lines = en.split('\n')
    ws = [T.cells_of_line(l) for l in lines]
    over = max([w - lim.max_cells for w in ws] + [0]) if lim.max_cells else 0
    ja_lines = len(ja.split('\n'))
    allowed = max(ja_lines, 1)
    rows_over = max(len(lines) - max(allowed, 1), 0)
    return len(lines), ws, over, rows_over


# ------------------------------------------------------------------- CLI ----

def _items(db):
    """-> {ja: (category, canonical record id, area, shard-order tuple)} via transwork (imported lazily)."""
    import transwork as W
    aggs = W.aggregate(db)
    items = W.build_items(db, aggs)
    return items


def cmd_classes(a):
    db = T.load_db(T.resolve_path(a.tdb))
    items = _items(db)
    cat_of = {it['ja']: it['_cat'] for it in items}
    out = T.resolve_path(a.out)
    os.makedirs(out, exist_ok=True)
    tab = collections.defaultdict(lambda: [0, collections.Counter(), 0, 0, None])
    n = 0
    with open(os.path.join(out, 'width_classes.tsv'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('id\tsource\ttable\tja_lines\tja_cells\tclass\tmax_cells\tmax_rows\tbasis\n')
        for fi, li, r in db.records():
            src = T.source_of(r['id'])
            ctx = r.get('ctx') or ''
            lim = limits(r['ja'], cat_of[r['ja']], src, ctx)
            ln, w = ja_shape(r['ja'])
            tk = table_key(ctx) or '-'
            fh.write('%s\t%s\t%s\t%d\t%d\t%s\t%s\t%s\t%s\n' % (
                r['id'], src, tk, ln, w, lim.cls, '' if lim.max_cells is None else lim.max_cells,
                '' if lim.max_rows is None else lim.max_rows, lim.basis))
            n += 1
            t = tab[(src, tk)]
            t[0] += 1
            t[1][(lim.cls, lim.basis)] += 1
            t[2] = max(t[2], w)
    with open(os.path.join(out, 'width_tables.tsv'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('source\ttable\trecords\tja_max_cells\tclasses (class:basis x count)\n')
        for (src, tk), t in sorted(tab.items()):
            if tk == '-':
                continue
            fh.write('%s\t%s\t%d\t%d\t%s\n' % (src, tk, t[0], t[2], ' '.join('%s:%s x%d' % (c, b, k) for (c, b), k in sorted(t[1].items()))))
    print('width_classes.tsv: %d records' % n)
    cnt = collections.Counter()
    for fi, li, r in db.records():
        lim = limits(r['ja'], cat_of[r['ja']], T.source_of(r['id']), r.get('ctx') or '')
        cnt[(lim.cls, lim.basis)] += 1
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print('  %-11s %-14s %7d records' % (k[0], k[1], v))


def check_en_px(en, lim, ja, table):
    """Pixel-mode counterpart of check_en -> (n_lines, widths px per line, over_px (max), wrapped rows).
    A line is over when the pen start of its last glyph is beyond 12*(max_cells-1) px (tools/pixelwidth.py); CELL-class texts must
    also satisfy the cell rule.  wrapped rows = rows after the engine's mid-word break."""
    lines = en.split('\n')
    res = [PX.check_line(l, lim.max_cells, table, 'game', 'CELL' if lim.cls == 'CELL' else None) for l in lines]
    return len(lines), [r['px'] for r in res], max([r['over'] for r in res] + [0]), sum(r['rows'] for r in res)


def _violation_rows(items, shard_of, en_of, lims, mode, table):
    """-> (rows sorted for output, number of texts checked) for width mode 'cells' or 'pixels'."""
    import transwork as W
    rows = []
    n_checked = 0
    for it in items:
        en = en_of.get(it['ja'])
        if not en or it['kind'] in ('ini', 'ptrblob') or it['skip']:
            continue
        n_checked += 1
        lim = merge_limits(lims[it['ja']])
        if lim.max_cells is None:
            continue
        if mode == 'pixels':
            nl, ws, over, wrapped = check_en_px(en, lim, it['ja'], table)
        else:
            nl, ws, over, _ro = check_en(en, lim, it['ja'])
            # wrapped length: a line longer than the window wraps and costs extra rows (the game has no word wrap)
            wrapped = sum(max(1, -(-w // lim.max_cells)) for w in ws)
        rows_over = max(nl - max(lim.max_rows, it['lines']), 0)          # more lines than the window has rows
        if over <= 0 and rows_over <= 0:
            continue
        area = it['_area']
        vis = 'A' if area <= W.AREA_IDX['meeting'] else ('B' if area <= W.AREA_IDX['match_ui'] else 'C')
        rows.append((it['_order'], it, lim, nl, ws, over, rows_over, wrapped, vis, en, shard_of.get(it['key'])))
    rows.sort(key=lambda x: (x[8], x[0], x[1]['key']))
    return rows, n_checked


def _esc(en):
    return en.replace('\\', '\\\\').replace('\n', '\\n').replace('\t', ' ')


def _write_cells_tsv(path, rows, W):
    out = ['rank\tvisibility\tshard\tkey\tid0\tarea\tcategory\tclass\tmax_cells\tmax_rows\tbasis\trecords\ten_lines\tja_lines\twidest\tover_by\twrapped_rows\ten\tja\n']
    for rank, (order, it, lim, nl, ws, over, rows_over, wrapped, vis, en, shard) in enumerate(rows, 1):
        out.append('\t'.join([
            str(rank), vis, str(shard), it['key'], it['id0'], W.AREAS[it['_area']][0], it['_cat'], lim.cls,
            str(lim.max_cells), str(lim.max_rows), lim.basis, str(it['ids_count']), str(nl), str(it['lines']),
            str(max(ws)), str(max(over, 0)), str(wrapped), _esc(en), it['ja'].replace('\n', '\\n').replace('\t', ' ')]) + '\n')
    T.write_atomic(path, ''.join(out))


def _write_px_tsv(path, rows, W, cell_keys):
    """width_violations_px.tsv: the texts over their window in pixel mode.  in_cell_list = yes when the text is also in
    width_violations.tsv, new when it is over only because of the pixel rule (13 px capitals, 12 px spaces, name tokens)."""
    out = ['rank\tvisibility\tshard\tkey\tid0\tarea\tcategory\tclass\tmax_cells\tmax_rows\tbasis\trecords\ten_lines\tja_lines\t'
           'widest_px\tmax_px\tover_px\twrapped_rows\twidest_cells\tin_cell_list\ten\tja\n']
    for rank, (order, it, lim, nl, ws, over, rows_over, wrapped, vis, en, shard) in enumerate(rows, 1):
        wcells = max(T.cells_of_line(l) for l in en.split('\n'))
        out.append('\t'.join([
            str(rank), vis, str(shard), it['key'], it['id0'], W.AREAS[it['_area']][0], it['_cat'], lim.cls,
            str(lim.max_cells), str(lim.max_rows), lim.basis, str(it['ids_count']), str(nl), str(it['lines']),
            str(max(ws)), str(PX.limit_px(lim.max_cells)), str(max(over, 0)), str(wrapped), str(wcells),
            'yes' if it['key'] in cell_keys else 'new', _esc(en), it['ja'].replace('\n', '\\n').replace('\t', ' ')]) + '\n')
    T.write_atomic(path, ''.join(out))


def _summary(label, rows):
    by = collections.Counter((r[8], r[2].cls, r[2].basis) for r in rows)
    print('%s: texts over their window: %d (records %d)' % (label, len(rows), sum(r[1]['ids_count'] for r in rows)))
    for k, v in sorted(by.items()):
        print('  vis %s  %-11s %-14s %6d texts' % (k[0], k[1], k[2], v))
    print('  by category:', dict(collections.Counter(r[1]['_cat'] for r in rows)))


def cmd_violations(a):
    db = T.load_db(T.resolve_path(a.tdb))
    import transwork as W
    aggs = W.aggregate(db)
    items = W.build_items(db, aggs)
    # shard numbers (same order as the plan)
    shards = W.build_shards(items)
    shard_of = {}
    for sh in shards:
        for it in sh['items']:
            shard_of[it['key']] = sh['shard']
    en_of = {}
    lims = collections.defaultdict(list)
    for fi, li, r in db.records():
        if r.get('en'):
            en_of[r['ja']] = r['en']
    cat_of = {it['ja']: it['_cat'] for it in items}
    for fi, li, r in db.records():
        lims[r['ja']].append(limits(r['ja'], cat_of[r['ja']], T.source_of(r['id']), r.get('ctx') or ''))
    table = PX.get_table(a.px_profile)
    mode = a.width_mode
    rows_c, n_checked = _violation_rows(items, shard_of, en_of, lims, 'cells', table)
    rows_p, _ = _violation_rows(items, shard_of, en_of, lims, 'pixels', table)
    out = T.resolve_path(a.out)
    print('merged texts checked: %d' % n_checked)
    cell_keys = {r[1]['key'] for r in rows_c}
    px_keys = {r[1]['key'] for r in rows_p}
    if mode in ('cells', 'both'):
        _write_cells_tsv(os.path.join(out, 'width_violations.tsv'), rows_c, W)
        _summary('cells', rows_c)
    if mode in ('pixels', 'both'):
        _write_px_tsv(os.path.join(out, 'width_violations_px.tsv'), rows_p, W, cell_keys)
        _summary('pixels (profile %s)' % a.px_profile, rows_p)
    gone = cell_keys - px_keys
    print('pixel mode vs cell mode: %d of %d cell violations disappear (%d remain), %d texts are over only in pixel mode' % (
        len(gone), len(cell_keys), len(cell_keys & px_keys), len(px_keys - cell_keys)))
    rec = {r[1]['key']: r[1]['ids_count'] for r in rows_c}
    print('  records: %d of %d cell-violation records disappear' % (sum(rec[k] for k in gone), sum(rec.values())))


def cmd_recheck(a):
    """Measure the texts of an existing width_violations.tsv (cell format) in pixels: which of them are still over their
    window?  Needs no database: the TSV carries the English text, the class and the limits.  Writes the remainder in the
    width_violations_px.tsv format to --out-file."""
    if not a.out_file:
        a.out_file = os.path.splitext(a.list)[0] + '_px.tsv'
    with open(T.resolve_path(a.list), encoding='utf-8', newline='') as fh:
        src = list(csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE))
    table = PX.get_table(a.px_profile)
    keep = []
    gone = collections.Counter()
    left = collections.Counter()
    gone_rec = left_rec = 0
    for r in src:
        en = r['en'].replace('\\n', '\n').replace('\\\\', '\\')
        lim = Limit(int(r['max_cells']), int(r['max_rows']), r['class'], r['basis'])
        nl, ws, over, wrapped = check_en_px(en, lim, r['ja'].replace('\\n', '\n'), table)
        rows_over = max(nl - max(lim.max_rows, int(r['ja_lines'])), 0)
        tier = r['visibility']
        if over <= 0 and rows_over <= 0:
            gone[tier] += 1
            gone_rec += int(r['records'])
            continue
        left[tier] += 1
        left_rec += int(r['records'])
        keep.append([r['rank'], tier, r['shard'], r['key'], r['id0'], r['area'], r['category'], r['class'], r['max_cells'],
                     r['max_rows'], r['basis'], r['records'], str(nl), r['ja_lines'], str(max(ws)), str(PX.limit_px(lim.max_cells)),
                     str(max(over, 0)), str(wrapped), r['widest'], 'yes', r['en'], r['ja']])
    head = ('rank\tvisibility\tshard\tkey\tid0\tarea\tcategory\tclass\tmax_cells\tmax_rows\tbasis\trecords\ten_lines\tja_lines\t'
            'widest_px\tmax_px\tover_px\twrapped_rows\twidest_cells\tin_cell_list\ten\tja\n')
    T.write_atomic(T.resolve_path(a.out_file), head + ''.join('\t'.join(k) + '\n' for k in keep))
    print('%s: %d texts (%d records); pixel mode (profile %s): %d disappear (%d records), %d remain (%d records)' % (
        a.list, len(src), sum(int(r['records']) for r in src), a.px_profile, sum(gone.values()), gone_rec, len(keep), left_rec))
    for t in sorted(set(gone) | set(left)):
        print('  tier %s: %d disappear, %d remain' % (t, gone[t], left[t]))
    ov = collections.Counter(min(int(k[16]), 99) for k in keep)
    print('  remaining overshoot (px): %s' % ', '.join('%s:%d' % (k, v) for k, v in sorted(ov.items())))
    print('  remaining by class/basis:', dict(collections.Counter((k[7], k[10]) for k in keep)))


def cmd_show(a):
    ja = a.text.replace('\\n', '\n')
    for cat in ('dialogue', 'label'):
        print(cat, limits(ja, cat, a.source, a.ctx))


def cmd_wrap(a):
    print(PX.wrap_text(a.text.replace('\\n', '\n'), a.cells, a.width_mode, PX.get_table(a.px_profile)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name, fn in (('classes', cmd_classes), ('violations', cmd_violations)):
        p = sub.add_parser(name)
        p.add_argument('--tdb', default='translation')
        p.add_argument('--out', default='build/trans')
        if name == 'violations':
            p.add_argument('--width-mode', choices=['cells', 'pixels', 'both'], default='cells',
                           help='list to write: cells -> width_violations.tsv (default), pixels -> width_violations_px.tsv, both')
            p.add_argument('--px-profile', choices=PX.PROFILES, default=PX.DEFAULT_PROFILE,
                           help='advance table of the pixel mode (default: the table of build_patch --proportional-font on)')
        p.set_defaults(fn=fn)
    p = sub.add_parser('recheck')
    p.add_argument('list', help='a width_violations.tsv in the cell format')
    p.add_argument('--out-file', default=None,
                   help='default: next to LIST with _px.tsv instead of .tsv (width_violations.tsv -> width_violations_px.tsv); never a name of another list')
    p.add_argument('--px-profile', choices=PX.PROFILES, default=PX.DEFAULT_PROFILE)
    p.set_defaults(fn=cmd_recheck)
    p = sub.add_parser('wrap')
    p.add_argument('text')
    p.add_argument('cells', type=int)
    p.add_argument('--width-mode', choices=['cells', 'pixels'], default='cells')
    p.add_argument('--px-profile', choices=PX.PROFILES, default=PX.DEFAULT_PROFILE)
    p.set_defaults(fn=cmd_wrap)
    p = sub.add_parser('show')
    p.add_argument('text')
    p.add_argument('--source', default='FLOW_PRG/MEETING.BIN')
    p.add_argument('--ctx', default='')
    p.set_defaults(fn=cmd_show)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == '__main__':
    main()
