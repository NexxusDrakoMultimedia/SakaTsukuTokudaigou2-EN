"""transwork: plan the translation work for a fleet of translator agents.

    python -I -X utf8 tools/transwork.py plan   [--tdb translation] [--out build/trans] [--skip-ids FILE] [--quiet]
    python -I -X utf8 tools/transwork.py prompt N [--shards DIR] [--width-mode cells|pixels] [--px-profile on|ideal|off]
                                                                       translator prompt for shard N (pixels: rule 4 and every
                                                                       item carry the pixel rule, docs/pixel-widths.md; default cells
                                                                       is byte-identical to the earlier prompt)
    python -I -X utf8 tools/transwork.py ids KEY  [--tdb translation]  every record id of a distinct text
    python -I -X utf8 tools/transwork.py show N   [--shards DIR] [--width-mode cells|pixels]
                                                                       one-line-per-item view of a shard (pixels: w = max_px)

`plan` reads translation/*.jsonl (the `en` fields are NOT consulted: the plan is stable while the
translation advances), groups the 126k records by distinct Japanese text, classifies every distinct
text, computes its byte budgets, orders the texts by what a player meets first and cuts them into
shards of about 100-150 texts of one category and source neighbourhood:

    build/trans/shards/NNNN.json   {shard, category, area, source, sources, guidance, n_items, items:[...]}
    build/trans/index.json         one row per shard
    build/trans/plan_summary.md    counts per category / area / shard
    build/trans/skip_report.tsv    every item with a skip hint (audit list)

Item fields: key (sha1 of ja, 12 hex), ja, ids_count, budget_fixed, budget_min, tokens, lines, ctx, prev,
next, plus skip (hint or null), kind (overlay|ini|bpinfo|ptrblob), id0 (canonical record id),
soft_max_bytes, max_chars_fixed, max_cells, max_rows, wclass.
  max_cells / max_rows  the text window the string is drawn in (tools/winwidth.py, docs/window-widths.md): widest line in
                half-width cells and number of rows; the strictest limit over all records of the text; null for browser text.
                39 / 3 only where the 20-cell window is proven, 33 / 2 where a 17-cell bubble cannot be excluded.
  wclass        MSG20x3 | BUBBLE17x2 | BUBBLE? (bubble or msg, undecidable: limit 33) | CELL (label / name cell) | BROWSER
  budget_fixed  smallest max_bytes (string + NUL) among the records of this text that can only be written
                in place (orphan / stride-table / interior-ptrs / BPINFO / 2_DP); null when every record
                is movable.  max_chars_fixed = budget_fixed - 1.
  budget_min    smallest max_bytes over all records (guide for movable text); null for MESSAGE.INI.
  soft_max_bytes  1.05 x Japanese bytes (with NUL): the length discipline for movable text.
Deterministic: the same translation/*.jsonl always gives byte-identical shard files.

Skip hints are deliberately narrow ("when in doubt do not skip": an unneeded translation is cheap, a missing one
ships Japanese).  A text is skip-hinted only when it is blank, already ASCII, a single IME kana cell, binary junk,
developer text with no sentence content (code identifiers, `tm:%d` variable dumps, dummy / debug vocabulary, PWK_EDIT
labels), or when EVERY record of it is listed in tools/trans_skip_ids.txt (known extraction false positives).
Player-visible prose is never skip-hinted because it contains a Latin word, a colon or the word "test".
"""
import argparse
import collections
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translib as T  # noqa: E402
import winwidth as WW  # noqa: E402
import pixelwidth as PX  # noqa: E402

SHARD_TARGET = 125        # items per shard (100-150 wanted)
SHARD_MAX = 150
SHARD_CHAR_CAP = 12000    # Japanese characters per shard: long prose (HELP) gets fewer, bigger texts per shard


def F(*names):
    return ['FLOW_PRG/%s.BIN' % n for n in names]


# Player-meets-it-first order.  A distinct text is assigned to the FIRST area/source in which it occurs.
AREAS = [
    ('title', ['FLOW_PRG/TITLE.BIN', 'ATFIRST/TITLE.BIN'] + F('OPTION', 'LOGO', 'LOADBAR', 'MOVIE', 'MOVIE_BG')),
    ('new_game', F('S_SELECT', 'N_ENTRY', 'HEREWEGO', 'INITCON', 'CLUBEDIT', 'NEW_YEAR', 'CAP_SLCT', 'NEWUNIF',
                   'PLNUMSET', 'PL_EDIT', 'SEARCH', 'SPF_READ', 'SCDRF')),
    ('save_load', F('LOAD', 'EXFLAG', 'BACKUP', 'AUTOSAVE', 'CSAVE', 'CSAVE3', 'CSAVE4', 'SONGSAVE', 'VTRLOAD',
                    'FREELOAD', 'EXTRADE')),
    ('menus', F('GAME', 'OFFICE', 'ESTABLIS', 'GETREP', 'NENREP', 'MON_INST','NEWMONTH', 'INVEST', 'LOCAL', 'TOWN', 'TOWNDATA',
                'HOMETOWN', 'SPT_CLUB', 'SUPPORT', 'SPONSOR', 'SPONSOR2', 'DRAFT', 'NEWCON', 'RECON', 'FIRE', 'YOUTH',
                'ABROAD', 'WEEKLY')),
    ('meeting', F('MEETING')),
    ('news', F('NEWS_OP', 'NEWS', 'NEWS_ED')),
    ('event', F('EVENT', 'TV_EVENT', 'JSCEVENT', 'SELNAT', 'GAMEOVER', 'ENDING')),
    ('training', F('TRAINING')),
    ('help', ['FLOW_PRG/HELP.BIN', 'ATFIRST/HELP.BIN']),
    ('match_ui', F('G_INCOME', 'G_RESULT', 'BPMATCH', 'BPMWEEK', 'CHALMODE', 'CHALDANI', 'CE_VS', 'SCHE0', 'SCHE1', 'ENDOPT',
                   'COMM', 'CON_REP', 'NF_CON', 'PASS_PL', 'J1_REP', 'PL_CON')),
    ('players', ['ETC_DATA/BPINFO.BIN']),
    ('rest', []),                                     # every overlay not listed anywhere, by name
    ('dev', F('PWK_EDIT') + F(*['FLOW%d' % i for i in range(1, 12)]) + F('GMSHOW00', 'GMSHOW01', 'GMSHOW02')),
    ('browser', ['DPETC/MESSAGE.INI', '2_DP.BIN']),
    ('junk', []),                                     # filled by category (debug / binary), never by source
]
AREA_IDX = {name: i for i, (name, _) in enumerate(AREAS)}
SRC_AREA = {}
for _ai, (_an, _srcs) in enumerate(AREAS):
    for _si, _s in enumerate(_srcs):
        SRC_AREA[_s] = (_ai, _si)
