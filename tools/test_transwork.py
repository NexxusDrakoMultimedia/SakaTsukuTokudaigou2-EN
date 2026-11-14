"""Self-test for tools/transwork.py, transcheck.py, transmerge.py, translib.py and textdb.preserve_en.

    python -I -X utf8 tools/test_transwork.py [--quick]      (about 30 s; --quick skips the real-database part)

Synthetic fixtures live in a temporary directory; the real translation/ directory is only READ (the
real-database part copies what it needs to a temporary directory).  Nothing in the repository is written
(every merge gets a temporary --lock-file, backup and rejects directory).

Regression blocks for the review's defect list: skip hints (classify, tools/trans_skip_ids.txt), malformed result
files, whitespace-only en, BAD_ENTRY counting, the merge lock (incl. real concurrent processes), atomic
textdb.write_jsonl + numbered orphan side files, textfmt_common extra keys, path resolution.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translib as T      # noqa: E402
import transwork as W     # noqa: E402
import transcheck as C    # noqa: E402
import transmerge as M    # noqa: E402
import winwidth as WW     # noqa: E402
import textdb             # noqa: E402
import textfmt_common as TC   # noqa: E402

QUICK = '--quick' in sys.argv
fails = []
n_checks = 0


def check(cond, msg):
    global n_checks
    n_checks += 1
    if not cond:
        fails.append(msg)
        print('FAIL:', msg)


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rv = fn(*a, **k)
    return rv, buf.getvalue()


def rec(rid, ja, mb, refs=1, ctx='ptr@1', orphan=False, en=''):
    r = {'id': rid, 'ja': ja, 'en': en, 'max_bytes': mb, 'refs': None if orphan else refs, 'ctx': ctx}
    if orphan:
        r['orphan'] = True
    return r


def write_db(tdb, spec):
    """spec: {name: (style, [records])}; style 'compact' or 'spaced'."""
    os.makedirs(tdb, exist_ok=True)
    for name, (style, recs) in spec.items():
        with open(os.path.join(tdb, name + '.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' if style == 'compact'
                        else json.dumps(r, ensure_ascii=False) + '\n')


JA_SEVEN = '@Y/７段@のクラブです\n頑張りましょう'
JA_NAME = '河本 鬼茂'
JA_NAME2 = '平塚 浪馬'
JA_PF = '%s選手は%d点です。'
JA_INI = 'オプション<br>設定'
JA_DEBUG = 'ダミーテキスト%d'


def fixture_db():
    return {
        'FLOW_PRG__MEETING.BIN': ('compact', [
            rec('FLOW_PRG/MEETING.BIN#100', JA_SEVEN, 60, ctx='tbl@23668[0/3]'),
            rec('FLOW_PRG/MEETING.BIN#140', JA_PF, 24, ctx='tbl@23668[1/3]'),
            rec('FLOW_PRG/MEETING.BIN#160', '決定', 8, ctx='tbl@23668[2/3]'),
            rec('FLOW_PRG/MEETING.BIN#170', JA_NAME, 14, ctx='orphan (no pointer) stride-table(in-place only)', orphan=True),
            rec('FLOW_PRG/MEETING.BIN#180', JA_DEBUG, 20),
        ]),
        'FLOW_PRG__OPTION.BIN': ('spaced', [
            rec('FLOW_PRG/OPTION.BIN#10', '決定', 4),
            rec('FLOW_PRG/OPTION.BIN#20', JA_NAME, 12, ctx='ptr@2 stride-table(in-place only)'),
            rec('FLOW_PRG/OPTION.BIN#30', JA_SEVEN, 50),
        ]),
        'ETC_DATA__BPINFO.BIN': ('spaced', [
            rec('ETC_DATA/BPINFO.BIN#40', JA_NAME2, 14, refs=None, ctx='player #1 name'),
        ]),
        'DPETC__MESSAGE.INI': ('spaced', [
            rec('DPETC/MESSAGE.INI#22', JA_INI, None, refs=None, ctx='key 0'),
        ]),
    }


def read_all(tdb):
    out = {}
    for fn in sorted(os.listdir(tdb)):
        if fn.endswith('.jsonl'):
            with open(os.path.join(tdb, fn), 'rb') as f:
                out[fn] = f.read()
    return out


def items_by_ja(shard_dir):
    out = {}
    for fn in sorted(os.listdir(shard_dir)):
        if fn.endswith('.json'):
            sh = C.load_json(os.path.join(shard_dir, fn))
            for it in sh['items']:
                out[it['ja']] = (sh, it)
    return out


# ---------------------------------------------------------------- plan ----

def test_plan(tmp):
    tdb = os.path.join(tmp, 'tdb')
    out1 = os.path.join(tmp, 'plan1')
    out2 = os.path.join(tmp, 'plan2')
    write_db(tdb, fixture_db())
    rv, _ = quiet(W.main, ['plan', '--tdb', tdb, '--out', out1, '--quiet'])
    check(rv == 0, 'plan exit code')
    quiet(W.main, ['plan', '--tdb', tdb, '--out', out2, '--quiet'])
    s1, s2 = read_all_json(os.path.join(out1, 'shards')), read_all_json(os.path.join(out2, 'shards'))
    check(s1 == s2 and len(s1) > 0, 'plan is deterministic (byte-identical shard files)')
    check(read_bytes(os.path.join(out1, 'index.json')) == read_bytes(os.path.join(out2, 'index.json')), 'index.json stable')
    # the plan must not depend on `en`: translate one record, re-plan, compare
    db = fixture_db()
    db['FLOW_PRG__MEETING.BIN'][1][2]['en'] = 'OK'
    tdb3 = os.path.join(tmp, 'tdb3')
    write_db(tdb3, db)
    out3 = os.path.join(tmp, 'plan3')
    quiet(W.main, ['plan', '--tdb', tdb3, '--out', out3, '--quiet'])
    check(read_all_json(os.path.join(out3, 'shards')) == s1, 'plan ignores en (stable while translating)')

    by = items_by_ja(os.path.join(out1, 'shards'))
    sh, it = by['決定']
    check(it['ids_count'] == 2 and it['budget_min'] == 4 and it['budget_fixed'] is None, 'label: ids_count 2, budget_min = smallest max_bytes')
    check(sh['category'] == 'label' and sh['area'] == 'title', 'label canonical in the highest-priority source (OPTION = title)')
    sh, it = by[JA_NAME]
    check(it['budget_fixed'] == 12 and it['budget_min'] == 12 and it['ids_count'] == 2, 'name: budget_fixed = min over the fixed slots (14, 12)')
    check(sh['category'] == 'name', 'name category')
    sh, it = by[JA_SEVEN]
    check(it['tokens'] == ['@Y/', '@'] and it['lines'] == 2 and it['budget_fixed'] is None and it['budget_min'] == 50, 'prose item: tokens, lines, budgets')
    check(it['soft_max_bytes'] == int(1.05 * (T.jp_bytes(JA_SEVEN) + 1)), 'soft_max_bytes = 1.05 x JP bytes')
    sh, it = by[JA_NAME2]
    check(it['budget_fixed'] == 14 and it['kind'] == 'bpinfo' and sh['category'] == 'name' and it['max_chars_fixed'] == 13, 'BPINFO name: fixed 14, 13 chars')
    sh, it = by[JA_INI]
    check(it['kind'] == 'ini' and it['budget_min'] is None and it['budget_fixed'] is None and sh['category'] == 'browser', 'INI: no limit')
    sh, it = by[JA_DEBUG]
    check(it['skip'] and sh['category'] == 'debug' and sh['area'] == 'junk', 'debug text: skip hint, junk area, kept in the plan')
    sh, it = by[JA_PF]
    check(it['tokens'] == ['%s', '%d'], 'printf tokens in order')
    # neighbours come from the canonical source in source order
    sh, it = by[JA_PF]
    check(it['prev'] == JA_SEVEN and it['next'] == '決定', 'prev/next = neighbouring Japanese in source order')
    # shard order: title (OPTION) before meeting before players before browser before junk
    order = [(json.loads(read_bytes(os.path.join(out1, 'shards', fn)))['area']) for fn in sorted(os.listdir(os.path.join(out1, 'shards')))]
    check(order == sorted(order, key=lambda a: W.AREA_IDX[a]), 'shards are in player-priority order: %s' % order)
    check(os.path.exists(os.path.join(out1, 'plan_summary.md')) and os.path.exists(os.path.join(out1, 'skip_report.tsv')), 'summary + skip report written')
    check('debug' in read_text(os.path.join(out1, 'plan_summary.md')), 'summary lists categories')


def read_bytes(p):
    with open(p, 'rb') as f:
        return f.read()


def read_text(p):
    return read_bytes(p).decode('utf-8')


def read_all_json(d):
    return {fn: read_bytes(os.path.join(d, fn)) for fn in sorted(os.listdir(d)) if fn.endswith('.json')}


# --------------------------------------------------------------- check ----

def mk(ja, lines=None, bf=None, bm=None, skip=None, kind='overlay'):
    return {'key': T.key_of(ja), 'ja': ja, 'lines': lines or T.line_count(ja), 'budget_fixed': bf, 'budget_min': bm,
            'skip': skip, 'kind': kind}


def codes(item, en, **kw):
    e, w = C.check_text(item, en, **kw)
    return sorted(x['code'] for x in e), sorted(x['code'] for x in w)


def rule(name, item, good, bad, code, **kw):
    eg, _ = codes(item, good, **kw)
    check(code not in eg and not eg, '%s: valid fixture passes (got %s)' % (name, eg))
    eb, _ = codes(item, bad, **kw)
    check(code in eb, '%s: invalid fixture fails with %s (got %s)' % (name, code, eb))


def test_check():
    seven = mk(JA_SEVEN, bm=50)
    label = mk('決定', bm=4)
    rule('EMPTY', label, 'OK', '', 'EMPTY')
    rule('EMPTY(blank)', label, 'OK', '   ', 'EMPTY')
    rule('NON_ASCII', label, 'Cafe', 'Café', 'NON_ASCII')
    rule('NON_ASCII(quote)', label, "It's", 'It’s', 'NON_ASCII')
    rule('NON_ASCII(tab)', label, 'a b', 'a\tb', 'NON_ASCII')
    rule('FORBIDDEN_CHAR(backslash)', label, 'a/b', 'a\\b', 'FORBIDDEN_CHAR')
    rule('FORBIDDEN_CHAR(tilde)', label, 'a-b', 'a~b', 'FORBIDDEN_CHAR')
    rule('STRAY_CHAR(%)', label, '50 percent', 'Win 50% now', 'STRAY_CHAR')
    rule('STRAY_CHAR(#)', label, 'No. 1', 'No #1', 'STRAY_CHAR')
    rule('TOKEN_MISMATCH(missing close)', seven, "@Y/7-dan@ club.\nLet's go!", "@Y/7-dan club.\nLet's go!", 'TOKEN_MISMATCH')
    rule('TOKEN_MISMATCH(extra)', seven, "@Y/7-dan@ club.\nLet's go!", "@Y/7-dan@ club @.\nLet's go!", 'TOKEN_MISMATCH')
    rule('TOKEN_MISMATCH(typed =)', label, 'OK', 'a=b', 'TOKEN_MISMATCH')
    rule('TOKEN_MISMATCH(typed @)', label, 'at home', 'a@home', 'TOKEN_MISMATCH')
    rule('TOKEN_MISMATCH(#tk)', mk('#tk01#が勝利'), '#tk01# wins', '#tk02# wins', 'TOKEN_MISMATCH')
    pf = mk(JA_PF)
    rule('TOKEN_ORDER(printf)', pf, '%s scored %d.', '%d points for %s.', 'TOKEN_ORDER')
    two = mk('@Y/甲@と@R/乙@')
    rule('TOKEN_ORDER(spans)', two, '@Y/A@ and @R/B@', '@Y/A and @R/B@@', 'TOKEN_ORDER')
    rule('TOKEN_ORDER(spans2)', two, '@Y/A@ and @R/B@', '@R/B@ and @Y/A@', 'XX') if False else None
    sn = mk('#sname#さんへ')
    rule('LINE_TOO_WIDE', sn, '#sname# ' + 'x' * 28, '#sname# ' + 'x' * 31, 'LINE_TOO_WIDE')
    rule('LINE_TOO_WIDE(plain)', label, 'x' * 39, 'x' * 40, 'LINE_TOO_WIDE')
    check(T.cells_of_line('%s %d %D %m $1', 'game') == 8 + 1 + 3 + 1 + 6 + 1 + 15 + 1 + 6, 'token expansion widths')
    check(T.cells_of_line('@Y/ab@', 'game') == 2, 'colour tokens have no width')
    rule('PUNCT_AT_EDGE', label, 'x' * 37 + '.', 'x' * 38 + '.', 'PUNCT_AT_EDGE')
    two_lines = mk('一行目\n二行目')
    rule('TOO_MANY_LINES', two_lines, 'one\ntwo', 'one\ntwo\nthree', 'TOO_MANY_LINES')
    rule('TOO_MANY_LINES(extra ok for movable)', two_lines, 'one\ntwo\nthree', 'one\ntwo\nthree\nfour', 'TOO_MANY_LINES', extra_lines=1)
    fixed2 = mk('一行目\n二行目', bf=40)
    rule('TOO_MANY_LINES(fixed never)', fixed2, 'one\ntwo', 'one\ntwo\nthree', 'TOO_MANY_LINES', extra_lines=1)
    fx = mk('河本 鬼茂', bf=12)
    rule('OVER_BUDGET', fx, 'O. Kawamoto', 'Oni Kawamoto', 'OVER_BUDGET')
    rule('OVER_BUDGET(edge)', fx, 'x' * 11, 'x' * 12, 'OVER_BUDGET')
    rule('LEADING_SPACE', two_lines, 'one\ntwo', ' one\ntwo', 'LEADING_SPACE')
    rule('TRAILING_SPACE', two_lines, 'one\ntwo', 'one \ntwo', 'TRAILING_SPACE')
    rule('EMPTY_LINE', two_lines, 'one\ntwo', 'one\n', 'EMPTY_LINE')
    indent = mk('　キャッチング')
    check(codes(indent, '  Catching')[0] == [], 'leading indent allowed when the Japanese has one')
    ini = mk(JA_INI, kind='ini')
    rule('NEWLINE_IN_INI', ini, 'Options<br>Settings', 'Options\nSettings', 'NEWLINE_IN_INI')
    check(codes(ini, 'Options<br>' + 'x' * 60)[0] == [], 'browser text has no 39-cell limit')
    check('TOKEN_MISMATCH' in codes(ini, 'Options Settings')[0], 'INI: html tag <br> is a control token')
    check(codes(mk('ch@b talk', kind='ini'), 'ch@b talk')[0] == [], 'INI: @ outside tokens is fine in browser text')
    # warnings
    e, w = codes(seven, "@Y/7-dan@ club we all love dearly,\nso let's get on with it now!")
    check('WARN_LONG' in w and not e, 'WARN_LONG is a warning, not an error: %s %s' % (e, w))
    check('WARN_LONG' not in codes(fx, 'x' * 11)[1], 'no soft warning for fixed slots')
    check('HONORIFIC' in codes(label, 'Kimura-san')[1], 'honorific warning')
    check('STACKED_PUNCT' in codes(label, 'Wow!!')[1], 'stacked punctuation warning')
    check('US_SPELLING' in codes(label, 'Color')[1], 'US spelling warning')
    # skip semantics
    sk = mk(JA_DEBUG, skip='debug')
    check(codes(sk, '') == ([], []), 'skip item may stay empty')
    check(codes(sk, JA_DEBUG) == ([], []), 'skip item may stay identical to the Japanese')
    check(codes(sk, 'Dummy text %d') == ([], []), 'skip item may be translated')
    check('NON_ASCII' in codes(sk, 'Dummy é %d')[0], 'a translated skip item is still validated')
    check('EMPTY' in codes(label, '')[0], 'non-skip item cannot be empty')

    # result-level checks
    shard = {'shard': 7, 'items': [label, seven, sk]}
    rep = C.check_result(shard, {'shard': 7, 'results': [{'key': label['key'], 'en': 'OK'}]})
    check(not rep['ok'] and any(e['code'] == 'MISSING' and e['key'] == seven['key'] for e in rep['errors']), 'MISSING reported for the untranslated non-skip item')
    check(all(e['key'] != sk['key'] for e in rep['errors']), 'skip item is never MISSING')
    rep = C.check_result(shard, {'shard': 7, 'results': [{'key': 'nope', 'en': 'x'}, {'key': label['key'], 'en': 'OK'}, {'key': label['key'], 'en': 'OK'}]}, allow_missing=True)
    codes_ = {e['code'] for e in rep['errors']}
    check({'UNKNOWN_KEY', 'DUPLICATE_KEY'} <= codes_, 'unknown and duplicate keys reported: %s' % codes_)
    rep = C.check_result(shard, {'shard': 7, 'results': {label['key']: 'OK', seven['key']: "@Y/7-dan@ club.\nLet's go!"}})
    check(rep['ok'], 'dict-style results accepted')
    # structured errors carry code, msg, hint
    e, _ = C.check_text(fx, 'Oni Kawamoto')
    check(e and e[0]['code'] == 'OVER_BUDGET' and e[0]['over'] == 1 and e[0]['hint'] and e[0]['budget'] == 12, 'structured error detail')


def test_check_cli(tmp):
    tdb = os.path.join(tmp, 'tdb')
    out = os.path.join(tmp, 'plan1')
    by = items_by_ja(os.path.join(out, 'shards'))
    sh, it = by['決定']
    shard_file = os.path.join(out, 'shards', '%04d.json' % sh['shard'])
    res = {'shard': sh['shard'], 'results': [{'key': x['key'], 'en': 'OK' if x['ja'] == '決定' else 'Hello'} for x in sh['items']]}
    good = os.path.join(tmp, 'good.json')
    with open(good, 'w', encoding='utf-8') as f:
        json.dump(res, f)
    rv, txt = quiet(C.main, [good, '--shards', os.path.join(out, 'shards')])
    check(rv == 0 and 'RESULT: OK' in txt, 'transcheck CLI exit 0 on a valid file')
    res['results'][0]['en'] = 'Café'
    bad = os.path.join(tmp, 'bad.json')
    with open(bad, 'w', encoding='utf-8') as f:
        json.dump(res, f)
    rej = os.path.join(tmp, 'rejects.json')
    rv, txt = quiet(C.main, [bad, '--shards', os.path.join(out, 'shards'), '--rejects', rej])
    check(rv == 1 and 'NON_ASCII' in txt, 'transcheck CLI exit 1 on errors')
    ro = C.load_json(rej)
    check(ro['repair'] and ro['repair'][0]['errors'][0]['code'] == 'NON_ASCII' and ro['repair'][0]['item']['ja'], 'repair work order written')
    rv, _ = quiet(C.main, [os.path.join(tmp, 'nothere.json')])
    check(rv == 2, 'transcheck CLI exit 2 on a missing file')
    rv, js = quiet(C.main, [bad, '--shards', os.path.join(out, 'shards'), '--json'])
    check(json.loads(js)['ok'] is False, '--json prints a structured report')


# --------------------------------------------------------------- merge ----

def make_results(items_en, sh_of):
    """[(ja, en)] -> one result dict per shard (a result file belongs to exactly one shard)."""
    by = {}
    for ja, en in items_en:
        by.setdefault(sh_of[ja], []).append({'key': T.key_of(ja), 'en': en})
    return [{'shard': s, 'results': r} for s, r in sorted(by.items())]


def test_merge(tmp):
    tdb = os.path.join(tmp, 'mtdb')
    plan = os.path.join(tmp, 'mplan')
    write_db(tdb, fixture_db())
    quiet(W.main, ['plan', '--tdb', tdb, '--out', plan, '--quiet'])
    shards = os.path.join(plan, 'shards')
    by = items_by_ja(shards)
    sh_of = {ja: s['shard'] for ja, (s, _) in by.items()}
    backup = os.path.join(tmp, 'backup')
    rejects = os.path.join(tmp, 'rejects')
    orig = read_all(tdb)

    def run(results, *extra):
        paths = []
        for i, r in enumerate(results):
            p = os.path.join(tmp, 'res_%d_%s.json' % (i, r['shard']))
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(r, f)
            paths.append(p)
        return quiet(M.main, ['merge'] + paths + ['--tdb', tdb, '--shards', shards, '--backup-dir', backup,
                                                  '--rejects-dir', rejects, '--lock-file', os.path.join(tmp, 'mt.lock')] + list(extra))

    r_label = make_results([('決定', 'OK')], sh_of)
    r_name = make_results([(JA_NAME, 'O. Kawamoto'), (JA_NAME2, 'Nami Hiratsuka')], sh_of)     # second is 14 chars: refused
    r_prose = make_results([(JA_SEVEN, "@Y/7-dan@ club.\nLet's go!"), (JA_PF, '%s scored %d.')], sh_of)
    r_ini = make_results([(JA_INI, 'Options<br>Settings')], sh_of)
    # 1. label + valid name merge; duplicates all filled
    rv, txt = run(r_label)
    db = T.load_db(tdb)
    ens = {r['id']: r['en'] for _, _, r in db.records()}
    check(rv == 0 and ens['FLOW_PRG/MEETING.BIN#160'] == 'OK' and ens['FLOW_PRG/OPTION.BIN#10'] == 'OK', 'merge fills EVERY record with the same ja')
    check(os.path.isdir(os.path.join(backup, '0001')), 'backup directory 0001 created')
    check(read_bytes(os.path.join(backup, '0001', 'FLOW_PRG__MEETING.BIN.jsonl')) == orig['FLOW_PRG__MEETING.BIN.jsonl'], 'backup holds the previous file content')
    check(not [f for f in os.listdir(tdb) if f.endswith('.tmp')], 'no temp files left behind (atomic replace)')
    # untouched files are byte-identical; changed files differ only in the changed lines
    after = read_all(tdb)
    check(after['ETC_DATA__BPINFO.BIN.jsonl'] == orig['ETC_DATA__BPINFO.BIN.jsonl'] and after['DPETC__MESSAGE.INI.jsonl'] == orig['DPETC__MESSAGE.INI.jsonl'], 'unrelated files untouched')
    ol, nl = orig['FLOW_PRG__OPTION.BIN.jsonl'].decode().split('\n'), after['FLOW_PRG__OPTION.BIN.jsonl'].decode().split('\n')
    check([i for i in range(len(ol)) if ol[i] != nl[i]] == [0], 'only the changed line of OPTION rewritten')
    check(nl[0].startswith('{"id": "FLOW_PRG/OPTION.BIN#10", "ja"') and '"en": "OK"' in nl[0], 'file style (spaced separators) preserved')
    check(after['FLOW_PRG__MEETING.BIN.jsonl'].decode().split('\n')[2].startswith('{"id":"FLOW_PRG/MEETING.BIN#160"'), 'file style (compact separators) preserved')
    # 2. idempotent
    before_bytes = read_all(tdb)
    rv, txt = run(r_label)
    check(rv == 0 and read_all(tdb) == before_bytes, 'second merge of the same result changes nothing')
    check(not os.path.isdir(os.path.join(backup, '0002')), 'idempotent merge creates no backup')
    check('records filled 0' in txt, 'second merge reports 0 filled')
    # 3. name result with one over-budget item: partial merge, refusal reported, repair order written
    rv, txt = run(r_name)
    db = T.load_db(tdb)
    ens = {r['id']: r['en'] for _, _, r in db.records()}
    check(rv == 1 and 'REFUSED' in txt, 'over-budget item refused (exit 1)')
    check(ens['FLOW_PRG/MEETING.BIN#170'] == 'O. Kawamoto' and ens['FLOW_PRG/OPTION.BIN#20'] == 'O. Kawamoto', 'valid sibling item merged to all ids')
    check(ens['ETC_DATA/BPINFO.BIN#40'] == '', 'refused item not written')
    rj = os.path.join(rejects, '%04d.json' % sh_of[JA_NAME2])
    check(os.path.exists(rj) and any(r['ja'] == JA_NAME2 for r in C.load_json(rj)['repair']), 'repair work order for the refused item')
    check(os.path.isdir(os.path.join(backup, '0002')), 'second backup counter after a real change')
    # 4. conflicts: a different string never replaces an existing one without --overwrite
    rv, txt = run(make_results([('決定', 'Confirm')], sh_of))
    db = T.load_db(tdb)
    check(next(r for _, _, r in db.records() if r['id'] == 'FLOW_PRG/OPTION.BIN#10')['en'] == 'OK' and 'CONFLICT' in txt, 'no overwrite without --overwrite')
    rv, txt = run(make_results([('決定', 'Confirm')], sh_of), '--overwrite')
    db = T.load_db(tdb)
    check(next(r for _, _, r in db.records() if r['id'] == 'FLOW_PRG/OPTION.BIN#10')['en'] == 'Confirm', '--overwrite replaces')
    # 5. never lowers coverage: an empty result blanks nothing and is refused
    cov0 = M.count_en(T.load_db(tdb))
    rv, txt = run(make_results([('決定', '')], sh_of), '--overwrite')
    check(M.count_en(T.load_db(tdb)) == cov0 and rv == 1, 'empty en neither blanks a record nor passes the checker')
    # 6. prose, printf, INI, skip handling
    rv, txt = run(r_prose + r_ini)
    check(rv == 0, 'prose + ini merge: %s' % txt)
    db = T.load_db(tdb)
    ens = {r['id']: r['en'] for _, _, r in db.records()}
    check(ens['FLOW_PRG/OPTION.BIN#30'] == "@Y/7-dan@ club.\nLet's go!" and ens['DPETC/MESSAGE.INI#22'] == 'Options<br>Settings', 'multi-line prose and html text merged')
    check(ens['FLOW_PRG/MEETING.BIN#180'] == '', 'skip-hinted debug item left empty')
    rv, txt = run(make_results([(JA_DEBUG, JA_DEBUG)], sh_of))
    db = T.load_db(tdb)
    rr = next(r for _, _, r in db.records() if r['id'] == 'FLOW_PRG/MEETING.BIN#180')
    check(rr['en'] == JA_DEBUG and rr.get('skip') is True, 'skip item kept identical gets "skip": true')
    # 7. all-or-nothing and dry-run
    snap = read_all(tdb)
    bad = make_results([(JA_NAME2, 'Nami Hiratsuka')], sh_of)[0]
    rv, txt = run([bad], '--all-or-nothing')
    check(rv == 1 and read_all(tdb) == snap, '--all-or-nothing refuses and writes nothing')
    good = make_results([(JA_NAME2, 'N. Hiratsuka')], sh_of)[0]
    rv, txt = run([good], '--dry-run')
    check(read_all(tdb) == snap and 'DRY RUN' in txt, '--dry-run writes nothing')
    # 8. stale shard: the database now has a tighter fixed slot than the shard says
    db_t = fixture_db()
    db_t['ETC_DATA__BPINFO.BIN'][1][0]['max_bytes'] = 8
    tdb2 = os.path.join(tmp, 'mtdb2')
    write_db(tdb2, db_t)
    res_p = os.path.join(tmp, 'stale.json')
    with open(res_p, 'w', encoding='utf-8') as f:
        json.dump(good, f)
    rv, txt = quiet(M.main, ['merge', res_p, '--tdb', tdb2, '--shards', shards, '--backup-dir', os.path.join(tmp, 'b2'), '--rejects-dir', os.path.join(tmp, 'r2'),
                           '--lock-file', os.path.join(tmp, 'mt.lock')])
    check(rv == 1 and 'OVER_BUDGET' in txt, 'budget is re-derived from the current database (stale shard refused)')
    # 9. status
    rv, txt = quiet(M.main, ['status', '--tdb', tdb, '--shards', shards])
    check(rv == 0 and 'records with en:' in txt and 'shards:' in txt, 'status prints coverage')
    rv, js = quiet(M.main, ['status', '--tdb', tdb, '--shards', shards, '--json'])
    cov = json.loads(js)
    db = T.load_db(tdb)
    check(cov['records_en'] == M.count_en(db) and cov['records'] == 10, 'status counts: %s/%s' % (cov['records_en'], cov['records']))
    check(cov['categories']['name']['done'] >= 1, 'status per category')
    rv, pend = quiet(M.main, ['status', '--tdb', tdb, '--shards', shards, '--pending'])
    pending = [int(x) for x in pend.split()]
    check(all(p in set(sh_of.values()) for p in pending), 'pending shard list')
    # status must not count skip-hinted items as work
    check(sh_of[JA_DEBUG] not in pending, 'skip-only shard is never pending')
    # unchanged coverage numbers never decrease between runs
    check(M.count_en(T.load_db(tdb)) >= cov0, 'coverage only grows')


# -------------------------------------------------------- extract guard ----

def test_preserve_en(tmp):
    p = os.path.join(tmp, 'x.jsonl')
    old = [rec('S#1', 'あ', 4, en='A'), rec('S#2', 'い', 4), rec('S#3', 'う', 4, en='U'), rec('S#4', 'え', 4, en='E')]
    old[0]['skip'] = True
    textdb.write_jsonl(p, old)
    new = [rec('S#1', 'あ', 4), rec('S#2', 'い', 4), rec('S#3', 'う2', 4), rec('S#5', 'お', 4)]
    out, orphans = textdb.preserve_en(p, new)
    check(out[0]['en'] == 'A' and out[0].get('skip') is True, 'en and skip carried over by id')
    check(out[1]['en'] == '' and out[3]['en'] == '', 'untranslated stay empty')
    check(out[2]['en'] == '', 'ja changed -> en not carried over')
    check(sorted(o['id'] for o in orphans) == ['S#3', 'S#4'], 'orphans reported: changed ja and vanished id')
    out2, orphans2 = textdb.preserve_en(os.path.join(tmp, 'nofile.jsonl'), new)
    check(orphans2 == [] and out2 is new, 'no existing file -> nothing to preserve')

    src = os.path.join(textdb.EXTRACTED, 'FLOW_PRG', 'CHALDANI.BIN')
    if not os.path.exists(src):
        print('  (extracted/ not present: end-to-end extract guard skipped)')
        return
    out_dir = os.path.join(tmp, 'ex')
    orph = os.path.join(tmp, 'orph')
    argv = ['extract', '--out', out_dir, '--only', 'FLOW_PRG/CHALDANI.BIN', '--orphan-dir', orph]
    rv, txt = quiet(textdb.main, argv)
    f = os.path.join(out_dir, 'FLOW_PRG__CHALDANI.BIN.jsonl')
    recs = textdb.read_jsonl(f)
    check(len(recs) > 50 and all(r['en'] == '' for r in recs), 'first extract: fresh records, en empty')
    recs[3]['en'] = 'Translated 3'
    recs[10]['en'] = 'Translated 10'
    recs.append(rec('FLOW_PRG/CHALDANI.BIN#fffff', 'ゴースト', 8, en='Ghost'))
    textdb.write_jsonl(f, recs)
    rv, txt = quiet(textdb.main, argv)
    again = textdb.read_jsonl(f)
    check(again[3]['en'] == 'Translated 3' and again[10]['en'] == 'Translated 10', 'EXTRACT RE-RUN PRESERVES en (was: erased)')
    check(len(again) == len(recs) - 1 and 'ORPHANED' in txt and '2 translations preserved' in txt, 'orphaned id reported: %s' % txt.strip().splitlines()[-2:])
    ofile = os.path.join(orph, 'FLOW_PRG__CHALDANI.BIN.jsonl')
    check(os.path.exists(ofile) and textdb.read_jsonl(ofile)[0]['en'] == 'Ghost', 'orphaned translation saved to the side file')
    first = read_bytes(f)
    quiet(textdb.main, argv)
    check(read_bytes(f) == first, 'extract is idempotent')
    # a second orphan set must not overwrite the first one
    recs3 = textdb.read_jsonl(f)
    recs3[5]['en'] = 'Translated 5'
    recs3.append(rec('FLOW_PRG/CHALDANI.BIN#ffffe', 'ghost2-' + 'x', 8, en='Ghost2'))
    textdb.write_jsonl(f, recs3)
    rv, txt = quiet(textdb.main, argv)
    o2 = os.path.join(orph, 'FLOW_PRG__CHALDANI.BIN.2.jsonl')
    check(textdb.read_jsonl(ofile)[0]['en'] == 'Ghost' and os.path.exists(o2) and textdb.read_jsonl(o2)[0]['en'] == 'Ghost2',
          'second orphan set goes to a numbered side file, the first is kept: %s' % sorted(os.listdir(orph)))
    check(textdb.read_jsonl(f)[5]['en'] == 'Translated 5', 'translations still preserved on the third extract')


# ------------------------------------------------- skeptic-defect regressions ----
# Each block below pins one defect found in review (numbers = the review's defect list).

def run_cli(fn, argv):
    """-> (exit code, output) of a CLI main(); a crash becomes ('EXC', text) so that it fails a check instead of aborting."""
    try:
        return quiet(fn, argv)
    except Exception as ex:       # noqa: BLE001
        return 'EXC', '%s: %s' % (type(ex).__name__, ex)


def put(tmp, name, data):
    """Write a result file: bytes as they are, anything else as JSON (lone surrogates become \\udXXX escapes)."""
    p = os.path.join(tmp, name)
    if isinstance(data, bytes):
        with open(p, 'wb') as f:
            f.write(data)
    else:
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    return p


def mkenv(tmp, name, spec=None):
    env = {'tdb': os.path.join(tmp, name + '_tdb'), 'plan': os.path.join(tmp, name + '_plan'),
           'backup': os.path.join(tmp, name + '_backup'), 'rejects': os.path.join(tmp, name + '_rejects'),
           'lock': os.path.join(tmp, name + '_merge.lock')}
    write_db(env['tdb'], spec or fixture_db())
    quiet(W.main, ['plan', '--tdb', env['tdb'], '--out', env['plan'], '--quiet'])
    env['shards'] = os.path.join(env['plan'], 'shards')
    env['sh_of'] = {ja: s['shard'] for ja, (s, _) in items_by_ja(env['shards']).items()}
    return env


def mrun(env, paths, *extra):
    return run_cli(M.main, ['merge'] + list(paths) + ['--tdb', env['tdb'], '--shards', env['shards'], '--backup-dir', env['backup'],
                                                      '--rejects-dir', env['rejects'], '--lock-file', env['lock']] + list(extra))


def ens_of(tdb):
    return {r['id']: r['en'] for _, _, r in T.load_db(tdb).records()}


# (1) skip hints ---------------------------------------------------------------------------------------------

EVENT, ENDOPT, GAME = 'FLOW_PRG/EVENT.BIN', 'FLOW_PRG/ENDOPT.BIN', 'FLOW_PRG/GAME.BIN'
JA_GMSHOW02 = ('    @K/「サカつく」@は@M/ネットワーク@に\n    対応しています。\n    Dreamcast付属のモデムを利用し、\n    @M/ネットワーク@で、あなたのクラブが\n'
               '    友達のDreamcastに届きます。\n\n    SEGAのサーバを使用した@Y/公式大会@や、\n    @M/ネットワーク@を使った楽しい遊びも\n'
               '    たくさん予定していますのでご期待\n    下さい！')
VISIBLE = [      # player-visible text that the old over-broad rules skip-hinted
    ('=w/テスト販売で好調な売れ行きとのことで\n正式に発売された様です。\nショップの売れ行きが伸びていますね。=', EVENT),
    ('実際にテスト販売を行った所、\n好調な売れ行きにより、正式発売しました。\nショップの売れ行きが伸びているそうです。', EVENT),
    ('@y/帝国ネットプロバイダー@さんの御好意で私たちのクラブの公式HPが開設されました。http://sakatoku.dricas.ne.jp/です。', EVENT),
    ('現在のクラブ状態をファイルにします。\nこのファイルは@Y/『BESTPLAYERS MATCH』@、\n@Y/『CHALLENGE MODE』@等で使用できます。', ENDOPT),
    ('私たちのクラブから殿堂入りした選手たちで\nクラブをつくり、それをファイルにします。\n@Y/『BESTPLAYERS MATCH』@で使用できます。', ENDOPT),
    (JA_GMSHOW02, 'FLOW_PRG/GMSHOW02.BIN'),
    ('ここの場所で、左右に移動すれば\n@B/「REPEAT」@@O/「END」@をつかむ事ができるよ。', 'FLOW_PRG/SS_EDIT.BIN'),
    ('Ｊリーグ DIVISION 1', 'FLOW_PRG/GETREP.BIN'),
    ('HOME %d位', GAME),
    ('%s　%s', 'FLOW_PRG/HOMETOWN.BIN'),                       # only control tokens + a full-width space: a layout string
    ('スーパーサブフラグ', 'FLOW_PRG/PL_EDIT.BIN'),              # "flag" without a printf value is not a flag dump
    ('          長所追加 MAX31：%d ', 'FLOW_PRG/PL_EDIT.BIN'),   # upper-case word + fullwidth colon + %d is not a variable name
    ('年棒:%d00万  up:%d万', 'FLOW_PRG/MEETING.BIN'),
    ('決勝戦', 'FLOW_PRG/WEEKLY.BIN'),
    ('増築：%d', 'FLOW_PRG/DRSISEKI.BIN'),
    ('国籍:%s', 'FLOW_PRG/DRSDENDO.BIN'),
    ('テストですだ', GAME),
]
HINTED = [       # clearly non-player data keeps its hint
    ('ダミー６', 'FLOW_PRG/COMM.BIN'),
    ('トレード禁止フラグ %d(%d)', ENDOPT),
    ('サポーター要望', 'FLOW_PRG/PWK_EDIT.BIN'),
    ('qualifiedteam[3]（予選通過クラブ）', 'FLOW_PRG/PWK_EDIT.BIN'),
    ('TEAM:%d は勝利しました', 'FLOW_PRG/NEWS_OP.BIN'),
    ('bcFunc:不正な選手番号  %d', GAME),
    ('不正なタイミングでコールされました。 (sysGameDefencePl)', GAME),
    ('PWK_RESULT 連勝記録 TEAM = %d, NUM = %d', 'FLOW_PRG/NEWS.BIN'),
    ('作戦変更  tm:%d', GAME),
    ('8b曙鐶曙', 'FLOW_PRG/NEWS_OP.BIN'),
    ('　', 'FLOW_PRG/OPTION.BIN'),
    ('OK', 'FLOW_PRG/OPTION.BIN'),
]


def test_classify(tmp):
    for ja, src in VISIBLE:
        cat, skip = W.classify(ja, src, 'ptr@1', 'overlay', False, False)
        check(skip is None, 'player-visible text is not skip-hinted: %r (%s)' % (ja[:24], skip))
    for ja, src in HINTED:
        cat, skip = W.classify(ja, src, 'ptr@1', 'overlay', False, False)
        check(skip, 'developer / junk text keeps its skip hint: %r' % ja[:24])
    cat, skip = W.classify('   ', 'DPETC/MESSAGE.INI', '', 'ini', False, False)
    check(skip and cat == 'browser', 'blank INI text is skip-hinted')
    # data-driven list of extraction false positives
    cat, skip = W.classify('緒喧', 'FLOW_PRG/NEWS_OP.BIN', 'orphan (no pointer)', 'overlay', True, True)
    check(skip is None, 'without the list the junk text is not recognised (that is why the list exists)')
    cat, skip = W.classify('緒喧', 'FLOW_PRG/NEWS_OP.BIN', 'orphan (no pointer)', 'overlay', True, True, denied=True)
    check(skip and 'trans_skip_ids' in skip and cat == 'binary', 'denied text gets a skip hint')

    tdb = os.path.join(tmp, 'sk_tdb')
    write_db(tdb, {'FLOW_PRG__NEWS_OP.BIN': ('compact', [
        rec('FLOW_PRG/NEWS_OP.BIN#28f21', '緒喧', 7, orphan=True, ctx='orphan (no pointer)'),
        rec('FLOW_PRG/NEWS_OP.BIN#28f40', '縁限', 9),
        rec('FLOW_PRG/NEWS_OP.BIN#28f60', '縁限', 9),
        rec('FLOW_PRG/NEWS_OP.BIN#28f80', '決定', 9)])})
    sk = os.path.join(tmp, 'skip_ids.txt')
    with open(sk, 'wb') as f:             # BOM, comments, a trailing comment, indentation, an id that is not in the database
        f.write(('﻿# known junk\n\nFLOW_PRG/NEWS_OP.BIN#28f21   # junk\n   FLOW_PRG/NEWS_OP.BIN#28f40\n'
                 'FLOW_PRG/GAME.BIN#deadbeef # stale\n').encode('utf-8'))
    check(W.load_skip_ids(sk) == frozenset(['FLOW_PRG/NEWS_OP.BIN#28f21', 'FLOW_PRG/NEWS_OP.BIN#28f40', 'FLOW_PRG/GAME.BIN#deadbeef']),
          'skip-id file: ids contain "#", comments / blank lines / BOM handled')
    out1, out2 = os.path.join(tmp, 'sk_p1'), os.path.join(tmp, 'sk_p2')
    rv, txt = quiet(W.main, ['plan', '--tdb', tdb, '--out', out1, '--skip-ids', sk])
    quiet(W.main, ['plan', '--tdb', tdb, '--out', out2, '--skip-ids', sk, '--quiet'])
    check(rv == 0 and '1 listed ids not in this database' in txt and '1 texts hinted' in txt, 'plan reports the list: %s' % txt.strip().splitlines()[-1:])
    by = items_by_ja(os.path.join(out1, 'shards'))
    check(by['緒喧'][1]['skip'] and 'trans_skip_ids' in by['緒喧'][1]['skip'], 'text whose every record is listed is skip-hinted')
    check(by['縁限'][1]['skip'] is None, 'text with one unlisted record is NOT hidden by the list')
    check(by['決定'][1]['skip'] is None, 'unlisted text unaffected')
    check(read_all_json(os.path.join(out1, 'shards')) == read_all_json(os.path.join(out2, 'shards')), 'plan with a skip list is deterministic')
    check('緒喧' in read_text(os.path.join(out1, 'skip_report.tsv')), 'listed text appears in skip_report.tsv')
    out3 = os.path.join(tmp, 'sk_p3')
    quiet(W.main, ['plan', '--tdb', tdb, '--out', out3, '--skip-ids', 'none', '--quiet'])
    check(items_by_ja(os.path.join(out3, 'shards'))['緒喧'][1]['skip'] is None, '--skip-ids none disables the list')
    default = W.load_skip_ids()
    check(len(default) >= 16 and all(re.match(r'^[A-Za-z0-9_/]+\.BIN#[0-9a-f]+$', i) for i in default),
          'repository list tools/trans_skip_ids.txt parses (%d ids)' % len(default))
    check('FLOW_PRG/NEWS_OP.BIN#28f21' in default and 'FLOW_PRG/NEWS_OP.BIN#28f00' in default, 'list names the NEWS_OP pointer-table junk')


# (2, 3, 4) malformed result files, whitespace-only en, BAD_ENTRY -----------------------------------------------

def test_whitespace_rules():
    sk = mk(JA_DEBUG, skip='debug')
    label = mk('決定', bm=4)
    blank = mk('　', skip='blank')
    for ws in ('   ', '\n', ' \n ', '　'):
        check('EMPTY' in codes(sk, ws)[0], 'whitespace-only en %r is invalid for a skip-hinted item' % ws)
        check('EMPTY' in codes(label, ws)[0] or 'NON_ASCII' in codes(label, ws)[0], 'whitespace-only en %r is invalid for a normal item' % ws)
    check(codes(sk, '') == ([], []), 'empty en still allowed for a skip-hinted item')
    check(codes(sk, JA_DEBUG) == ([], []), 'identical Japanese still allowed for a skip-hinted item')
    check(codes(blank, '　') == ([], []), 'a blank skip-hinted text may be kept identical')
    check('EMPTY' in codes(blank, ' ')[0], 'but another whitespace string is not a translation')
    check(codes(blank, '') == ([], []), 'and empty is fine for it')
    e, _ = C.check_text(sk, '  ')
    check(e and e[0]['hint'] and 'whitespace' in e[0]['msg'], 'whitespace error explains itself')


def test_window_width():
    """per-window line width (docs/window-widths.md): the 17-cell bubble takes 33 half-width cells, the 20x3 window 39"""
    two = '私ではそのような重責を果たすのは\n不可能だよ。'            # 2 lines, widest 34 cells
    three = 'あいうえおかきくけこ\nさしすせそたちつてと\nなにぬねのはひふへほ'
    wide = '一二三四五六七八九十一二三四五六七八九十\n短い'          # a 40-cell line: only the 20-cell window holds it
    lim = WW.limits(two, 'dialogue', 'FLOW_PRG/MEETING.BIN', 'tbl@23668[1/10]')
    check((lim.max_cells, lim.max_rows) == (33, 2) and lim.cls.startswith('BUBBLE'), 'two short lines in an overlay with a bubble: 33 cells, 2 rows')
    lim = WW.limits(three, 'dialogue', 'FLOW_PRG/MEETING.BIN', 'tbl@23668[1/10]')
    check((lim.max_cells, lim.max_rows, lim.cls) == (39, 3, 'MSG20x3'), 'three lines: only the 20x3 window has three rows')
    lim = WW.limits(wide, 'dialogue', 'FLOW_PRG/MEETING.BIN', 'tbl@23668[1/10]')
    check(lim.max_cells == 39 and lim.basis == 'ja-wide', 'a Japanese line wider than 34 cells: not a bubble')
    lim = WW.limits(two, 'dialogue', 'FLOW_PRG/HELP.BIN', 'tbl@10[1/10]')
    check(lim.max_cells == 39 and lim.basis == 'ovl-no-bubble', 'an overlay without a 17x2 factory shows 39 cells')
    lim = WW.limits('決定', 'label', 'FLOW_PRG/MEETING.BIN', '')
    check(lim.cls == 'CELL' and lim.max_cells == 39, 'labels keep the default')
    check(WW.limits('<br>', 'browser', 'DPETC/MESSAGE.INI', '').max_cells is None, 'browser text has no cell rule')
    m = WW.merge_limits([WW.Limit(39, 3, 'MSG20x3', 'x'), WW.Limit(33, 2, 'BUBBLE?', 'y')])
    check((m.max_cells, m.max_rows) == (33, 2), 'a text shared by two windows takes the strictest limit')
    it = mk(two, bm=60)
    it['max_cells'], it['max_rows'] = 33, 2
    e, _ = C.check_text(it, 'I cannot possibly bear such a heavy\nresponsibility.')
    check('LINE_TOO_WIDE' in [x['code'] for x in e], 'transcheck: 34 cells in a 33-cell window is LINE_TOO_WIDE')
    e, _ = C.check_text(it, 'I cannot possibly bear such a\nheavy responsibility.')
    check(not [x for x in e if x['code'] == 'LINE_TOO_WIDE'], 'transcheck: 33 cells fits')
    it2 = mk(two, bm=60)
    check('LINE_TOO_WIDE' not in [x['code'] for x in C.check_text(it2, 'I cannot possibly bear such a heavy\nresponsibility.')[0]],
          'an item without max_cells keeps the 39-cell default')



def test_pixel_width(tmp):
    """pixel mode (docs/pixel-widths.md): advance table of the proportional font, engine wrap rule, worst-case tokens"""
    import pixelwidth as PX
    import fontpatch as FPT
    tab = PX.get_table('on')
    check(len(tab) == 256 and all(tab[b] for b in range(256)), 'px table: 256 entries, a stored 0 means 12')
    check(tab[ord('i')] == 5 and tab[ord('W')] == 13 and tab[ord('0')] == 12 and tab[ord('9')] == 12, 'px table: i 5, W 13, digits 12')
    check(tab[0x20] == FPT.SPACE_ADV == 12, 'px table (build profile): the space keeps 12 px (skeptic D1)')
    check(PX.get_table('ideal')[0x20] == 6 and all(PX.get_table('off')[b] == 12 for b in range(256)), 'px profiles: ideal space 6, off = 12 everywhere')
    meta = PX.get_table('ideal')
    check(all(meta[b] == tab[b] for b in range(0x21, 0x7F)), 'px profiles: build table and measured hybrid-H table agree on all 94 glyphs')
    try:
        PX.get_table('bogus')
        check(False, 'unknown px profile is refused')
    except ValueError:
        check(True, 'unknown px profile is refused')
    # identity: with every advance 12 the pixel rule IS the cell rule (engine: glyph starts at <= 12*(max_cells-1))
    off = PX.get_table('off')
    ident = True
    for n in range(1, 45):
        for mc in (33, 39):
            ident &= PX.fits(PX.advances('x' * n, off), mc) == (n <= mc)
    check(ident, 'profile off: pixel fit == cell fit for 1..44 glyphs in 33 and 39 cell windows')
    check(sum(PX.advances('#tk01#', off)) == 12 * T.cells_of_line('#tk01#') and sum(PX.advances('#tk01#')) == 13 * T.cells_of_line('#tk01#'),
          'name token: 12 px per cell in profile off (identity), 13 in profile on')
    check(PX.advances('%.d') == [] and PX.advances('a%.fb', off) == [12, 12], 'malformed printf field %.d: 0 px, no exception')
    # exact boundary with 13 px glyphs: start of the last glyph <= 384 (bubble) / 456 (message)
    check(PX.fits(PX.advances('e' * 30, tab), 33) and not PX.fits(PX.advances('e' * 31, tab), 33), 'px: 30 x 13 px fit the bubble, 31 do not')
    check(PX.fits(PX.advances('e' * 36, tab), 39) and not PX.fits(PX.advances('e' * 37, tab), 39), 'px: 36 x 13 px fit the message window, 37 do not')
    check(PX.fits(PX.advances('i' * 77, tab), 33) and not PX.fits(PX.advances('i' * 78, tab), 33), 'px: 5 px glyphs (77 per bubble line)')
    check(PX.limit_px(33) == 396 and PX.limit_px(39) == 468 and PX.start_limit_px(33) == 384 and PX.start_limit_px(39) == 456, 'px limits 396 / 468, starts 384 / 456')
    r = PX.check_line('e' * 31, 33, tab)
    check(not r['ok'] and r['px'] == 403 and r['start'] == 390 and r['over'] == 6 and r['rows'] == 2, 'px check_line numbers: %s' % r)
    check(PX.wrap_rows(PX.advances('e' * 62, tab), 33) == 3 and PX.wrap_rows([], 33) == 1, 'px wrap_rows follows the engine break')
    # tokens: worst case, zero-width colour / window tokens
    check(sum(PX.advances('#tk00#', tab)) == 130 and sum(PX.advances('#sname#', tab)) == 130 and sum(PX.advances('#chi#', tab)) == 104,
          'px tokens: names 10 x 13, other #x# 8 x 13')
    check(sum(PX.advances('%d', tab)) == 36 and sum(PX.advances('%D', tab)) == 72 and sum(PX.advances('%m', tab)) == 180
          and sum(PX.advances('%s', tab)) == 104 and sum(PX.advances('%5d', tab)) == 60, 'px tokens: numbers 12 px per cell, %s 13 px per cell, explicit field width')
    check(sum(PX.advances('@Y/hi@', tab)) == tab[ord('h')] + tab[ord('i')], 'px tokens: colour tokens are zero width')
    check(PX.advances('100%%', tab)[-1] == tab[ord('%')], 'px tokens: %% is one percent glyph')
    # transcheck: pixel mode
    it = mk('私ではそのような重責を果たすのは\n不可能だよ。', bm=60)
    it['max_cells'], it['max_rows'], it['wclass'] = 33, 2, 'BUBBLE?'
    narrow = 'I will illustrate it in this little\nfilm'
    check(T.cells_of_line(narrow.split('\n')[0]) == 35, 'fixture: 35 cells')
    e, _ = C.check_text(it, narrow)
    check('LINE_TOO_WIDE' in [x['code'] for x in e], 'cells mode: 35 cells are too wide for the bubble')
    e, _ = C.check_text(it, narrow, width_mode='pixels')
    check(not [x for x in e if x['code'] == 'LINE_TOO_WIDE'], 'pixel mode: the same line is only %d px and fits' % PX.line_px(narrow.split('\n')[0], tab)[0])
    wide = 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nW'            # 31 x 13 px: 31 cells, over in pixels only
    e, _ = C.check_text(it, wide)
    check('LINE_TOO_WIDE' not in [x['code'] for x in e], 'cells mode: 31 capitals fit 33 cells')
    e, _ = C.check_text(it, wide, width_mode='pixels')
    msgs = [x['msg'] for x in e if x['code'] == 'LINE_TOO_WIDE']
    check(msgs and 'px wide' in msgs[0], 'pixel mode: 31 capitals are 403 px, LINE_TOO_WIDE')
    cell = dict(it, wclass='CELL')
    e, _ = C.check_text(cell, 'i' * 34 + '\nx', width_mode='pixels')
    check('LINE_TOO_WIDE' in [x['code'] for x in e], 'CELL class: pixel mode never admits a line the cell rule refuses')
    one = dict(mk('あ', bm=60), max_cells=33, max_rows=1, wclass='BUBBLE?')
    punct = 'x' * 32 + '.'
    e, _ = C.check_text(one, punct)
    check('PUNCT_AT_EDGE' in [x['code'] for x in e], 'cells mode: a full 33-cell line ending in a full stop is PUNCT_AT_EDGE')
    e, _ = C.check_text(one, punct, width_mode='pixels')
    check('PUNCT_AT_EDGE' not in [x['code'] for x in e], 'pixel mode: no punctuation edge rule')
    shard = {'shard': 1, 'items': [it]}
    rep = C.check_result(shard, {'shard': 1, 'results': [{'key': it['key'], 'en': wide}]}, width_mode='pixels')
    lw = [x for x in rep['errors'] if x['code'] == 'LINE_TOO_WIDE']
    check(lw and lw[0]['max_px'] == 396 and lw[0]['over_px'] == 6, 'check_result passes the width mode through')
    rep = C.check_result(shard, {'shard': 1, 'results': [{'key': it['key'], 'en': wide}]})
    check(all(x['code'] != 'LINE_TOO_WIDE' for x in rep['errors']), 'check_result default stays cells')
    # word wrap
    text = 'I cannot possibly bear such a heavy responsibility for the whole club and its supporters'
    for mode in ('cells', 'pixels'):
        ls = PX.wrap_text(text, 33, mode, tab).split('\n')
        okw = all(PX.fits(PX.advances(l, tab), 33) if mode == 'pixels' else len(l) <= 33 for l in ls)
        check(' '.join(ls) == text and okw, 'wrap_text %s: words kept, every line fits' % mode)
    check(len(PX.wrap_text(text, 33, 'pixels', tab).split('\n')) <= len(PX.wrap_text(text, 33, 'cells', tab).split('\n')), 'wrap_text: pixel mode needs no more lines than cell mode here')
    check(PX.wrap_text('one\ntwo three', 39, 'cells', tab) == 'one\ntwo three', 'wrap_text keeps existing newlines')
    # winwidth.check_en_px / recheck, transwork prompt / show
    lim = WW.Limit(33, 2, 'BUBBLE?', 'ja-fit')
    nl, ws, over, wrapped = WW.check_en_px(wide, lim, 'あ\nあ', tab)
    check(nl == 2 and over == 6 and wrapped == 3 and ws[0] == 403, 'winwidth.check_en_px: 31 capitals over by 6 px, wraps to 3 rows')
    tsv = os.path.join(tmp, 'px_list.tsv')
    head = 'rank\tvisibility\tshard\tkey\tid0\tarea\tcategory\tclass\tmax_cells\tmax_rows\tbasis\trecords\ten_lines\tja_lines\twidest\tover_by\twrapped_rows\ten\tja\n'

    def row(k, en):
        return '\t'.join(['1', 'A', '1', k, 'X#1', 'meeting', 'dialogue', 'BUBBLE?', '33', '2', 'ja-fit', '2', '2', '2', '35', '2', '3', en, 'あ\\nあ']) + '\n'
    with open(tsv, 'w', encoding='utf-8', newline='') as fh:
        fh.write(head + row('aaa', 'I will illustrate it in this little\\nfilm') + row('bbb', 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\\nW'))
    outf = os.path.join(tmp, 'px_left.tsv')
    rv, txt = run_cli(WW.main, ['recheck', tsv, '--out-file', outf])
    left = open(outf, encoding='utf-8').read().splitlines()
    check(len(left) == 2 and left[1].split('\t')[3] == 'bbb' and '1 disappear' in txt, 'winwidth recheck: keeps only the text that is still over (%s)' % txt.splitlines()[:1])
    env = mkenv(tmp, 'pxp')
    rv, txt = run_cli(W.main, ['prompt', '1', '--shards', env['shards']])
    check(' 4. Width: every ASCII character is one cell; at most item.max_cells cells per line' in txt and 'PIXELS' not in txt and 'max_px' not in txt,
          'transwork prompt: default (cells) keeps the cell rule 4 and no max_px')
    rv, txt = run_cli(W.main, ['prompt', '1', '--shards', env['shards'], '--width-mode', 'pixels'])
    check('Width in PIXELS' in txt and '13 px: ' in txt and '"max_px": ' in txt and '"max_cells": ' in txt, 'transwork prompt --width-mode pixels: pixel rule 4, advances, max_px in the items')
    rv, txt = run_cli(W.main, ['show', '1', '--shards', env['shards'], '--width-mode', 'pixels'])
    check(txt.startswith('shard 1'), 'transwork show --width-mode pixels runs')


def test_check_malformed(tmp):
    env = mkenv(tmp, 'cm')
    n, key = env['sh_of']['決定'], T.key_of('決定')
    shards = env['shards']

    def chk(name, data, *extra):
        return run_cli(C.main, [put(tmp, name, data), '--shards', shards] + list(extra))

    good = {'shard': n, 'results': [{'key': key, 'en': 'OK'}]}
    rv, txt = chk('c_good.json', good)
    check(rv == 0, 'baseline result passes: %s' % txt)
    rv, txt = chk('c_bom.json', b'\xef\xbb\xbf' + json.dumps(good).encode('utf-8'))
    check(rv == 0, 'UTF-8 BOM accepted: %s' % txt)
    for name, data, why in [
            ('c_list.json', [{'key': key, 'en': 'OK'}], 'top level is a list'),
            ('c_scalar.json', 5, 'top level is a number'),
            ('c_null.json', {'shard': n, 'results': None}, 'results is null'),
            ('c_nokey.json', {'shard': n}, 'results member missing'),
            ('c_str.json', {'shard': n, 'results': 'abc'}, 'results is a string'),
            ('c_num.json', {'shard': n, 'results': 7}, 'results is a number'),
            ('c_badshard.json', {'shard': 'x', 'results': []}, 'shard is not a number'),
            ('c_listshard.json', {'shard': [1], 'results': []}, 'shard is a list'),
            ('c_boolshard.json', {'shard': True, 'results': []}, 'shard is a boolean'),
            ('c_noshard.json', {'shard': 99999, 'results': []}, 'shard file does not exist'),
            ('c_nojson.json', b'this is not json', 'not JSON'),
            ('c_empty.json', b'', 'empty file'),
            ('c_badutf.json', b'\xff\xfe\x00{', 'not UTF-8')]:
        rv, txt = chk(name, data)
        check(rv == 2 and 'malformed input' in txt, 'malformed input (%s) -> exit 2, no crash: %s %s' % (why, rv, txt.strip()[:100]))
    rv, txt = run_cli(C.main, [os.path.join(tmp, 'nothere.json'), '--shards', shards])
    check(rv == 2, 'missing file -> exit 2')
    rv, txt = chk('c_strshard.json', {'shard': str(n), 'results': [{'key': key, 'en': 'OK'}]})
    check(rv == 0, 'shard number given as a digit string is accepted')
    rv, js = chk('c_list2.json', [1], '--json')
    check(rv == 2 and json.loads(js[js.index('{\n'):])['ok'] is False, '--json on malformed input still prints a JSON verdict')
    # validation errors (exit 1) are not malformed input (exit 2)
    rv, txt = chk('c_val.json', {'shard': n, 'results': [{'key': key, 'en': 'Café'}]})
    check(rv == 1, 'validation error -> exit 1')
    # bad entries inside a well-formed file: BAD_ENTRY errors (exit 1), never a crash
    rv, txt = chk('c_entries.json', {'shard': n, 'results': [{'key': ['a'], 'en': 'x'}, {'en': 'x'}, 5, None, 'str', {'key': {'k': 1}},
                                                            {'key': key, 'en': 'OK'}]}, '--json')
    rep = json.loads(txt) if rv == 1 else {}
    check(rv == 1 and sum(1 for e in rep.get('errors', []) if e['code'] == 'BAD_ENTRY') == 6, 'six unusable entries -> six BAD_ENTRY, exit 1: %s' % txt[:100])
    check(rep.get('n_ok') == 1, 'the valid entry of the same file still validates')
    rv, txt = chk('c_entval.json', {'shard': n, 'results': [{'key': key, 'en': ['OK']}]})
    check(rv == 1 and 'BAD_ENTRY' in txt, 'en that is not a string -> BAD_ENTRY')
    # lone surrogate in en (and in a key): reported, printable, writable
    rej = os.path.join(tmp, 'c_rej.json')
    rv, txt = chk('c_surr.json', {'shard': n, 'results': [{'key': key, 'en': 'a\ud800b'}, {'key': 'k\udc80', 'en': 'x'}]}, '--rejects', rej)
    check(rv == 1 and 'NON_ASCII' in txt and 'UNKNOWN_KEY' in txt, 'lone surrogate: errors reported without a crash: %s %s' % (rv, txt.strip()[:120]))
    check(os.path.exists(rej) and C.load_json(rej)['repair'][0]['errors'][0]['code'] == 'NON_ASCII', 'repair order written for the surrogate case')
    rv, js = chk('c_surr2.json', {'shard': n, 'results': [{'key': key, 'en': 'a\ud800b'}]}, '--json')
    check(rv == 1 and json.loads(js)['ok'] is False, '--json with a lone surrogate')
    # '{key: en}' maps keep working
    rv, txt = chk('c_map.json', {'shard': n, 'results': {key: 'OK'}})
    check(rv == 0, 'map-style results accepted')


def test_merge_malformed(tmp):
    env = mkenv(tmp, 'mm')
    sh_of = env['sh_of']
    orig = ens_of(env['tdb'])
    K = T.key_of
    f_good = put(tmp, 'm_good.json', {'shard': sh_of['決定'], 'results': [{'key': K('決定'), 'en': 'OK'}]})
    f_list = put(tmp, 'm_list.json', [1, 2])
    f_null = put(tmp, 'm_null.json', {'shard': sh_of['決定'], 'results': None})
    f_json = put(tmp, 'm_json.json', b'{oops')
    f_bom = put(tmp, 'm_bom.json', b'\xef\xbb\xbf' + json.dumps({'shard': sh_of[JA_NAME], 'results': [{'key': K(JA_NAME), 'en': 'O. Kawamoto'}]}).encode())
    f_surr = put(tmp, 'm_surr.json', {'shard': sh_of[JA_PF], 'results': [{'key': K(JA_PF), 'en': 'a\ud800b'}]})
    f_bad = put(tmp, 'm_bad.json', {'shard': sh_of[JA_SEVEN], 'results': [
        {'key': K(JA_SEVEN), 'en': "@Y/7-dan@ club.\nLet's go!"}, {'en': 'x'}, 5, {'key': ['a'], 'en': 'x'}]})
    f_missing = os.path.join(tmp, 'm_does_not_exist.json')
    rv, txt = mrun(env, [f_list, f_good, f_null, f_json, f_bom, f_surr, f_bad, f_missing])
    ens = ens_of(env['tdb'])
    check(rv == 2, 'a batch with malformed files exits 2: %s %s' % (rv, txt[-200:]))
    check(ens['FLOW_PRG/OPTION.BIN#10'] == 'OK' and ens['FLOW_PRG/MEETING.BIN#160'] == 'OK', 'valid file of the batch still merged')
    check(ens['FLOW_PRG/MEETING.BIN#170'] == 'O. Kawamoto', 'BOM file of the batch merged')
    check(ens['FLOW_PRG/OPTION.BIN#30'] == "@Y/7-dan@ club.\nLet's go!", 'valid item of a file with bad entries merged')
    check(ens['FLOW_PRG/MEETING.BIN#140'] == '', 'lone-surrogate item refused, not written')
    check('MALFORMED result files (not merged, reported separately): 4' in txt, 'four malformed files counted: %s' % txt)
    for name in ('m_list.json', 'm_null.json', 'm_json.json', 'm_does_not_exist.json'):
        check(re.search(r'  MALFORMED \S*%s: ' % re.escape(name), txt) is not None, 'malformed file named in the report: %s' % name)
    check('BAD_ENTRY: 3 result entries' in txt, 'BAD_ENTRY entries counted (3): %s' % txt)
    check('REFUSED' in txt and 'NON_ASCII' in txt, 'surrogate item listed as refused')
    check(not [f for f in os.listdir(env['tdb']) if f.endswith('.tmp')], 'no temp files left')
    check(not os.path.exists(env['lock']), 'lock released')

    # BAD_ENTRY alone: valid items merge, exit 1 (was 0), count printed
    env = mkenv(tmp, 'mb')
    f = put(tmp, 'mb_bad.json', {'shard': env['sh_of']['決定'], 'results': [{'key': T.key_of('決定'), 'en': 'OK'}, {'en': 'x'}, None]})
    rv, txt = mrun(env, [f])
    check(rv == 1 and 'BAD_ENTRY: 2' in txt and ens_of(env['tdb'])['FLOW_PRG/OPTION.BIN#10'] == 'OK', 'BAD_ENTRY -> exit 1, valid entry merged: %s %s' % (rv, txt[-160:]))
    env = mkenv(tmp, 'mc')
    f = put(tmp, 'mc_bad.json', {'shard': env['sh_of']['決定'], 'results': [{'key': T.key_of('決定'), 'en': 'OK'}, 7]})
    snap = read_all(env['tdb'])
    rv, txt = mrun(env, [f], '--all-or-nothing')
    check(rv == 1 and read_all(env['tdb']) == snap and 'BAD_ENTRY: 1' in txt, '--all-or-nothing: a BAD_ENTRY refuses the run')
    f2 = put(tmp, 'mc_ok.json', {'shard': env['sh_of']['決定'], 'results': [{'key': T.key_of('決定'), 'en': 'OK'}]})
    rv, txt = mrun(env, [f2, put(tmp, 'mc_list.json', [])], '--all-or-nothing')
    check(rv == 2 and read_all(env['tdb']) == snap, '--all-or-nothing: a malformed file refuses the run')
    rv, txt = mrun(env, [f2, put(tmp, 'mc_list2.json', [])], '--dry-run')
    check(rv == 2 and read_all(env['tdb']) == snap and 'DRY RUN' in txt, '--dry-run with a malformed file writes nothing')

    # whitespace-only en: refused at merge time for a skip-hinted item too
    env = mkenv(tmp, 'mw')
    f = put(tmp, 'mw.json', {'shard': env['sh_of'][JA_DEBUG], 'results': [{'key': T.key_of(JA_DEBUG), 'en': '   '}]})
    snap = read_all(env['tdb'])
    rv, txt = mrun(env, [f])
    check(rv == 1 and read_all(env['tdb']) == snap and 'REFUSED' in txt and 'EMPTY' in txt, 'whitespace-only en refused for a skip-hinted item: %s %s' % (rv, txt[-120:]))


# (5) merge lock, stale temp files ---------------------------------------------------------------------------

def test_merge_lock(tmp):
    env = mkenv(tmp, 'lk')
    sh_of = env['sh_of']
    f = put(tmp, 'lk_label.json', {'shard': sh_of['決定'], 'results': [{'key': T.key_of('決定'), 'en': 'OK'}]})
    snap = read_all(env['tdb'])
    # a lock held by somebody else: wait, then stop with a message that names the file; never delete the foreign lock
    with open(env['lock'], 'w') as fh:
        fh.write('pid 1 (somebody else)\n')
    t0 = time.time()
    rv, txt = mrun(env, [f], '--lock-timeout', '0.4')
    check(rv == 2 and 'merge lock' in txt and env['lock'] in txt and 'delete the lock file' in txt, 'held lock -> exit 2 with a timeout message: %s' % txt.strip()[:200])
    check(0.3 < time.time() - t0 < 10, 'it waited for the timeout (%.1f s)' % (time.time() - t0))
    check(read_all(env['tdb']) == snap and os.path.exists(env['lock']), 'nothing written, foreign lock file left alone')
    rv, txt = mrun(env, [f], '--lock-timeout', '0.2', '--dry-run')
    check(rv == 0 and 'DRY RUN' in txt, 'a dry run does not need the lock')
    os.remove(env['lock'])
    rv, txt = mrun(env, [f])
    check(rv == 0 and not os.path.exists(env['lock']), 'lock file removed after a successful merge')
    # lock released when the merge fails half way (file with CRLF: refused with an error)
    env2 = mkenv(tmp, 'lk2')
    p = os.path.join(env2['tdb'], 'FLOW_PRG__OPTION.BIN.jsonl')
    with open(p, 'rb') as fh:
        data = fh.read()
    with open(p, 'wb') as fh:
        fh.write(data.replace(b'\n', b'\r\n'))
    f2 = put(tmp, 'lk2_label.json', {'shard': env2['sh_of']['決定'], 'results': [{'key': T.key_of('決定'), 'en': 'OK'}]})
    rv, txt = mrun(env2, [f2])
    check(rv == 2 and 'CRLF' in txt and not os.path.exists(env2['lock']), 'lock released after a failed merge: %s' % txt.strip()[:100])

    # stale temp files of a crashed run are removed (under the lock), but not by a dry run
    env3 = mkenv(tmp, 'lk3')
    stale = [os.path.join(env3['tdb'], 'FLOW_PRG__MEETING.BIN.jsonl.tmp'), os.path.join(env3['rejects'], '0003.json.tmp')]
    os.makedirs(env3['rejects'])
    for s in stale:
        with open(s, 'w') as fh:
            fh.write('half written')
    f3 = put(tmp, 'lk3_label.json', {'shard': env3['sh_of']['決定'], 'results': [{'key': T.key_of('決定'), 'en': 'OK'}]})
    mrun(env3, [f3], '--dry-run')
    check(all(os.path.exists(s) for s in stale), 'dry run leaves temp files alone')
    rv, txt = mrun(env3, [f3])
    check(rv == 0 and not any(os.path.exists(s) for s in stale) and 'removed stale temp files' in txt, 'stale temp files removed: %s' % txt.strip()[:200])

    # serialisation: the waiting merge re-reads the database INSIDE the lock.  While we hold the lock, "another merge"
    # writes a record; the waiting process must not clobber it with a stale copy.
    env4 = mkenv(tmp, 'lk4')
    f4 = put(tmp, 'lk4_label.json', {'shard': env4['sh_of']['決定'], 'results': [{'key': T.key_of('決定'), 'en': 'OK'}]})
    cmd = [sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, 'transmerge.py'), 'merge', f4, '--tdb', env4['tdb'], '--shards', env4['shards'],
           '--backup-dir', env4['backup'], '--rejects-dir', env4['rejects'], '--lock-file', env4['lock'], '--lock-timeout', '60']
    with M.MergeLock(env4['lock'], 5):
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        time.sleep(1.0)
        check(proc.poll() is None, 'second merge waits while the lock is held')
        spec = fixture_db()
        spec['FLOW_PRG__OPTION.BIN'][1][1]['en'] = 'Concurrent Name'       # OPTION#20, a record the waiting merge also rewrites the file of
        write_db(env4['tdb'], spec)
    out, _ = proc.communicate(timeout=60)
    ens = ens_of(env4['tdb'])
    check(proc.returncode == 0, 'waiting merge succeeds after the lock is released: %s' % out.decode('utf-8', 'replace')[-200:])
    check(ens['FLOW_PRG/OPTION.BIN#10'] == 'OK' and ens['FLOW_PRG/OPTION.BIN#20'] == 'Concurrent Name', 'no lost update: the other merge\'s write survived')
    check(not os.path.exists(env4['lock']), 'lock removed by the subprocess')

    # two real concurrent processes: both merges land, distinct backup directories
    env5 = mkenv(tmp, 'lk5')
    fa = put(tmp, 'lk5_a.json', {'shard': env5['sh_of']['決定'], 'results': [{'key': T.key_of('決定'), 'en': 'OK'}]})
    fb = put(tmp, 'lk5_b.json', {'shard': env5['sh_of'][JA_NAME], 'results': [{'key': T.key_of(JA_NAME), 'en': 'O. Kawamoto'}]})
    procs = [subprocess.Popen([sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, 'transmerge.py'), 'merge', fx, '--tdb', env5['tdb'],
                               '--shards', env5['shards'], '--backup-dir', env5['backup'], '--rejects-dir', env5['rejects'],
                               '--lock-file', env5['lock']], stdout=subprocess.PIPE, stderr=subprocess.STDOUT) for fx in (fa, fb)]
    outs = [p_.communicate(timeout=120)[0].decode('utf-8', 'replace') for p_ in procs]
    ens = ens_of(env5['tdb'])
    check([p_.returncode for p_ in procs] == [0, 0], 'two concurrent merges both succeed: %s' % [o[-120:] for o in outs])
    check(ens['FLOW_PRG/OPTION.BIN#10'] == 'OK' and ens['FLOW_PRG/MEETING.BIN#170'] == 'O. Kawamoto', 'both concurrent merges are in the database')
    check(sorted(d for d in os.listdir(env5['backup']) if d.isdigit()) == ['0001', '0002'], 'distinct backup counters')


# (8) path resolution ----------------------------------------------------------------------------------------

def test_paths(tmp):
    root, cwd0 = os.path.join(tmp, 'fakeroot'), os.path.join(tmp, 'cwd0')
    os.makedirs(root)
    os.makedirs(cwd0)
    check(T.resolve_path(os.path.abspath(tmp)) == os.path.normpath(os.path.abspath(tmp)), 'absolute path kept')
    old_root, old_cwd = T.ROOT, os.getcwd()
    try:
        T.ROOT = root
        os.chdir(cwd0)
        os.makedirs(os.path.join(root, 'only_root'))
        os.makedirs(os.path.join(cwd0, 'both'))
        os.makedirs(os.path.join(root, 'both'))
        check(T.resolve_path('only_root') == os.path.join(root, 'only_root'), 'relative path found under the repo root')
        check(T.resolve_path('both') == os.path.join(cwd0, 'both'), 'the current directory wins over the repo root')
        check(T.resolve_path('new_out') == os.path.join(cwd0, 'new_out'), 'a path that exists nowhere is relative to the cwd')

        # result files + every option relative, database / shards only under the (fake) repo root
        env = mkenv(tmp, 'pt')
        shutil.copytree(env['tdb'], os.path.join(root, 'tdbrel'))
        shutil.copytree(env['shards'], os.path.join(root, 'shardsrel'))
        n, key = env['sh_of']['決定'], T.key_of('決定')
        os.makedirs(os.path.join(root, 'results'))
        os.makedirs(os.path.join(cwd0, 'results'))
        with open(os.path.join(root, 'results', 'x.json'), 'w') as fh:
            json.dump({'shard': n, 'results': [{'key': key, 'en': 'FromRoot'}]}, fh)
        argv = ['merge', 'results/x.json', '--tdb', 'tdbrel', '--shards', 'shardsrel', '--backup-dir', 'bk_rel',
                '--rejects-dir', 'rj_rel', '--lock-file', 'lock_rel/merge.lock']
        rv, txt = run_cli(M.main, argv)
        ens = ens_of(os.path.join(root, 'tdbrel'))
        check(rv == 0 and ens['FLOW_PRG/OPTION.BIN#10'] == 'FromRoot', 'result file / --tdb / --shards fall back to the repo root: %s %s' % (rv, txt.strip()[-160:]))
        check(os.path.isdir(os.path.join(cwd0, 'bk_rel', '0001')) and not os.path.exists(os.path.join(root, 'bk_rel')),
              'a new output directory is created relative to the cwd')
        check(not os.path.exists(os.path.join(cwd0, 'lock_rel', 'merge.lock')) and os.path.isdir(os.path.join(cwd0, 'lock_rel')), 'lock file in the cwd, released')
        with open(os.path.join(cwd0, 'results', 'x.json'), 'w') as fh:
            json.dump({'shard': n, 'results': [{'key': key, 'en': 'FromCwd'}]}, fh)
        rv, txt = run_cli(M.main, argv + ['--overwrite'])
        check(rv == 0 and ens_of(os.path.join(root, 'tdbrel'))['FLOW_PRG/OPTION.BIN#10'] == 'FromCwd', 'the same relative result path resolves against the cwd first')
        rv, txt = run_cli(M.main, ['merge', 'results/none.json', '--tdb', 'tdbrel', '--shards', 'shardsrel', '--lock-file', 'lock_rel/merge.lock',
                                   '--backup-dir', 'bk_rel', '--rejects-dir', 'rj_rel'])
        check(rv == 2 and 'malformed result file results/none.json' in txt, 'a missing result file is reported as such')
        rv, txt = run_cli(M.main, ['status', '--tdb', 'tdbrel', '--shards', 'shardsrel'])
        check(rv == 0 and 'records with en:' in txt, 'status resolves its options the same way')
        rv, txt = run_cli(C.main, ['results/x.json', '--shards', 'shardsrel'])
        check(rv == 0, 'transcheck resolves the result file and --shards the same way: %s' % txt.strip()[-100:])
    finally:
        os.chdir(old_cwd)
        T.ROOT = old_root


# (6, 7) textdb / textfmt_common writers ---------------------------------------------------------------------

def test_writers(tmp):
    # (6) textdb.write_jsonl is atomic
    p = os.path.join(tmp, 'w6', 'x.jsonl')
    textdb.write_jsonl(p, [rec('S#1', 'あ', 4, en='A')])
    before = read_bytes(p)
    try:
        textdb.write_jsonl(p, [rec('S#1', 'あ', 4, en='B'), rec('S#2', 'bad\ud800', 4)])
        failed = False
    except UnicodeEncodeError:
        failed = True
    check(failed and read_bytes(p) == before and not [f for f in os.listdir(os.path.dirname(p)) if f.endswith('.tmp')],
          'textdb.write_jsonl: a failing write leaves the old file intact and no temp file')
    real_replace = os.replace

    def boom(a, b):
        raise OSError('simulated crash before the rename')
    os.replace = boom
    try:
        try:
            textdb.write_jsonl(p, [rec('S#1', 'あ', 4, en='C')])
        except OSError:
            pass
    finally:
        os.replace = real_replace
    check(read_bytes(p) == before and not [f for f in os.listdir(os.path.dirname(p)) if f.endswith('.tmp')], 'textdb.write_jsonl: nothing visible before os.replace')
    textdb.write_jsonl(p, [rec('S#1', 'あ', 4, en='D')])
    check(textdb.read_jsonl(p)[0]['en'] == 'D' and not os.path.exists(p + '.tmp'), 'textdb.write_jsonl replaces the file')

    # (6) orphan side files are numbered, never overwritten
    od = os.path.join(tmp, 'w6_orph')
    os.makedirs(od)
    names = []
    for i in range(3):
        op = textdb.orphan_path(od, 'FLOW_PRG/CHALDANI.BIN')
        names.append(os.path.basename(op))
        textdb.write_jsonl(op, [rec('FLOW_PRG/CHALDANI.BIN#%x' % i, 'ゴースト', 8, en='G%d' % i)])
    check(names == ['FLOW_PRG__CHALDANI.BIN.jsonl', 'FLOW_PRG__CHALDANI.BIN.2.jsonl', 'FLOW_PRG__CHALDANI.BIN.3.jsonl'], 'orphan files get a counter: %s' % names)
    check([textdb.read_jsonl(os.path.join(od, n))[0]['en'] for n in names] == ['G0', 'G1', 'G2'], 'earlier orphan sets are kept')

    # (7) textfmt_common.write_jsonl / merge_existing keep skip + extra keys
    q = os.path.join(tmp, 'w7', 'y.jsonl')
    ents = [{'id': 'S#1', 'ja': 'あ', 'en': 'A', 'max_bytes': 4, 'refs': 1, 'ctx': 'c', 'skip': True, 'note': 'keep me', 'orphan': True},
            {'id': 'S#2', 'ja': 'い', 'en': '', 'max_bytes': 4, 'refs': None, 'ctx': ''}]
    TC.write_jsonl(q, ents)
    lines = read_text(q).split('\n')
    check(list(json.loads(lines[0]).keys()) == ['id', 'ja', 'en', 'max_bytes', 'refs', 'ctx', 'skip', 'note', 'orphan'],
          'textfmt write_jsonl: fixed keys first, extra keys (skip, note, orphan) kept: %s' % list(json.loads(lines[0]).keys()))
    check(list(json.loads(lines[1]).keys()) == ['id', 'ja', 'en', 'max_bytes', 'refs', 'ctx'], 'a plain record stays plain')
    check(not os.path.exists(q + '.tmp'), 'textfmt write_jsonl leaves no temp file')
    again = TC.read_jsonl(q)
    check(again[0]['skip'] is True and again[0]['note'] == 'keep me' and again[0]['orphan'] is True, 'extra keys round-trip')
    # merge_existing: en + skip + extra keys come back when the id and ja match, nothing when ja changed
    fresh = [{'id': 'S#1', 'ja': 'あ', 'en': '', 'max_bytes': 4, 'refs': 1, 'ctx': 'c2'},
             {'id': 'S#2', 'ja': 'い2', 'en': '', 'max_bytes': 4, 'refs': None, 'ctx': ''},
             {'id': 'S#3', 'ja': 'う', 'en': '', 'max_bytes': 4, 'refs': None, 'ctx': ''}]
    merged = TC.merge_existing(q, [dict(e) for e in fresh])
    check(merged[0]['en'] == 'A' and merged[0]['skip'] is True and merged[0]['note'] == 'keep me' and merged[0]['ctx'] == 'c2', 'merge_existing keeps en, skip and extra keys; fresh fields win')
    check(set(merged[1]) == set(fresh[1]) and merged[1]['en'] == '', 'ja changed: nothing carried over')
    TC.write_jsonl(q, merged)
    check(TC.read_jsonl(q)[0]['skip'] is True, 'skip survives an extractor re-run (merge_existing + write_jsonl)')
    try:
        TC.write_jsonl(q, [{'id': 'S#9', 'ja': 'x\ud800'}])
    except UnicodeEncodeError:
        pass
    check(TC.read_jsonl(q)[0]['id'] == 'S#1' and not os.path.exists(q + '.tmp'), 'textfmt write_jsonl is atomic too')
    # a file left in mixed separator styles by another writer is healed by the merge writer (translib.normalise_styles)
    a = {'id': 'S#1', 'ja': 'あ', 'en': 'a'}
    b = {'id': 'S#2', 'ja': 'い', 'en': 'b'}
    mixed = T.DbFile('X', q, [T.dump_record(a, False), T.dump_record(b, True)], [a, b], False)
    check(T.normalise_styles(mixed) == 1 and mixed.lines == [T.dump_record(a, False), T.dump_record(b, False)]
          and mixed.recs == [a, b] and T.normalise_styles(mixed) == 0, 'normalise_styles re-serialises only the odd lines, records untouched')


# ---------------------------------------------------------- real data ----

def test_real(tmp):
    t0 = time.time()
    real = T.DEFAULT_TDB
    db = T.load_db(real)
    check(db.count() > 100000, 'real database loaded: %d records' % db.count())
    # re-serialising every record with the detected style reproduces the file lines exactly
    bad = 0
    for f in db.files:
        if not f.plain:
            bad += 1
        for ln, r in zip(f.lines, f.recs):
            if T.dump_record(r, f.compact) != ln:
                bad += 1
                break
    check(bad == 0, 'every real jsonl file re-serialises byte-identically (%d files differ)' % bad)
    out1, out2 = os.path.join(tmp, 'real1'), os.path.join(tmp, 'real2')
    t1 = time.time()
    quiet(W.main, ['plan', '--out', out1, '--quiet'])
    plan_s = time.time() - t1
    quiet(W.main, ['plan', '--out', out2, '--quiet'])
    s1, s2 = read_all_json(os.path.join(out1, 'shards')), read_all_json(os.path.join(out2, 'shards'))
    check(s1 == s2, 'real plan is deterministic')
    check(plan_s < 60, 'real plan under a minute (%.1f s)' % plan_s)
    seen, n_items, sizes = set(), 0, []
    for fn, raw in s1.items():
        sh = json.loads(raw)
        sizes.append(len(sh['items']))
        check(len(sh['items']) == sh['n_items'] and len(sh['items']) <= W.SHARD_MAX, 'shard %s size' % fn)
        for it in sh['items']:
            check(it['key'] not in seen, 'unique key %s' % it['key']) if it['key'] in seen else None
            seen.add(it['key'])
            n_items += 1
    distinct = len({r['ja'] for _, _, r in db.records()})
    check(n_items == distinct == len(seen), 'every distinct Japanese text is in exactly one shard (%d / %d)' % (n_items, distinct))
    check(max(sizes) <= 150 and sorted(sizes)[len(sizes) // 2] >= 100, 'shard sizes about 100-150')
    # (1) skip hints on the real data: player-visible text is never hidden, the listed pointer junk is
    allitems = [it for raw in s1.values() for it in json.loads(raw)['items']]
    hidden = [it['ja'][:30] for it in allitems if it['skip'] and re.search(
        r'テスト販売|BESTPLAYERS|CHALLENGE MODE|REPEAT|dricas|DIVISION|Dreamcast|SEGA', it['ja'])]
    check(not hidden, 'no real player-visible text with Latin words / test sale is skip-hinted: %s' % hidden)
    by_ja = {it['ja']: it for it in allitems}
    check(by_ja[JA_GMSHOW02]['skip'] is None, 'GMSHOW02 network demo text is translated')
    for ja in ('緒喧', ' 縁限誌呉誌交誌兄'):
        check(by_ja[ja]['skip'] and 'trans_skip_ids' in by_ja[ja]['skip'], 'listed NEWS_OP pointer junk %r is skip-hinted' % ja)
    n_skip = sum(1 for it in allitems if it['skip'])
    check(300 < n_skip < 750, 'skip-hint count in a sane range: %d' % n_skip)
    check(by_ja['緒喧']['id0'] == 'FLOW_PRG/NEWS_OP.BIN#28f21', 'canonical id of the junk text')
    # merge a 2-item fixture into a COPY of the real database
    cp = os.path.join(tmp, 'realcopy')
    shutil.copytree(real, cp, ignore=shutil.ignore_patterns('glossary.tsv'))
    # the real database is translated by now: blank the English of the two fixture texts in the COPY so the merge below
    # starts from the untranslated state the assertions describe
    cdb = T.load_db(cp)
    for cf in cdb.files:
        touched = False
        for li, r in enumerate(cf.recs):
            if r['ja'] in ('億', '万円') and r.get('en'):
                r['en'] = ''
                cf.lines[li] = T.dump_record(r, cf.compact)
                touched = True
        if touched:
            T.write_atomic(cf.path, '\n'.join(cf.lines) + '\n')
    sh1 = json.loads(s1['0001.json'])
    it_a = next(i for i in sh1['items'] if i['ja'] == '億')
    it_b = next(i for i in sh1['items'] if i['ja'] == '万円')
    res = {'shard': 1, 'results': [{'key': it_a['key'], 'en': 'B'}, {'key': it_b['key'], 'en': 'x' * 8}]}
    rp = os.path.join(tmp, 'real_res.json')
    with open(rp, 'w', encoding='utf-8') as f:
        json.dump(res, f)
    rv, txt = quiet(M.main, ['merge', rp, '--tdb', cp, '--shards', os.path.join(out1, 'shards'), '--backup-dir', os.path.join(tmp, 'rb'),
                            '--rejects-dir', os.path.join(tmp, 'rr'), '--lock-file', os.path.join(tmp, 'mt.lock')])
    check(rv == 1 and 'REFUSED' in txt, 'real fixture: 8 chars into a 7-char slot refused')
    res['results'][1]['en'] = 'x' * 7
    with open(rp, 'w', encoding='utf-8') as f:
        json.dump(res, f)
    rv, txt = quiet(M.main, ['merge', rp, '--tdb', cp, '--shards', os.path.join(out1, 'shards'), '--backup-dir', os.path.join(tmp, 'rb'),
                            '--rejects-dir', os.path.join(tmp, 'rr'), '--lock-file', os.path.join(tmp, 'mt.lock')])
    db2 = T.load_db(cp)
    n_a = sum(1 for _, _, r in db2.records() if r['ja'] == '億' and r['en'] == 'B')
    check(rv == 0 and n_a == it_a['ids_count'], 'real fixture: all %d ids of the text received the string (got %d)' % (it_a['ids_count'], n_a))
    # exactly the records of the two texts changed
    orig_en = {r['id']: r.get('en', '') for _, _, r in db.records()}
    fixture_ja = ('億', '万円')
    changed = sum(1 for _, _, r in db2.records() if r.get('en', '') != (orig_en.get(r['id'], '') if r['ja'] not in fixture_ja else ''))
    check(changed == it_a['ids_count'] + it_b['ids_count'], 'only the records of the merged texts changed')
    print('  real part: %.1f s, plan %.1f s' % (time.time() - t0, plan_s))


def main():
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix='test_transwork_')
    try:
        print('plan'); test_plan(tmp)
        print('check'); test_check(); test_check_cli(tmp)
        print('window width'); test_window_width()
        print('pixel width'); test_pixel_width(tmp)
        print('merge/status'); test_merge(tmp)
        print('extract guard'); test_preserve_en(tmp)
        print('skip hints'); test_classify(tmp)
        print('malformed input / whitespace / BAD_ENTRY'); test_whitespace_rules(); test_check_malformed(tmp); test_merge_malformed(tmp)
        print('merge lock'); test_merge_lock(tmp)
        print('paths'); test_paths(tmp)
        print('writers (textdb, textfmt_common)'); test_writers(tmp)
        if not QUICK:
            print('real database'); test_real(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('%d checks, %d failed, %.0f s' % (n_checks, len(fails), time.time() - t0))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
