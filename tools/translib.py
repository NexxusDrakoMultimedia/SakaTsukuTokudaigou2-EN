"""translib: shared primitives of the translation work tools (transwork / transcheck / transmerge).

Pure stdlib, deterministic.  Run the tools with  python -I -X utf8 tools/<tool>.py.

  * DB loading that keeps the raw jsonl lines (so a merge touches only the lines it changes)
  * item key of a distinct Japanese text (sha1 of the utf-8 text, 12 hex digits)
  * control-token grammar (game text and browser/HTML text) and on-screen width model
  * fixed / movable classification of a record (docs/capacity-design.md: fixed = orphan,
    stride-table, interior-ptrs, BPINFO, 2_DP.BIN; movable = pointer-referenced overlay text)

The width model is docs/capacity-ratio.md section 7 / tools/re/capacity/ratio/build_sample.py:
every ASCII character is one 12-px cell, the default window is 39 cells wide, colour/window tokens
and raw <XX> bytes take no width, substitution tokens expand to assumed widths.
"""
import glob
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_TDB = os.path.join(ROOT, 'translation')
TRANS_DIR = os.path.join(ROOT, 'build', 'trans')
SHARD_DIR = os.path.join(TRANS_DIR, 'shards')
RESULT_DIR = os.path.join(TRANS_DIR, 'results')
BACKUP_DIR = os.path.join(TRANS_DIR, 'backup')

MAX_CELLS = 39            # default dialogue window: 20 cells = 39 half-width characters per line
SOFT_RATIO = 1.05         # movable text: warn above 1.05 x the Japanese byte size (L4 discipline)


# ------------------------------------------------------------------ keys ----

def key_of(ja):
    """Stable item key of a distinct Japanese text."""
    return hashlib.sha1(ja.encode('utf-8')).hexdigest()[:12]


def source_of(rid):
    """'FLOW_PRG/X.BIN#3f204' -> 'FLOW_PRG/X.BIN'."""
    return rid.rsplit('#', 1)[0]


def src_base(source):
    """'FLOW_PRG/MEETING.BIN' -> 'MEETING', 'ATFIRST/TITLE.BIN' -> 'ATFIRST/TITLE', '2_DP.BIN' -> '2_DP'."""
    s = source
    if s.startswith('FLOW_PRG/'):
        s = s[len('FLOW_PRG/'):]
    for suf in ('.BIN', '.INI'):
        if s.endswith(suf):
            s = s[:-len(suf)]
    return s


# -------------------------------------------------------------------- DB ----

class DbFile:
    __slots__ = ('name', 'path', 'lines', 'recs', 'compact', 'plain')

    def __init__(self, name, path, lines, recs, compact, plain=True):
        self.name = name          # 'FLOW_PRG__MEETING.BIN'
        self.path = path
        self.lines = lines        # raw lines (no trailing newline) of the non-blank lines
        self.recs = recs          # parsed record per line
        self.compact = compact    # True: separators (',', ':')  False: json default (', ', ': ')
        self.plain = plain        # False: blank lines / CRLF / missing final newline: a merge refuses to rewrite it


class Db:
    def __init__(self, tdb, files):
        self.tdb = tdb
        self.files = files

    def records(self):
        for fi, f in enumerate(self.files):
            for li, r in enumerate(f.recs):
                yield fi, li, r

    def count(self):
        return sum(len(f.recs) for f in self.files)


def load_db(tdb=None):
    tdb = tdb or DEFAULT_TDB
    files = []
    for p in sorted(glob.glob(os.path.join(tdb, '*.jsonl'))):
        with open(p, encoding='utf-8', newline='') as fh:
            text = fh.read()
        raw = text.split('\n')
        plain = text.endswith('\n') or text == ''
        if raw and raw[-1] == '':
            raw.pop()
        lines, recs = [], []
        compact = True
        for ln in raw:
            if not ln.strip():
                plain = False
                continue
            if ln.endswith('\r'):
                plain = False
            lines.append(ln)
            recs.append(json.loads(ln))
        if lines:
            compact = lines[0].startswith('{"id":"')
        files.append(DbFile(os.path.basename(p)[:-len('.jsonl')], p, lines, recs, compact, plain))
    return Db(tdb, files)


def dump_record(rec, compact):
    if compact:
        return json.dumps(rec, ensure_ascii=False, separators=(',', ':'))
    return json.dumps(rec, ensure_ascii=False)


def line_is_compact(line):
    """True when a raw jsonl line was written with the compact separators (',', ':')."""
    return line.startswith('{"id":"')


def normalise_styles(f):
    """Re-serialise every line of DbFile `f` whose separator style differs from the file style (f.compact), in place.
    A file can end up mixed when some other writer (textdb.write_jsonl is compact, textfmt_common.write_jsonl is spaced)
    rewrote single records; the merge writer heals that whenever it rewrites a file, so that
    dump_record(rec, f.compact) == line holds for every line.  Returns the number of lines changed (records untouched)."""
    n = 0
    for li, ln in enumerate(f.lines):
        if line_is_compact(ln) != f.compact:
            f.lines[li] = dump_record(f.recs[li], f.compact)
            n += 1
    return n


def write_atomic(path, text):
    """Write utf-8 text with LF endings: temp file in the same directory, then os.replace.
    On any failure (unencodable text, full disk, ...) the temp file is removed and the old file is untouched."""
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def resolve_path(p):
    """One path rule for every path argument of the translation tools (result files, --tdb, --shards,
    --shard-file, --backup-dir, --rejects-dir, --lock-file): an absolute path is used as is; a relative path
    is looked for in the current directory FIRST, then under the repository root; when it exists in neither
    place (an output that will be created) it is taken relative to the current directory."""
    if os.path.isabs(p):
        return os.path.normpath(p)
    here = os.path.abspath(p)
    if os.path.exists(here):
        return here
    there = os.path.normpath(os.path.join(ROOT, p))
    if os.path.exists(there):
        return there
    return here