REST_IDX = AREA_IDX['rest']
JUNK_IDX = AREA_IDX['junk']

CAT_ORDER = ['label', 'numunit', 'system', 'dialogue', 'meeting', 'news', 'event', 'training', 'help', 'tactic',
             'dataroom', 'place', 'name', 'browser', 'debug', 'binary']
CAT_RANK = {c: i for i, c in enumerate(CAT_ORDER)}

SYSTEM_BASES = {'LOAD', 'EXFLAG', 'BACKUP', 'AUTOSAVE', 'CSAVE', 'CSAVE3', 'CSAVE4', 'SONGSAVE', 'VTRLOAD', 'FREELOAD',
                'EXTRADE'}
EVENT_BASES = {'EVENT', 'TV_EVENT', 'JSCEVENT'}
NEWS_BASES = {'NEWS', 'NEWS_ED', 'NEWS_OP'}
ALWAYS_DEBUG_BASES = {'PWK_EDIT'}

HIRA_KATA = re.compile(r'[\u3041-\u3096\u30a1-\u30fa\u30fc]')
NAME_CHARS = r'[\u3041-\u30ff\u4e00-\u9fff\u3005\uff66-\uff9f\u30fb\uff21-\uff3a]'
NAME_RE = re.compile(r'^%s{1,6}[ \u3000]%s{1,6}$' % (NAME_CHARS, NAME_CHARS))
NAME_HW_RE = re.compile(r'^[\uff66-\uff9f][\uff66-\uff9f A-Z.]{1,11}$')
KANJI_ONLY = re.compile(r'^[\u4e00-\u9fff\u3005\u30f6]+$')
PLACE_SUFFIX = '市区郡町村県府道島'
HIRA_ONLY = re.compile(r'^[\u3041-\u3096\u30fc]{2,12}$')
NONFMT_RE = re.compile(r'#[A-Za-z0-9_]+#|@[A-Z]/|=[A-Za-z]/|\$[0-9A-Z]|<[0-9A-F]{2}>')
NUMRE = re.compile(r'[0-9\uff10-\uff19]|%[-0-9.]*[dDmM]')
JUNK_CHARS = set('曙酔糟')
SYMBOLS = re.compile(r'[\u0370-\u04ff\u2018-\u201f\u2500-\u257f]')
SANDWICH = re.compile(r'[A-Za-z\uff21-\uff3a\uff41-\uff5a][\u4e00-\u9fff]+[A-Za-z0-9\uff21-\uff5a\uff41-\uff5a]|'
                      r'[\u4e00-\u9fff][A-Za-z][\u4e00-\u9fff]')
RAWBYTES = re.compile(r'<[0-9A-F]{2}>')
NAME_FOREIGN_RE = re.compile(r'^[\uff66-\uff9f\u30fb\u30fc ]{3,16}$')
SENTENCE_END = re.compile(r'[\u3002\uff01\uff1f!?]')

# --- developer-text markers.  A skip hint is a PROMISE that the text never reaches the player, so the rules are narrow:
# "when in doubt do not skip" (an unneeded translation is cheap, a missing one ships Japanese).
_A = r'(?<![A-Za-z0-9_])'          # ASCII-only word boundaries: Japanese letters are \w for Python, so \b would not do
_Z = r'(?![A-Za-z0-9_])'
CODE_RE = re.compile('|'.join([
    _A + r'[A-Z]{2,}(?:_[A-Z0-9]+)+' + _Z,                 # GM_AI_CHC_TYPE_DF, PWK_RESULT, TEAM_MY
    _A + r'[a-z][a-z0-9]*(?:_[a-z0-9]+)+' + _Z,            # snake_case: result_view, home_team, first_backup
    _A + r'[a-z]+(?:[A-Z][a-z0-9]+)+' + _Z,                # camelCase: bcFunc, ytMes, sysGameDefencePl
    _A + r'(?:[A-Z][a-z0-9]+){2,}' + _Z,                   # PascalCase: NsMessegeGetTeamScore, LookAtBall
    _A + r'[A-Za-z_][A-Za-z0-9_]*\[(?:[0-9]+|%d)\]',       # jstat[1], rank[%d], Week[%d]
    _A + r'[A-Za-z_][A-Za-z0-9_]*\(\)',                    # plAbroadEnd()
    _A + r'PWK[A-Z0-9_]*' + _Z,                            # PWK_..., PWKHOME
]))
# identifier + ':' / '=' + printf format: a variable dump (tm:%d, team = %d, money:%d, NUM = %d), judged on the raw text
FMT_DEBUG_RE = re.compile(_A + r'(?:[a-z][A-Za-z0-9_.\[\]]{2,}|tm|pl|of|df|TEAM|NUM|FRAME|PLAYER|HOME|AWAY|Team|Num|Scene|Level|File)'
                          r'\s*[:=：]\s*[%&][-0-9.]*[dDsfxX]')
