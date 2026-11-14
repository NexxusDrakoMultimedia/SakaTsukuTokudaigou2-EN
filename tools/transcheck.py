"""transcheck: validate candidate English strings against their shard items.

    python -I -X utf8 tools/transcheck.py RESULT.json [--shards DIR] [--shard-file PATH]
                                          [--json] [--rejects PATH] [--extra-lines N] [--allow-missing]
                                          [--width-mode cells|pixels] [--px-profile on|ideal|off]

RESULT.json is a shard result file  {"shard": N, "results": [{"key": "...", "en": "..."}, ...]}
(optional "note" fields are ignored).  The items come from build/trans/shards/NNNN.json (written by
`transwork.py plan`).  Exit codes: 0 = no errors (warnings allowed), 1 = validation errors in a well-formed file,
2 = malformed or unreadable input (not JSON, top level not an object, "results" missing / null / not a list or map,
bad "shard", shard file missing or broken) or usage error.  A UTF-8 BOM in the result file is accepted.

Rules (docs/style-guide.md section 2 is binding; every rule has an error code):
  EMPTY             en empty (only items with a `skip` hint may be left empty)
  NON_ASCII         a character outside 0x20-0x7E (newline is the only control character allowed)
  FORBIDDEN_CHAR    backslash or tilde (0x5C draws as a yen sign, 0x7E as an overline)
  STRAY_CHAR        '@' '=' '#' or '%' that is not part of a control token of the Japanese text
  TOKEN_MISMATCH    control tokens differ from the Japanese as a multiset (missing / extra)
  TOKEN_ORDER       printf formats (%s %d ...) reordered, or colour / window spans no longer open-close
  LINE_TOO_WIDE     a line is wider than the item's window (item.max_cells: 39 in the 20-cell window, 33 in a 17-cell speech
                    bubble, docs/window-widths.md; 39 when the item has no max_cells; token expansion widths of docs/capacity-ratio.md)
                    --width-mode pixels (docs/pixel-widths.md) counts pixels instead: the advance table of the proportional font
                    (tools/pixelwidth.py, profile --px-profile, default the table of `build_patch.py --proportional-font on`), names
                    and numbers at their worst case; the line must satisfy  pen start of its last glyph <= 12*(max_cells-1) px.
  PUNCT_AT_EDGE     a line that fills all max_cells cells ends in . , ! ? (ASCII punctuation cannot hang into the margin;
                    cells mode only: the pixel rule has no such edge, the engine draws any glyph that starts inside the window)
  TOO_MANY_LINES    more lines than the Japanese (+ --extra-lines for movable items; fixed items never)
  OVER_BUDGET       len(en) + 1 > budget_fixed (fixed slot: orphan / stride table / interior ptr / BPINFO / 2_DP)
  LEADING_SPACE / TRAILING_SPACE / EMPTY_LINE   layout whitespace the Japanese does not have
  NEWLINE_IN_INI    newline in a one-line browser (MESSAGE.INI) value
  MISSING / UNKNOWN_KEY / DUPLICATE_KEY / BAD_ENTRY    result-file level problems
Warnings (never fail the run): WARN_LONG (movable text above 1.05 x the Japanese bytes), HONORIFIC,
STACKED_PUNCT, ELLIPSIS, DOUBLE_SPACE, US_SPELLING, EMPTY_SPAN.
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translib as T  # noqa: E402
import pixelwidth as PX  # noqa: E402

SUGGEST = {          # likely replacements for the usual non-ASCII intruders
    '‘': "'", '’': "'", '“': '"', '”': '"', '–': '-', '—': '-',
    '…': '...', '×': 'x', '·': '.', '•': '-', '　': ' ', ' ': ' ',
    '「': '"', '」': '"', '『': '"', '』': '"', '！': '!', '？': '?',
    '、': ',', '。': '.', '〜': '-', 'é': 'e', 'è': 'e', 'ü': 'u',
    'ō': 'o', 'ū': 'u', 'ö': 'o', 'ä': 'a', 'á': 'a', 'ó': 'o',
}
HONORIFIC_RE = re.compile(r'\b[A-Za-z]+-(san|kun|sama|chan|senshu)\b')
STACKED_RE = re.compile(r'[!?]{3,}|!!|\?\?')
ELLIPSIS_RE = re.compile(r'\.{4,}')
US_RE = re.compile(r'\b(color|colors|center|centers|defense|offense|organize|organized|gray|traveling|meter|meters)\b', re.I)
PUNCT_END = '.,!?'


def _err(code, msg, hint='', **detail):
    d = {'code': code, 'msg': msg}
    if hint:
        d['hint'] = hint
    d.update(detail)
    return d


def check_text(item, en, extra_lines=0, width_mode='cells', px_profile=PX.DEFAULT_PROFILE):
    """-> (errors, warnings) for one candidate string.  item: a shard item (needs ja; uses
    budget_fixed, lines, skip, kind when present).  width_mode 'cells' (default: one cell per glyph) or 'pixels'
    (tools/pixelwidth.py advance table of px_profile)."""
    errs, warns = [], []
    ja = item['ja']
    kind = item.get('kind') or 'overlay'
    mode = T.mode_of_kind(kind)
    skip = item.get('skip')
    if not isinstance(en, str):
        return [_err('BAD_ENTRY', 'en is not a string', 'return a JSON string')], warns
    if en == '':
        if skip:
            return errs, warns                      # skip-hinted item left untouched: fine
        return [_err('EMPTY', 'empty translation', 'every item without a skip hint needs an English string')], warns
    if en.strip() == '':
        # whitespace-only is never a translation, skip-hinted or not (the only exception: a blank Japanese text that
        # a skip-hinted item keeps identical)
        if skip and ja.strip() == '' and en == ja:
            return errs, warns
        return [_err('EMPTY', 'whitespace-only translation', 'return real text, or "" for a skip-hinted item')], warns
    if skip and en == ja:
        return errs, warns                          # skip-hinted item kept identical to the Japanese

    # --- characters -------------------------------------------------------------------------
    bad = [(i, c) for i, c in enumerate(en) if not (0x20 <= ord(c) <= 0x7e or c == '\n')]
    if bad:
        shown = ', '.join('%r (U+%04X)%s' % (c, ord(c), (' -> use %r' % SUGGEST[c]) if c in SUGGEST else '')
                          for _, c in bad[:5])
        errs.append(_err('NON_ASCII', 'non-ASCII or control character: ' + shown,
                         'ASCII 0x20-0x7E plus newline only; no accents, curly quotes, dashes or bullets',
                         positions=[i for i, _ in bad[:10]]))
    for ch, why in (('\\', 'draws as a yen sign'), ('~', 'draws as an overline')):
        if ch in en:
            errs.append(_err('FORBIDDEN_CHAR', 'forbidden character %r (%s)' % (ch, why),
                             'remove it; use "-" for ranges', char=ch))

    # --- control tokens -----------------------------------------------------------------------
    ja_t = T.canon_tokens(T.tokens_of(ja, mode))
    en_t = T.canon_tokens(T.tokens_of(en, mode))
    jc, ec = collections.Counter(ja_t), collections.Counter(en_t)
    missing = sorted((jc - ec).elements())
    extra = sorted((ec - jc).elements())
    if missing or extra:
        parts = []
        if missing:
            parts.append('missing %s' % ' '.join(missing))
        if extra:
            parts.append('extra %s' % ' '.join(extra))
        hint = 'copy every control token of the Japanese exactly'
        if any(t in ('@', '=') or t.startswith('#') for t in extra):
            hint += ' ; never type @ = # yourself (write "at", "No.", "and", "plus")'
        errs.append(_err('TOKEN_MISMATCH', 'control tokens differ: ' + '; '.join(parts), hint,
                         missing=missing, extra=extra, expected=ja_t))
    rest = T.strip_tokens(en, mode)
    stray = sorted({c for c in rest if c in (T.BROWSER_STRAY if mode == 'browser' else T.GAME_STRAY)})
    if stray:
        errs.append(_err('STRAY_CHAR', 'character(s) %s outside a control token' % ' '.join(repr(c) for c in stray),
                         '@ = # and a lone % are control characters; write "at", "No.", "and", "percent"',
                         chars=stray))
    if not (missing or extra):
        if T.printf_order(ja_t) != T.printf_order(en_t):
            errs.append(_err('TOKEN_ORDER', 'printf formats reordered: expected %s, got %s' % (
                ' '.join(T.printf_order(ja_t)), ' '.join(T.printf_order(en_t))),
                'formats are filled positionally; keep %s %d %D %m in the Japanese order (rephrase the sentence)'))
        if mode == 'game':
            jcol, jwin = T.pair_sequences(ja_t)
            ecol, ewin = T.pair_sequences(en_t)
            for name, jseq, eseq in (('colour @X/ .. @', jcol, ecol), ('window =X/ .. =', jwin, ewin)):
                if T.alternates(jseq) and not T.alternates(eseq):
                    errs.append(_err('TOKEN_ORDER', '%s spans are not open/close in order' % name,
                                     'each opener must be followed by its closer before the next opener'))
            if re.search(r'@[A-Z]/@|=[A-Za-z]/=', en) and not re.search(r'@[A-Z]/@|=[A-Za-z]/=', ja):
                warns.append(_err('EMPTY_SPAN', 'colour/window span with nothing inside'))

    # --- layout ---------------------------------------------------------------------------------
    lines = en.split('\n')
    ja_lines = ja.split('\n')
    n_ja = int(item.get('lines') or len(ja_lines))
    fixed = item.get('budget_fixed') is not None
    allowed = n_ja + (0 if fixed else int(extra_lines))
    # the text window of the string (tools/winwidth.py): cells per line and rows; items of an older shard have neither (39 cells)
    max_cells = item.get('max_cells')
    if max_cells is None:
        max_cells = T.MAX_CELLS
    max_rows = item.get('max_rows')
    if max_rows is not None:
        allowed = min(allowed, max(int(max_rows), n_ja))
    if mode == 'browser' and '\n' in en and kind == 'ini':
        errs.append(_err('NEWLINE_IN_INI', 'newline in a one-line MESSAGE.INI value', 'use <br> where the Japanese uses it'))
    if len(lines) > allowed:
        errs.append(_err('TOO_MANY_LINES', '%d lines, the Japanese has %d%s' % (
            len(lines), n_ja, '' if not extra_lines or fixed else ' (+%d allowed)' % extra_lines),
            'rewrite shorter so it fits the original line count', lines=len(lines), allowed=allowed))
    lead_ok = any(l[:1] in (' ', '　') for l in ja_lines)
    trail_ok = any(l[-1:] in (' ', '　') for l in ja_lines)
    blank_ok = any(l == '' for l in ja_lines)
    for i, l in enumerate(lines):
        if l == '':
            if not blank_ok and len(lines) > 1:
                errs.append(_err('EMPTY_LINE', 'empty line %d' % (i + 1), 'the Japanese has no empty line', line=i + 1))
            continue
        if l[0] == ' ' and not lead_ok:
            errs.append(_err('LEADING_SPACE', 'line %d starts with a space' % (i + 1), 'break lines at the space, not after it', line=i + 1))
        if l[-1] == ' ' and not trail_ok:
            errs.append(_err('TRAILING_SPACE', 'line %d ends with a space' % (i + 1), 'delete the space before the newline', line=i + 1))
        if mode == 'game' and width_mode == 'pixels':
            r = PX.check_line(l, max_cells, PX.get_table(px_profile), mode, item.get('wclass'))
            if not r['ok']:
                errs.append(_err('LINE_TOO_WIDE', 'line %d is %d px wide, its last glyph starts at %d px (max start %d px = %d px window, window %s, %s font): %r' % (
                    i + 1, r['px'], r['start'], PX.start_limit_px(max_cells), r['limit'], item.get('wclass') or 'default', px_profile, l),
                    'insert a newline at a word boundary or shorten (advances: narrow i l . , : ; I 5 px, most lower case 12-13, capitals 11-13, space 12; '
                    'names and numbers are charged 13 / 12 px per cell: #tkNN#/#sname# 10 cells, %s 8, %d 3, %D 6, %m 15, $N 6)',
                    line=i + 1, width=r['px'], start=r['start'], max_cells=max_cells, max_px=r['limit'], over_px=r['over']))
        elif mode == 'game':
            w = T.cells_of_line(l, mode)
            if w > max_cells:
                errs.append(_err('LINE_TOO_WIDE', 'line %d is %d cells wide (max %d, window %s): %r' % (i + 1, w, max_cells, item.get('wclass') or 'default', l),
                                 'insert a newline at a word boundary or shorten (token widths: #tkNN#/#sname# 10, %s 8, %d 3, %D 6, %m 15, $N 6)',
                                 line=i + 1, width=w, max_cells=max_cells))
            elif w == max_cells and l.rstrip()[-1:] in PUNCT_END:
                errs.append(_err('PUNCT_AT_EDGE', 'line %d fills all %d cells and ends in %r' % (i + 1, w, l.rstrip()[-1]),
                                 'leave one cell free after . , ! ? (move the last word down or shorten)', line=i + 1, width=w))

    # --- byte budget ----------------------------------------------------------------------------
    nbytes = len(en.encode('cp932', errors='replace')) + 1          # + NUL
    bf = item.get('budget_fixed')
    if bf is not None and nbytes > bf:
        errs.append(_err('OVER_BUDGET', 'needs %d bytes with NUL, fixed slot is %d (%d characters max, %d too many)' % (
            nbytes, bf, bf - 1, nbytes - bf), 'shorten by %d characters (space ladder: short form, drop filler, shortest noun; names: "G. Family")' % (nbytes - bf),
            need=nbytes, budget=bf, over=nbytes - bf))
    if bf is None and kind != 'ini':
        jp_total = T.jp_bytes(ja) + 1
        if nbytes > T.SOFT_RATIO * jp_total:
            bm = item.get('budget_min')
            warns.append(_err('WARN_LONG', '%d bytes vs %d Japanese bytes (x%.2f, soft limit x%.2f)%s' % (
                nbytes, jp_total, nbytes / jp_total, T.SOFT_RATIO,
                '' if bm is None else '; smallest slot %d' % bm),
                'prose should aim at about 0.85 x natural English (<= %d bytes)' % int(T.SOFT_RATIO * jp_total),
                need=nbytes, jp=jp_total, soft=int(T.SOFT_RATIO * jp_total)))

    # --- style warnings --------------------------------------------------------------------------
    if HONORIFIC_RE.search(en):
        warns.append(_err('HONORIFIC', 'honorific %r' % HONORIFIC_RE.search(en).group(0), 'drop -san/-kun/-sama; use the name only'))
    if STACKED_RE.search(en):
        warns.append(_err('STACKED_PUNCT', 'stacked ! or ?', 'one "!" or "!?" is enough'))
    if ELLIPSIS_RE.search(en):
        warns.append(_err('ELLIPSIS', 'more than three dots', 'use exactly "..."'))
    if re.search(r'(?<=\S)  +(?=\S)', en):
        warns.append(_err('DOUBLE_SPACE', 'double space inside a line'))
    if US_RE.search(en):
        warns.append(_err('US_SPELLING', 'US spelling %r' % US_RE.search(en).group(0), 'British spelling: colour, centre, defence, organise, grey'))
    return errs, warns


# ------------------------------------------------------------------ result files ----

class MalformedInput(ValueError):
    """The file is not a usable result / shard file (as opposed to a well-formed result with validation errors)."""


def _jtype(x):
    return {type(None): 'null', bool: 'boolean', int: 'number', float: 'number', str: 'string', list: 'array',
            dict: 'object'}.get(type(x), type(x).__name__)


def _safe(s):
    """A str that can always be printed / written as utf-8: lone surrogates (JSON "\\ud800") become \\ud800 text."""
    if isinstance(s, str):
        return s.encode('utf-8', 'backslashreplace').decode('utf-8')
    return s


def load_json(path):
    """Read a JSON file; a UTF-8 BOM is accepted.  Raises OSError, or ValueError (JSONDecodeError, UnicodeDecodeError)."""
    with open(path, encoding='utf-8-sig') as fh:
        try:
            return json.load(fh)
        except RecursionError:                       # absurdly nested file: malformed input, not a crash
            raise ValueError('JSON nested too deeply')


def shard_path(shards_dir, n):
    return os.path.join(shards_dir, '%04d.json' % int(n))


def load_shard(path):
    sh = load_json(path)
    if not isinstance(sh, dict) or not isinstance(sh.get('items'), list) or not all(
            isinstance(it, dict) and isinstance(it.get('key'), str) and isinstance(it.get('ja'), str) for it in sh['items']):
        raise MalformedInput('%s: not a shard file (an object with an "items" list of {key, ja, ...})' % path)
    return sh


def validate_shape(result):
    """Raise MalformedInput unless result is {"shard": N, "results": [...] or {...}}."""
    if not isinstance(result, dict):
        raise MalformedInput('top level is a JSON %s, expected an object {"shard": N, "results": [{"key", "en"}, ...]}' % _jtype(result))
    if 'results' not in result:
        raise MalformedInput('no "results" member')
    res = result['results']
    if not isinstance(res, (list, dict)):
        raise MalformedInput('"results" is a JSON %s, expected a list of {"key", "en"} objects or a {key: en} map' % _jtype(res))


def result_entries(result):
    """Normalise results to a list of (key, en, raw) accepting a list of objects or a {key: en} map.
    An entry that is not an object with a string "key" gets key None (reported as BAD_ENTRY).
    Raises MalformedInput when the result is not shaped like a result file at all."""
    validate_shape(result)
    res = result['results']
    if isinstance(res, dict):
        return [(k, v, {'key': k, 'en': v}) for k, v in res.items()]
    out = []
    for e in res:
        if isinstance(e, dict) and isinstance(e.get('key'), str):
            out.append((e['key'], e.get('en'), e))
        else:
            out.append((None, None, e))
    return out


def check_result(shard, result, extra_lines=0, allow_missing=False, width_mode='cells', px_profile=PX.DEFAULT_PROFILE):
    """Check a whole result against its shard.  Returns a report dict (JSON-serialisable):
    ok, counts, per-key outcome 'keys' {key: {'ok', 'errors', 'warnings'}} and flat lists."""
    items = {it['key']: it for it in shard['items']}
    rep = {'shard': shard.get('shard'), 'n_items': len(items), 'n_results': 0, 'n_ok': 0, 'n_error_items': 0,
           'n_warnings': 0, 'keys': {}, 'errors': [], 'warnings': [], 'missing': [], 'unknown': [], 'duplicates': []}
    seen = set()
    for key, en, raw in result_entries(result):
        rep['n_results'] += 1
        if key is None:
            shown = _safe(repr(raw))
            rep['errors'].append({'key': None, 'code': 'BAD_ENTRY', 'hint': 'every entry must be {"key": "<12 hex>", "en": "..."}',
                                  'msg': 'result entry %s is not an object with a string "key"' % (shown if len(shown) <= 100 else shown[:97] + '...')})
            continue
        if key not in items:
            key = _safe(key)
            rep['unknown'].append(key)
            rep['errors'].append({'key': key, 'code': 'UNKNOWN_KEY', 'msg': 'key not in shard %s' % shard.get('shard'),
                                  'hint': 'copy the key from the item exactly'})
            continue
        if key in seen:
            rep['duplicates'].append(key)
            rep['errors'].append({'key': key, 'code': 'DUPLICATE_KEY', 'msg': 'key appears more than once',
                                  'hint': 'return each key once'})
            continue
        seen.add(key)
        item = items[key]
        errs, warns = check_text(item, en, extra_lines, width_mode, px_profile)
        for e in errs:
            e = dict(e, key=key, ja=item['ja'], en=_safe(en))
            rep['errors'].append(e)
        for w in warns:
            rep['warnings'].append(dict(w, key=key, ja=item['ja'], en=_safe(en)))
        rep['keys'][key] = {'ok': not errs, 'errors': [e['code'] for e in errs], 'warnings': [w['code'] for w in warns]}
        rep['n_warnings'] += len(warns)
        if not errs:
            rep['n_ok'] += 1
    for key, it in items.items():
        if key not in seen and not it.get('skip'):
            rep['missing'].append(key)
            if not allow_missing:
                rep['errors'].append({'key': key, 'code': 'MISSING', 'ja': it['ja'], 'msg': 'no translation returned',
                                      'hint': 'every item without a skip hint needs an entry'})
    rep['n_error_items'] = len({e['key'] for e in rep['errors']})
    rep['ok'] = not rep['errors']
    return rep


def format_report(rep, show_warnings=True):
    out = []
    out.append('shard %s: %d items, %d results, %d ok, %d items with errors, %d warnings, %d missing' % (
        rep['shard'], rep['n_items'], rep['n_results'], rep['n_ok'], rep['n_error_items'], rep['n_warnings'], len(rep['missing'])))
    for e in rep['errors']:
        out.append('ERROR %s %s: %s' % (e.get('key'), e['code'], e['msg']))
        if e.get('ja') is not None:
            out.append('      ja: %s' % e['ja'].replace('\n', '\\n'))
        if e.get('en') is not None and e['code'] not in ('MISSING', 'UNKNOWN_KEY'):
            out.append('      en: %s' % str(e['en']).replace('\n', '\\n'))
        if e.get('hint'):
            out.append('      fix: %s' % e['hint'])
    if show_warnings:
        for w in rep['warnings']:
            out.append('warn  %s %s: %s' % (w.get('key'), w['code'], w['msg']))
    out.append('RESULT: %s' % ('OK' if rep['ok'] else 'FAILED'))
    return '\n'.join(out)


def repair_file(shard, rep):
    """Structured work order for a repair agent: every failing item with its errors and limits."""
    items = {it['key']: it for it in shard['items']}
    bykey = collections.OrderedDict()
    for e in rep['errors']:
        k = e.get('key')
        if k is None:
            continue
        bykey.setdefault(k, []).append({kk: vv for kk, vv in e.items() if kk not in ('key', 'ja', 'en')})
    out = []
    for k, errs in bykey.items():
        it = items.get(k)
        if it is None:
            continue
        en = None
        for e in rep['errors']:
            if e.get('key') == k and 'en' in e:
                en = e['en']
                break
        out.append({'key': k, 'ja': it['ja'], 'en': en, 'errors': errs, 'item': it})
    return {'shard': shard.get('shard'), 'repair': out}


def find_shard(args_shard_file, shards_dir, result):
    """The shard a result belongs to.  Raises MalformedInput (a ValueError) for a result that is not shaped like a result
    file, a bad "shard" number or a missing / broken shard file; OSError when the shard file cannot be read."""
    validate_shape(result)
    if args_shard_file:
        return load_shard(args_shard_file)
    n = result.get('shard')
    if n is None:
        raise MalformedInput('result file has no "shard" number; pass --shard-file')
    if isinstance(n, bool) or not (isinstance(n, int) or (isinstance(n, str) and n.strip().isdigit())):
        raise MalformedInput('"shard" is %s, expected a shard number' % (_safe(repr(n)) if len(repr(n)) <= 60 else _jtype(n)))
    p = shard_path(shards_dir, int(n))
    if not os.path.exists(p):
        raise MalformedInput('shard file %s not found (run transwork.py plan)' % p)
    return load_shard(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Validate a shard result file.')
    ap.add_argument('result', help='RESULT.json  {"shard": N, "results": [{"key","en"}]}')
    ap.add_argument('--shards', default=T.SHARD_DIR, help='shard directory (default build/trans/shards)')
    ap.add_argument('--shard-file', help='explicit shard file instead of <shards>/NNNN.json')
    ap.add_argument('--json', action='store_true', help='print the structured report as JSON')
    ap.add_argument('--rejects', metavar='PATH', help='write a repair work order (failing items + errors) here')
    ap.add_argument('--extra-lines', type=int, default=0, help='extra lines allowed for movable items (default 0)')
    ap.add_argument('--allow-missing', action='store_true', help='do not fail on items without a result')
    ap.add_argument('--quiet', action='store_true', help='hide warnings in the text report')
    ap.add_argument('--width-mode', choices=['cells', 'pixels'], default='cells',
                    help='line width rule: cells (default, one cell per glyph) or pixels (proportional font advances, docs/pixel-widths.md)')
    ap.add_argument('--px-profile', choices=PX.PROFILES, default=PX.DEFAULT_PROFILE,
                    help='advance table for --width-mode pixels: on = the table of build_patch --proportional-font on (default), ideal, off')
    a = ap.parse_args(argv)
    # every path: current directory first, then the repository root (translib.resolve_path)
    result_path = T.resolve_path(a.result)
    try:
        result = load_json(result_path)
        shard = find_shard(T.resolve_path(a.shard_file) if a.shard_file else None, T.resolve_path(a.shards), result)
        rep = check_result(shard, result, a.extra_lines, a.allow_missing, a.width_mode, a.px_profile)
    except (OSError, ValueError) as ex:                     # unreadable / not JSON / not a result file: not a validation result
        what = 'malformed input' if isinstance(ex, ValueError) else 'cannot read'
        print('transcheck: %s: %s: %s' % (what, a.result, _safe(str(ex))), file=sys.stderr)
        if a.json:
            print(json.dumps({'ok': False, 'malformed': _safe(str(ex)), 'result_file': a.result}, ensure_ascii=False, indent=1))
        return 2
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(format_report(rep, not a.quiet))
    if a.rejects and not rep['ok']:
        rj = T.resolve_path(a.rejects)
        os.makedirs(os.path.dirname(rj), exist_ok=True)
        T.write_atomic(rj, json.dumps(repair_file(shard, rep), ensure_ascii=False, indent=1) + '\n')
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