# ------------------------------------------------------- record classes ----

def record_kind(source):
    if source == 'DPETC/MESSAGE.INI':
        return 'ini'
    if source.endswith('BPINFO.BIN'):
        return 'bpinfo'
    if source in ('2_DP.BIN', '1ST_READ.BIN'):
        return 'ptrblob'
    return 'overlay'


def is_fixed(rec):
    """True when the string can only be overwritten in place (docs/capacity-design.md, section 1).
    INI text has no limit at all (file is rebuilt); the other non-overlay sources are in place."""
    kind = record_kind(source_of(rec['id']))
    if kind == 'ini':
        return False
    if kind in ('bpinfo', 'ptrblob'):
        return True
    ctx = rec.get('ctx') or ''
    return bool(rec.get('orphan')) or not rec.get('refs') or 'stride-table' in ctx or 'interior-ptrs' in ctx


def tbl_size(ctx):
    """'tbl@23668[3/1150]' -> 1150 (pointer table length), else 0."""
    m = re.search(r'\[(\d+)/(\d+)\]', ctx or '')
    return int(m.group(2)) if m else 0


# ---------------------------------------------------------------- tokens ----

# game text: colour @Y/..@, window =K/..=, #name# substitutions, printf formats, $N, raw <XX>
GAME_TOKEN_RE = re.compile(r'%%|%[-0-9.]*[sdDmMfxX]|@[A-Z]/|@|=[A-Za-z]/|=|#[A-Za-z0-9_]+#|\$[0-9A-Z]|<[0-9A-F]{2}>')
# browser text (MESSAGE.INI, 2_DP.BIN): HTML tags and entities, printf formats
BROWSER_TOKEN_RE = re.compile(r'%%|%[-0-9.]*[sdDmfxX]|<[^<>]*>|&[#A-Za-z0-9]+;')
PRINTF_RE = re.compile(r'%[-0-9.]*[sdDmMfxX]')

GAME_STRAY = '@=#%'
BROWSER_STRAY = '%'

WIDTH_SUBST = (          # (regex, assumed cells) - docs/capacity-ratio.md section 7
    (re.compile(r'#(?:sname|tk\d\d)#'), 10),
    (re.compile(r'#[A-Za-z0-9_]+#'), 8),
    (re.compile(r'\$[0-9A-Z]'), 6),
)


def mode_of_kind(kind):
    return 'browser' if kind in ('ini', 'ptrblob') else 'game'


def token_re(mode):
    return BROWSER_TOKEN_RE if mode == 'browser' else GAME_TOKEN_RE


def canon_tokens(tokens):
    """`%M` (compact money, tools/moneypatch.py COMPACT_FLAG) is the same format as `%m` for the Japanese-vs-English token comparison."""
    return ['%m' if t == '%M' else t for t in tokens]


def tokens_of(s, mode='game'):
    """Ordered list of control tokens in s."""
    return token_re(mode).findall(s)


def strip_tokens(s, mode='game'):
    return token_re(mode).sub('', s)


def _fmt_cells(tok):
    m = re.match(r'%(-?)([0-9]*)(?:\.[0-9]+)?([sdDmMfxX])', tok)
    if not m:
        return 1 if tok == '%%' else 0
    n = int(m.group(2) or 0)
    base = {'s': 8, 'd': 3, 'D': 6, 'm': 15, 'M': 12, 'f': 6, 'x': 4, 'X': 4}[m.group(3)]
    return max(n, base)


def cells_of_line(line, mode='game'):
    """On-screen width of one line (no newline) in half-width cells, token expansion included."""
    if mode == 'browser':
        s = BROWSER_TOKEN_RE.sub(lambda m: 'x' * _fmt_cells(m.group(0)) if m.group(0)[0] == '%' else '', line)
        return sum(_cw(c) for c in s)

    def rep(m):
        t = m.group(0)
        c = t[0]
        if c == '%':
            return 'x' * _fmt_cells(t)
        if c in '@=' or t[0] == '<':
            return ''
        for rx, w in WIDTH_SUBST:
            if rx.fullmatch(t):
                return 'x' * w
        return ''
    s = GAME_TOKEN_RE.sub(rep, line)
    return sum(_cw(c) for c in s)


def _cw(c):
    o = ord(c)
    if o < 0x80 or 0xff61 <= o <= 0xff9f:
        return 1
    return 2


def jp_bytes(ja):
    """Byte size of a Japanese text as stored (cp932; <XX> = 1 byte), WITHOUT the NUL."""
    n = 0
    pos = 0
    for m in re.finditer(r'<[0-9A-F]{2}>', ja):
        n += len(ja[pos:m.start()].encode('cp932', errors='replace'))
        n += 1
        pos = m.end()
    n += len(ja[pos:].encode('cp932', errors='replace'))
    return n


def line_count(s):
    return s.count('\n') + 1


def alternates(seq):
    """True when a token sequence strictly alternates open, close, open, ... (may end open)."""
    return all((i % 2 == 0) == is_open for i, is_open in enumerate(seq))


def pair_sequences(tokens):
    """Colour (@..) and window (=..) token kinds as open(True)/close(False) sequences."""
    col, win = [], []
    for t in tokens:
        if t[0] == '@':
            col.append(len(t) > 1)
        elif t[0] == '=':
            win.append(len(t) > 1)
    return col, win


def printf_order(tokens):
    return [t for t in tokens if PRINTF_RE.fullmatch(t)]