# vocabulary that only developers use (dummy, debug, dump, flag, ...); counts only when the text has no sentence content
DEV_WORD_RE = re.compile('ダミー|デバッグ|デバック|ダンプ|だがや|BootRom|TEAM_')
DEV_FLAG_RE = re.compile('フラグ')                  # "flag" counts only next to a printf value (a flag dump), see classify
SKIP_IDS_PATH = os.path.join(HERE, 'trans_skip_ids.txt')


def load_skip_ids(path=None):
    """Record ids of known extraction false positives (pointer tables / binary read as text): one id per line, '#'
    starts a comment, blank lines are ignored.  Returns a frozenset; a missing file is an empty list."""
    path = SKIP_IDS_PATH if path is None else path
    ids = set()
    if not os.path.exists(path):
        return frozenset()
    with open(path, encoding='utf-8-sig') as fh:
        for ln in fh:
            ln = re.sub(r'(^|\s)#.*$', '', ln).strip()      # record ids contain '#': a comment starts at '#' after a space
            if ln:
                ids.add(ln)
    return frozenset(ids)


def classify(ja, source, ctx, kind, fixed, orphan, denied=False):
    """-> (category, skip hint or None) for one distinct text, judged on its canonical record.
    denied: every record of the text is listed in tools/trans_skip_ids.txt (known extraction false positive)."""
    mode = T.mode_of_kind(kind)
    base = T.src_base(source)
    vis = T.strip_tokens(ja, mode)
    v = vis.replace('\n', '')
    n = len(v)
    junk_cat = 'browser' if kind in ('ini', 'ptrblob') else 'binary'
    if denied:
        return junk_cat, 'listed in tools/trans_skip_ids.txt (extraction false positive): leave as is'
    if ja.strip() == '':
        return junk_cat, 'blank (no visible text): leave as is'
    # blank apart from control tokens (e.g. '%s' + full-width space) is NOT blank: it is a layout string the player sees
    if all(ord(c) < 128 for c in ja):
        return ('browser' if kind in ('ini', 'ptrblob') else 'label'), 'ascii-only: already English, keep'
    if kind == 'bpinfo':
        return 'name', None
    if kind in ('ini', 'ptrblob'):
        if kind == 'ptrblob':
            if 'u+' in v and not HIRA_KATA.search(v):
                return 'binary', 'binary junk read as text: leave as is'
            if n == 1 and HIRA_KATA.search(v):
                return 'browser', 'single kana (IME table cell): leave as is'
        return 'browser', None
    tbl = T.tbl_size(ctx)
    vs = v.strip().lstrip('>').strip()
    # --- shapes that identify table entries
    if (orphan or tbl or 'stride-table' in ctx) and 2 <= n <= 12 and (NAME_RE.match(v.strip()) or NAME_HW_RE.match(v.strip())):
        return 'name', None
    if fixed and (orphan or 'stride-table' in ctx) and 2 <= n <= 9 and ' ' in v.strip() and not HIRA_KATA.search(v):
        return 'name', None
    if (orphan or tbl) and NAME_FOREIGN_RE.match(v.strip()):
        return 'name', None
    if base == 'PLNUMSET' and HIRA_ONLY.match(vs):
        return 'name', None            # hiragana readings of surnames / given names (nickname selection)
    one_line = '\n' not in ja
    muni_tbl = 1250 <= tbl <= 1300            # the 1270-entry municipality table that most overlays carry
    if one_line and KANJI_ONLY.match(vs) and 2 <= len(vs) <= 7 and (vs[-1] in PLACE_SUFFIX or muni_tbl):
        return 'place', None
    if base == 'HOMETOWN' and HIRA_ONLY.match(vs):
        return 'place', None
    if one_line and muni_tbl and KANJI_ONLY.match(vs) and len(vs) <= 4:
        return 'place', None
    # --- junk
    if not HIRA_KATA.search(v):
        if any(c in JUNK_CHARS for c in v) and n <= 16:
            return 'binary', 'binary junk read as text: leave as is'
        if SYMBOLS.search(v):
            return 'binary', 'binary junk read as text: leave as is'
        if n <= 10 and ' ' not in v and SANDWICH.search(v):
            return 'binary', 'binary junk read as text: leave as is'
        if len(RAWBYTES.findall(ja)) >= 2:
            return 'binary', 'binary junk read as text: leave as is'
    # developer text.  Narrow on purpose: a Latin word, a colon, a "test" or a "dummy" is NOT enough (BESTPLAYERS MATCH,
    # Dreamcast, REPEAT/END, http://..., "test sale" shop dialogue are all player-visible).  Only
    #  * a code identifier (snake_case, camelCase, PascalCase, NAME_WITH_UNDERSCORES, arr[3], f(), PWK...) -- never
    #    in HELP text, or
    #  * with no sentence content at all: a variable dump (tm:%d), developer vocabulary (dummy, debug, dump, flag), or a
    #    PWK_EDIT screen label.
    sentence = SENTENCE_END.search(v)
    if (CODE_RE.search(v) and base not in ('HELP', 'ATFIRST/HELP')) \
            or (not sentence and (FMT_DEBUG_RE.search(ja) or DEV_WORD_RE.search(ja) or base in ALWAYS_DEBUG_BASES
                                  or (DEV_FLAG_RE.search(ja) and T.PRINTF_RE.search(ja)))):
        return 'debug', 'debug/developer text: optional, lowest priority'
    if base in NEWS_BASES and n >= 6 and '#tk' in ja:
        return 'news', None                # headline strings: "#tk21#..." (short, token-led)
    if n < 12 and NUMRE.search(NONFMT_RE.sub('', ja)) and not SENTENCE_END.search(v):
        return 'numunit', None
    prose = n >= 12 or (n >= 10 and '\n' in ja)
    if base == 'HELP' or base == 'ATFIRST/HELP':
        return ('help' if n >= 8 else 'label'), None
    if base == 'TRAINING' and fixed and n >= 6:
        return 'tactic', None
    if prose:
        if base in SYSTEM_BASES:
            return 'system', None
        if base == 'MEETING':
            return 'meeting', None
        if base in NEWS_BASES:
            return 'news', None
        if base in EVENT_BASES:
            return 'event', None
        if base == 'TRAINING':
            return 'training', None
        if base.startswith('DRS') or base == 'DATAROOM':
            return 'dataroom', None
        return 'dialogue', None
    if SENTENCE_END.search(v) and n >= 5:
        return ('system' if base in SYSTEM_BASES else 'dialogue'), None
    if base.startswith('DRS') or base == 'DATAROOM':
        return 'dataroom', None
    return 'label', None


GUIDANCE = {
    'label': 'UI labels and menu entries. Space ladder (style-guide s3): full wording, standard short form, drop filler, '
             'shortest noun. Same Japanese -> same English everywhere. Keep leading/trailing alignment spaces if the Japanese has them.',
    'numunit': 'Numbers with units / counters ("3人", "%d位", "%d週"). Digits in tables; keep every format token in order. '
               'Full-width digits become ASCII.',
    'system': 'System messages (save/load/memory card/VM). Plain, polite, short. "VM" stays "VM"; keep the line structure.',
    'dialogue': 'Spoken or window text. Staff are polite and warm, players keep their voice (gruff / nervous / composed). '
                'Aim at about 0.85 x natural English (about 1.0-1.05 x the Japanese bytes); break lines yourself at word '
                'boundaries, never more lines than the Japanese, max 39 cells per line.',
    'meeting': 'Meeting-room dialogue (players, staff, supporters speak). Keep each speaker\'s voice; two short lines usually; '
               'aim at about 0.85 x natural English; max 39 cells per line, never more lines than the Japanese.',
    'news': 'News / headline text. Newsreader tone, concise; keep #tkNN# and @Y/..@ spans; about 0.85 x natural; max 39 cells.',
    'event': 'Event dialogue and event-script strings. Same voice rules as dialogue; developer lines (": %d") are debug.',
    'training': 'Training screen text: explanations of drills, results, formations. Short imperative English.',
    'tactic': 'Training tactic / formation instruction texts in fixed in-place slots (no relocation possible): write AT '
              'budget_fixed-1 characters or fewer. Terse English.',
    'help': 'HELP.BIN: the most visible long text. Friendly instructional English, one idea per sentence, headings in '
            '@Y/..@ stay; max 39 cells per line, never more lines than the Japanese, about 0.85 x natural.',
    'dataroom': 'Data room / record screens (rankings, records, history). Terse labels; keep every format token in order.',
    'place': 'Municipalities, prefectures, regions, old provinces (Hepburn, no macrons). Drop City/Pref. suffix; keep '
             '-gun/-cho/-mura only when needed to tell same-name places apart or when it fits budget_fixed-1. '
             'Hiragana readings become lower-case romaji. Fictional places: phonetic.',
    'name': 'Person names (players, staff): Given Family order, Hepburn, no macrons. Fixed 14-byte fields hold 13 characters: '
            'ladder "Given Family" -> "G. Family" -> "Family". Foreign players: the usual English spelling; half-width kana '
            'names are foreign: transliterate phonetically. Same name -> same English.',
    'browser': 'Dream Passport network browser UI (dead service, lowest priority). Keep HTML tags (<br> <font ..>) and %s %d exactly; '
               'MESSAGE.INI values are one line (no newline).',
    'debug': 'Debug / developer strings: never shown to players. Optional (empty en is accepted); if translated keep every format token.',
    'binary': 'Binary data misread as text, blank or untranslatable: leave empty.',
}


# ------------------------------------------------------------------ planning ----

class Agg:
    __slots__ = ('ja', 'ids', 'fixed_min', 'all_min', 'kinds', 'canon', 'srcs', 'locs')

    def __init__(self, ja):
        self.ja = ja
        self.ids = []
        self.fixed_min = None
        self.all_min = None
        self.kinds = set()
        self.canon = None            # (rank tuple, fi, li)
        self.srcs = set()
        self.locs = []               # (source, ctx) of every record: the window class is judged per record


def source_rank(source):
    """(area index, position in the area, name) - a total order over sources, ints and strings never mixed."""
    r = SRC_AREA.get(source)
    if r is not None:
        return (r[0], r[1], '')
    area = REST_IDX if T.record_kind(source) == 'overlay' else AREA_IDX['browser']
    return (area, 1000000, source)


def aggregate(db):
    """-> OrderedDict ja -> Agg in first-seen file order (deterministic)."""
    aggs = collections.OrderedDict()
    for fi, li, r in db.records():
        ja = r['ja']
        a = aggs.get(ja)
        if a is None:
            a = aggs[ja] = Agg(ja)
        src = T.source_of(r['id'])
        a.ids.append(r['id'])
        a.srcs.add(src)
        a.locs.append((src, r.get('ctx') or ''))
        a.kinds.add(T.record_kind(src))
        mb = r.get('max_bytes')
        if mb is not None:
            if a.all_min is None or mb < a.all_min:
                a.all_min = mb
            if T.is_fixed(r) and (a.fixed_min is None or mb < a.fixed_min):
                a.fixed_min = mb
        rank = source_rank(src) + (li,)
        if a.canon is None or (rank, fi) < (a.canon[0], a.canon[1]):
            a.canon = (rank, fi, li)
    return aggs


def item_kind(a):
    if a.kinds == {'ini'}:
        return 'ini'
    for k in ('overlay', 'bpinfo', 'ptrblob'):
        if k in a.kinds:
            return k
    return 'ini'


def build_items(db, aggs=None, skip_ids=None):
    """-> list of plan items (dicts, internal fields prefixed '_') in plan order.
    skip_ids: set of record ids (tools/trans_skip_ids.txt) that are known extraction false positives; a text is
    skip-hinted from this list only when EVERY record of the text is listed.  None = the repository's default list."""
    aggs = aggs or aggregate(db)
    if skip_ids is None:
        skip_ids = load_skip_ids()
    items = []
    for ja, a in aggs.items():
        rank, fi, li = a.canon
        f = db.files[fi]
        rec = f.recs[li]
        source = T.source_of(rec['id'])
        kind = item_kind(a)
        mode = T.mode_of_kind(kind)
        ctx = rec.get('ctx') or ''
        fixed = T.is_fixed(rec)
        denied = bool(skip_ids) and all(i in skip_ids for i in a.ids)
        cat, skip = classify(ja, source, ctx, kind, fixed, bool(rec.get('orphan')), denied)
        prev = f.recs[li - 1]['ja'] if li > 0 else ''
        nxt = f.recs[li + 1]['ja'] if li + 1 < len(f.recs) else ''
        jb = T.jp_bytes(ja) + 1
        bf = a.fixed_min
        item = collections.OrderedDict([
            ('key', T.key_of(ja)), ('ja', ja), ('ids_count', len(a.ids)),
            ('budget_fixed', bf), ('budget_min', a.all_min),
            ('tokens', T.tokens_of(ja, mode)), ('lines', T.line_count(ja)),
            ('ctx', ctx), ('prev', prev[:60]), ('next', nxt[:60]),
            ('skip', skip), ('kind', kind), ('id0', rec['id']),
            ('soft_max_bytes', None if (bf is not None or kind == 'ini') else int(T.SOFT_RATIO * jb)),
            ('max_chars_fixed', None if bf is None else bf - 1),
        ])
        # window class (tools/winwidth.py): strictest limit over the records of this text; null max_cells = no cell rule
        wl = WW.merge_limits([WW.limits(ja, cat, s, c) for s, c in a.locs])
        item['max_cells'] = wl.max_cells
        item['max_rows'] = wl.max_rows
        item['wclass'] = wl.cls
        area = JUNK_IDX if (cat in ('debug', 'binary') or skip) else rank[0]
        item['_cat'] = cat
        item['_area'] = area
        item['_order'] = (area, CAT_RANK[cat], rank[1], rank[2], rank[3])
        item['_srcs'] = len(a.srcs)
        item['_src'] = source
        item['_records'] = len(a.ids)
        item['_chars'] = len(ja)
        items.append(item)
    items.sort(key=lambda it: (it['_order'], it['key']))
    return items


def chunk(group):
    """Cut an ordered list of items (one area+category) into shard-sized pieces."""
    pieces, cur, chars = [], [], 0
    for it in group:
        cur.append(it)
        chars += it['_chars']
        if len(cur) >= SHARD_TARGET or (len(cur) >= 10 and chars >= SHARD_CHAR_CAP):
            pieces.append(cur)
            cur, chars = [], 0
    if cur:
        if pieces and len(cur) < 40 and len(pieces[-1]) + len(cur) <= SHARD_MAX \
                and sum(i['_chars'] for i in pieces[-1] + cur) <= SHARD_CHAR_CAP * 1.25:
            pieces[-1].extend(cur)
        else:
            pieces.append(cur)
    return pieces


def build_shards(items):
    shards = []
    groups = collections.OrderedDict()
    for it in items:
        groups.setdefault((it['_area'], it['_cat']), []).append(it)
    for (area, cat), grp in groups.items():
        for piece in chunk(grp):
            srcs = collections.Counter(T.src_base(i['_src']) for i in piece)
            main = srcs.most_common(1)[0][0] if len(srcs) == 1 else '+'.join(
                s for s, _ in sorted(srcs.items(), key=lambda kv: (-kv[1], kv[0]))[:3]) + ('+' if len(srcs) > 3 else '')
            shards.append({'shard': len(shards) + 1, 'category': cat, 'area': AREAS[area][0], 'source': main,
                           'sources': sorted(srcs), 'guidance': GUIDANCE[cat], 'items': piece})
    return shards


def public_item(it):
    return collections.OrderedDict((k, v) for k, v in it.items() if not k.startswith('_'))


def shard_json(sh):
    head = collections.OrderedDict([('shard', sh['shard']), ('category', sh['category']), ('area', sh['area']),
                                    ('source', sh['source']), ('sources', sh['sources']), ('guidance', sh['guidance']),
                                    ('n_items', len(sh['items']))])
    h = json.dumps(head, ensure_ascii=False)[:-1]
    body = ',\n'.join(json.dumps(public_item(i), ensure_ascii=False) for i in sh['items'])
    return h + ', "items": [\n' + body + '\n]}\n'


def summary_md(db, aggs, items, shards, seconds):
    nrec = db.count()
    out = []
    out.append('# Translation plan summary\n')
    out.append('Generated by `tools/transwork.py plan` (deterministic; `en` fields are ignored).\n')
    out.append('* records: %d in %d files; distinct Japanese texts: %d; shards: %d (target %d texts, max %d, %d JP chars)' % (
        nrec, len(db.files), len(items), len(shards), SHARD_TARGET, SHARD_MAX, SHARD_CHAR_CAP))
    nfix = sum(1 for i in items if i['budget_fixed'] is not None)
    nini = sum(1 for i in items if i['kind'] == 'ini')
    out.append('* texts with a fixed in-place slot (budget_fixed): %d; unlimited (MESSAGE.INI only): %d; movable only: %d' % (
        nfix, nini, len(items) - nfix - nini))
    nskip = sum(1 for i in items if i['skip'])
    out.append('* skip-hinted texts: %d (audit list: build/trans/skip_report.tsv)\n' % nskip)
    by_cat = collections.OrderedDict((c, [0, 0, 0, 0, 0, 0]) for c in CAT_ORDER)   # texts, records, skip, shards, fixed, chars
    for i in items:
        r = by_cat[i['_cat']]
        r[0] += 1
        r[1] += i['_records']
        r[2] += 1 if i['skip'] else 0
        r[4] += 1 if i['budget_fixed'] is not None else 0
        r[5] += i['_chars']
    for sh in shards:
        by_cat[sh['category']][3] += 1
    out.append('## Per category\n')
    out.append('| category | distinct texts | records | skip-hinted | with fixed slot | JP chars | shards |')
    out.append('|---|---:|---:|---:|---:|---:|---:|')
    tot = [0] * 6
    for c, r in by_cat.items():
        if r[0] == 0:
            continue
        out.append('| %s | %d | %d | %d | %d | %d | %d |' % (c, r[0], r[1], r[2], r[4], r[5], r[3]))
        tot = [x + y for x, y in zip(tot, r)]
    out.append('| **total** | %d | %d | %d | %d | %d | %d |\n' % (tot[0], tot[1], tot[2], tot[4], tot[5], tot[3]))
    out.append('## Per area (player order)\n')
    out.append('| area | first shard | last shard | shards | distinct texts | categories |')
    out.append('|---|---:|---:|---:|---:|---|')
    by_area = collections.OrderedDict()
    for sh in shards:
        by_area.setdefault(sh['area'], []).append(sh)
    for a, shs in by_area.items():
        cats = collections.Counter()
        for s in shs:
            cats[s['category']] += len(s['items'])
        out.append('| %s | %d | %d | %d | %d | %s |' % (a, shs[0]['shard'], shs[-1]['shard'], len(shs),
                                                       sum(len(s['items']) for s in shs),
                                                       ', '.join('%s %d' % kv for kv in cats.items())))
    out.append('\n## Canonical source of the distinct texts (top 25)\n')
    srcs = collections.Counter(i['_src'] for i in items)
    out.append('| source | distinct texts first seen here |')
    out.append('|---|---:|')
    for s, n in sorted(srcs.items(), key=lambda kv: (-kv[1], kv[0]))[:25]:
        out.append('| %s | %d |' % (s, n))
    sizes = [len(s['items']) for s in shards]
    out.append('\n## Shard sizes\n')
    out.append('min %d, median %d, max %d texts; %d shards have fewer than 100 texts (small categories or JP-character cap).' % (
        min(sizes), sorted(sizes)[len(sizes) // 2], max(sizes), sum(1 for s in sizes if s < 100)))
    out.append('\nplan time %.1f s' % seconds)
    return '\n'.join(out) + '\n'


def cmd_plan(a):
    t0 = time.time()
    db = T.load_db(os.path.join(T.ROOT, a.tdb) if not os.path.isabs(a.tdb) else a.tdb)
    aggs = aggregate(db)
    if a.skip_ids is None:
        skip_ids = load_skip_ids()
    elif a.skip_ids.lower() == 'none':
        skip_ids = frozenset()
    else:
        sp = T.resolve_path(a.skip_ids)
        if not os.path.exists(sp):
            raise SystemExit('transwork: --skip-ids file %s not found' % sp)
        skip_ids = load_skip_ids(sp)
    items = build_items(db, aggs, skip_ids)
    known = {i for ag in aggs.values() for i in ag.ids}
    stale_ids = sorted(skip_ids - known)
    keys = {}
    for it in items:
        if it['key'] in keys:
            raise SystemExit('key collision %s: %r / %r' % (it['key'], keys[it['key']], it['ja']))
        keys[it['key']] = it['ja']
    shards = build_shards(items)
    out = a.out if os.path.isabs(a.out) else os.path.join(T.ROOT, a.out)
    sdir = os.path.join(out, 'shards')
    os.makedirs(sdir, exist_ok=True)
    wanted = set()
    for sh in shards:
        name = '%04d.json' % sh['shard']
        wanted.add(name)
        T.write_atomic(os.path.join(sdir, name), shard_json(sh))
    for fn in os.listdir(sdir):
        if fn.endswith('.json') and fn not in wanted:
            os.remove(os.path.join(sdir, fn))
    index = [collections.OrderedDict([('shard', s['shard']), ('category', s['category']), ('area', s['area']),
                                      ('source', s['source']), ('n_items', len(s['items'])),
                                      ('n_skip', sum(1 for i in s['items'] if i['skip'])),
                                      ('file', 'shards/%04d.json' % s['shard'])]) for s in shards]
    T.write_atomic(os.path.join(out, 'index.json'), json.dumps(index, ensure_ascii=False, indent=0) + '\n')
    rows = ['key\tcategory\tskip\tsource\tja']
    for i in items:
        if i['skip']:
            rows.append('%s\t%s\t%s\t%s\t%s' % (i['key'], i['_cat'], i['skip'], i['_src'], i['ja'].replace('\n', '\\n').replace('\t', ' ')))
    T.write_atomic(os.path.join(out, 'skip_report.tsv'), '\n'.join(rows) + '\n')
    secs = time.time() - t0
    T.write_atomic(os.path.join(out, 'plan_summary.md'), summary_md(db, aggs, items, shards, secs))
    if not a.quiet:
        print('plan: %d records, %d distinct texts, %d shards (%d skip-hinted texts) in %.1f s -> %s' % (
            db.count(), len(items), len(shards), sum(1 for i in items if i["skip"]), secs, os.path.normpath(out)))
        print('skip-ids: %d ids listed, %d texts hinted from the list, %d listed ids not in this database%s' % (
            len(skip_ids), sum(1 for i in items if i['skip'] and i['skip'].startswith('listed in')), len(stale_ids),
            (' (' + ', '.join(stale_ids[:5]) + (', ...' if len(stale_ids) > 5 else '') + ')') if stale_ids else ''))
    return 0


# ----------------------------------------------------------------- helpers ----

RULE4_CELLS = """ 4. Width: every ASCII character is one cell; at most item.max_cells cells per line (39 in the 20-cell window, 33 in a speech
    bubble; token widths: #sname#/#tkNN# 10, #chi# etc. 8, %s 8, %d 3, %D 6, %m 8, $N 6; colour/window tokens 0). The game has
    no word wrap at the window edge: a longer line is cut in the middle of a word. Insert \\n yourself at word boundaries. Never
    more lines than item.lines (and never more than item.max_rows). A line that is exactly max_cells wide must not end in . , ! ?.
    No leading/trailing spaces unless the Japanese has them.
"""


def rule4_pixels(profile=PX.DEFAULT_PROFILE):
    """Rule 4 of the translator prompt in pixel mode (docs/pixel-widths.md): the advance table of `profile` replaces 'one cell'."""
    t = PX.get_table(profile)
    by = collections.OrderedDict()
    for b in range(0x20, 0x7F):
        by.setdefault(t[b], []).append('space' if b == 0x20 else chr(b))
    adv = '; '.join('%d px: %s' % (px, ' '.join(by[px])) for px in sorted(by))
    return (""" 4. Width in PIXELS (proportional font): a line fits when the pen start of its LAST glyph is at most 12*(item.max_cells-1) px
    (item.max_px = 12*max_cells = 396 in a speech bubble, 468 in the 20-cell window is the nominal line length; the last glyph may
    end 1 px beyond it). Advances: """ + adv + """. Digits are 12 px. Names and numbers are charged at
    their worst case: #sname#/#tkNN# 10 glyphs x 13 px, #chi# etc. 8 x 13, %s 8 x 13, $N 6 x 13; %d 3, %D 6, %m 8 digits x 12 px;
    colour/window tokens 0 px. The game has no word wrap at the window edge: a longer line is cut in the middle of a word. Insert
    \\n yourself at word boundaries (python -I -X utf8 tools/winwidth.py wrap TEXT CELLS --width-mode pixels proposes breaks).
    Never more lines than item.lines (and never more than item.max_rows). No leading/trailing spaces unless the Japanese has them.
""")


PROMPT = """You are a translator for the English patch of "J.League Pro Soccer Club o Tsukurou! Special Edition 2" (Sakatsuku
Tokudaigou 2, Dreamcast, 1999-2000). Translate the Japanese texts of ONE shard into British English.

INPUT: shard file {path} (JSON, shown below). Each item: key, ja (Japanese; \\n = line break), ids_count (how many places use
the text), budget_fixed (hard limit in bytes incl. the NUL, or null), max_chars_fixed (= budget_fixed - 1 characters),
soft_max_bytes (length target for movable text, bytes incl. NUL), tokens (control tokens that must be kept),
lines (maximum line count), max_cells / max_rows (the text window's width in cells and its rows, see rule 4), wclass,
ctx / prev / next (neighbouring Japanese for context), skip (hint, see below).

OUTPUT: write {out} as JSON  {{"shard": {shard}, "results": [{{"key": "...", "en": "..."}}, ...]}}  with one entry for every
item that has no skip hint (items with a skip hint may be omitted or returned with "en": ""). Optional "note" fields are ignored.
Then run:  python -I -X utf8 tools/transcheck.py {out}   and repair every ERROR it reports (fix means rewriting the string).

HARD RULES (a violation is rejected by transcheck):
 1. ASCII only (0x20-0x7E) plus \\n. No curly quotes, dashes, accents, bullets. Never use backslash or tilde.
 2. Never type @ = # or a lone % yourself. Keep every control token of the Japanese exactly (same multiset):
    @Y/..@ (colour spans), =K/..= (window style), #sname# #tk00# #chi# #ken# #kyu# #to#, %s %d %2d %D %m, $1.., <XX>.
    Move a token only to follow the words it colours. %s/%d/%m formats stay in the Japanese ORDER. Fixed-width digits become ASCII.
 3. Byte budget: len(en) + 1 <= budget_fixed (so at most max_chars_fixed characters) when budget_fixed is set.
{rule4} 5. Same Japanese -> same English everywhere (the key says it is one text). Follow docs/style-guide.md and translation/glossary.tsv.

STYLE (docs/style-guide.md): British English, football/match/pitch/kit, Owner = the player, drop honorifics, staff polite and warm,
players keep their voice, one "!" is enough, "..." for the ellipsis. Prose targets about 0.85 x natural English length
(soft_max_bytes); names use the ladder "Given Family" -> "G. Family" -> "Family"; places drop City/Pref.; tactic texts
must fit max_chars_fixed.

SKIP HINTS: an item with "skip" set is debug text, binary junk read as text, blank, or already English: leave it out, or return
"en": "" (or the Japanese itself unchanged). Translate it only if it is clearly player-visible text.

CATEGORY GUIDANCE ({category}): {guidance}

SHARD {shard} ({category}, area {area}, source {source}, {n} items):
"""


def cmd_prompt(a):
    p = os.path.join(a.shards, '%04d.json' % a.n)
    with open(p, encoding='utf-8') as fh:
        raw = fh.read()
    sh = json.loads(raw)
    out_path = 'build/trans/results/%04d.json' % a.n
    rule4 = RULE4_CELLS
    if getattr(a, 'width_mode', 'cells') == 'pixels':
        # pixel mode: rule 4 speaks pixels and every item carries max_px (12 * max_cells, the nominal line length)
        rule4 = rule4_pixels(a.px_profile)
        for it in sh['items']:
            if it.get('max_cells') is not None:
                it['max_px'] = PX.limit_px(it['max_cells'])
        raw = shard_json(sh)
    sys.stdout.write(PROMPT.format(path='build/trans/shards/%04d.json' % a.n, out=out_path, shard=sh['shard'],
                                   category=sh['category'], guidance=sh['guidance'], area=sh['area'],
                                   source=sh['source'], n=sh['n_items'], rule4=rule4))
    sys.stdout.write(raw)
    return 0


def cmd_ids(a):
    db = T.load_db(os.path.join(T.ROOT, a.tdb) if not os.path.isabs(a.tdb) else a.tdb)
    n = 0
    for _, _, r in db.records():
        if T.key_of(r['ja']) == a.key:
            print('%s\tmax_bytes=%s\t%s' % (r['id'], r.get('max_bytes'), r.get('ctx')))
            n += 1
    if not n:
        print('no record with key %s' % a.key, file=sys.stderr)
        return 1
    return 0


def cmd_show(a):
    p = os.path.join(a.shards, '%04d.json' % a.n)
    with open(p, encoding='utf-8') as fh:
        sh = json.load(fh)
    print('shard %d  %s / %s / %s  %d items' % (sh['shard'], sh['category'], sh['area'], sh['source'], sh['n_items']))
    px = getattr(a, 'width_mode', 'cells') == 'pixels'
    for it in sh['items']:
        print('%s fx=%s mn=%s l=%d w=%s %s%s | %s' % (it['key'], it['budget_fixed'], it['budget_min'], it['lines'],
                                                 PX.limit_px(it['max_cells']) if px and it.get('max_cells') is not None else it.get('max_cells'),
                                                 '[skip] ' if it['skip'] else '', it['ja'].replace('\n', '\\n')[:70],
                                                 ' '.join(it['tokens'])))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--tdb', default='translation')
    p.add_argument('--out', default='build/trans')
    p.add_argument('--skip-ids', metavar='FILE', help='list of record ids that are extraction false positives '
                   '(default tools/trans_skip_ids.txt; "none" = no list)')
    p.add_argument('--quiet', action='store_true')
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser('prompt')
    p.add_argument('n', type=int)
    p.add_argument('--shards', default=T.SHARD_DIR)
    p.add_argument('--width-mode', choices=['cells', 'pixels'], default='cells')
    p.add_argument('--px-profile', choices=PX.PROFILES, default=PX.DEFAULT_PROFILE)
    p.set_defaults(fn=cmd_prompt)
    p = sub.add_parser('ids')
    p.add_argument('key')
    p.add_argument('--tdb', default='translation')
    p.set_defaults(fn=cmd_ids)
    p = sub.add_parser('show')
    p.add_argument('n', type=int)
    p.add_argument('--shards', default=T.SHARD_DIR)
    p.add_argument('--width-mode', choices=['cells', 'pixels'], default='cells')
    p.set_defaults(fn=cmd_show)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
