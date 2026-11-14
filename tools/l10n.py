# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""l10n: the PUBLIC form of the translation (English + identifiers + hashes) and the way back to the working form.

The working form is what every other tool reads:  translation/*.jsonl  (one record per Japanese string with the Japanese
text in `ja`).  It is local and gitignored.  The committed form is  l10n/*.jsonl : the same records WITHOUT the Japanese;
each string is identified by its record id ("FILE#hexoffset", which also names the file and the place) and by `jah`, the
first 16 bytes (32 hex digits) of the SHA-256 of the RAW Shift-JIS (cp932) bytes of the string as they are on the disc.
`import` reads those bytes out of the player's own disc, checks every hash and fills `ja` back in.  The format is specified in
docs/l10n-format.md.

    python -I -X utf8 tools/l10n.py export [--tdb translation] [--out l10n] [--only SUBSTR ..]
    python -I -X utf8 tools/l10n.py import --disc "My Game.cue" [--extracted DIR] [--l10n l10n] [--out translation]
                                           [--keep-going] [--report FILE] [--force] [--no-verify] [--only SUBSTR ..]
    python -I -X utf8 tools/l10n.py verify [--tdb translation] [--work build/l10n_rt] [--disc ..] [--extracted ..] [--full]
    python -I -X utf8 tools/l10n.py stats  [--l10n l10n] [--tdb translation]

export    translation/*.jsonl (+ refit/) -> l10n/*.jsonl, deterministic, atomic, in the order of the source files.  Refuses to
          write anything when a Japanese character would end up in the output.
import    l10n + the player's disc -> the working form.  The disc (or extracted/ folder) is verified against the Redump-style
          hashes of tools/release.toml first and the tool refuses on a mismatch (exit 3).  Every string is read by id from the
          disc, its hash is compared, every difference is reported BY ID (exit 1; --keep-going lists all, default stops at the
          first bad file).  Files with a mismatch are never written.  An existing differing output file is only replaced with --force.
verify    round trip on the current tree: export -> import -> byte comparison with the working form, into a scratch folder
          (never touches translation/ or l10n/).
stats     record counts and sizes.
Exit status: 0 ok, 1 hash mismatch / data problem, 2 bad usage, 3 the disc is not the dump the data was made for.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

FORMAT = 1
HASH_ALGO = 'sha256'
HASH_BYTES = 16                      # truncated: 32 hex digits
DEF_TDB = os.path.join(ROOT, 'translation')
DEF_L10N = os.path.join(ROOT, 'l10n')
DEF_EXTRACTED = os.path.join(ROOT, 'extracted')
MANIFEST_NAME = 'MANIFEST.json'
DISC_FILES_NAME = 'disc-files.tsv'
GAME_PRODUCT = 'HDR-0183'

CTX_MIN = 3                          # compaction thresholds (docs/l10n-format.md section 5)
CTX_LEN = 12
STYLES = {'compact': (',', ':'), 'spaced': (', ', ': ')}
# canonical key order of a record (the order every writer of the working form uses); other keys follow in their own order
CANON = ('id', 'ja', 'en', 'max_bytes', 'slot', 'refs', 'ctx', 'fmt', 'orphan', 'skip', 'cont', 'why', 'cls')
RESERVED = ('jah', 'same', 'ko', 'codec', 'sty')       # keys of the l10n form; a working record must not use them
JP_RE = re.compile('[\u2e80-\u33ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef\U0001b000-\U0001b16f\U0001f200-\U0001f2ff\U00020000-\U0002ffff]')
BCAST_SOURCE = 'BCAST/BCAST.BIN'
INI_SOURCE = 'DPETC/MESSAGE.INI'
# sources whose `ja` was written by tools/textfmt_common.decode_text; every other source uses the codec of tools/textdb.py
COMMON_CODEC_SOURCES = frozenset([BCAST_SOURCE, INI_SOURCE, 'ETC_DATA/BPINFO.BIN', 'ATFIRST/BPINFO.BIN', '2_DP.BIN', '1ST_READ.BIN'])
SECTOR = 2048
BCAST_TABLE = 0x60
BCAST_TEXT0 = 0x80
BPINFO_NAME = 14


class L10nError(Exception):
    """A readable problem (printed without a traceback)."""


# ============================================================================================ codecs (frozen, format v1)
_TOKEN = re.compile(r'<([0-9A-F]{2})>')
_HEXPAIR = re.compile(r'[0-9A-F]{2}>')


def decode_textdb(b):
    """bytes -> text exactly as tools/textdb.decode_text (FLOW_PRG / ATFIRST overlays): plain ASCII, `\\n` for 0x0a, `<XX>` for
    every other byte that is not a cp932 character >= U+0100 or a half-width katakana; a literal `<` is always `<3C>`."""
    out = []
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if c == 0x0a:
            out.append('\n')
            i += 1
        elif 0x20 <= c < 0x7f:
            out.append('<3C>' if c == 0x3c else chr(c))
            i += 1
        else:
            if (0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc) and i + 1 < n:
                try:
                    ch = b[i:i + 2].decode('cp932')
                    if len(ch) == 1 and ch.encode('cp932') == b[i:i + 2] and ch != '<' and ch >= '\u0100' and ch != '\n':
                        out.append(ch)
                        i += 2
                        continue
                except (UnicodeDecodeError, UnicodeEncodeError):
                    pass
            elif 0xa1 <= c <= 0xdf:
                out.append(chr(0xff61 + c - 0xa1))
                i += 1
                continue
            out.append('<%02X>' % c)
            i += 1
    return ''.join(out)


def decode_common(b):
    """bytes -> text exactly as tools/textfmt_common.decode_text (INI, BPINFO, 2_DP / 1ST_READ, BCAST): like decode_textdb, but a
    `<` is written `<3C>` only when `XX>` follows, and cp932 characters from U+0080 up are kept."""
    out = []
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if c == 0x0A:
            out.append('\n')
            i += 1
        elif 0x20 <= c < 0x7F:
            if c == 0x3c and _HEXPAIR.match(b[i + 1:i + 4].decode('latin1')):
                out.append('<3C>')
            else:
                out.append(chr(c))
            i += 1
        elif 0xA1 <= c <= 0xDF:
            out.append(bytes([c]).decode('cp932'))
            i += 1
        elif (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i + 1 < n:
            pair = b[i:i + 2]
            try:
                s = pair.decode('cp932')
                if len(s) == 1 and s.encode('cp932') == pair and s >= '\u0080' and s != '\ufffd':
                    out.append(s)
                    i += 2
                    continue
            except Exception:
                pass
            out.append('<%02X>' % c)
            i += 1
        else:
            out.append('<%02X>' % c)
            i += 1
    return ''.join(out)


def encode_text(s):
    """text -> raw bytes: the inverse of both decoders (`<XX>` tokens are single bytes, `\\n` is 0x0a, the rest is cp932)."""
    out = bytearray()
    pos = 0
    for m in _TOKEN.finditer(s):
        out += _enc_plain(s[pos:m.start()])
        out.append(int(m.group(1), 16))
        pos = m.end()
    out += _enc_plain(s[pos:])
    return bytes(out)


def _enc_plain(s):
    out = bytearray()
    for ch in s:
        if ch == '\n':
            out.append(0x0a)
        elif ord(ch) < 0x80:
            out.append(ord(ch))
        else:
            out += ch.encode('cp932')
    return bytes(out)


CODECS = {'textdb': decode_textdb, 'common': decode_common}


def codec_of(source):
    return 'common' if source in COMMON_CODEC_SOURCES else 'textdb'


def jah(raw):
    """The identity hash of a string: first HASH_BYTES bytes of SHA-256 over its raw cp932 bytes, as hex."""
    return hashlib.sha256(raw).digest()[:HASH_BYTES].hex()


# ============================================================================================ reading the working form
def split_id(rid):
    src, off = rid.rsplit('#', 1)
    return src, int(off, 16)


def read_working(path):
    """-> (records, styles, final_newline): the parsed records, the style ('compact' / 'spaced') of every line, and whether the
    file ends with a newline.  Raises L10nError for a line json.dumps cannot reproduce (that file could not be restored exactly)."""
    raw = slurp(path)
    if b'\r' in raw:
        raise L10nError('%s: CR characters (expected LF line ends)' % path)
    text = raw.decode('utf-8')
    final_nl = text.endswith('\n')
    lines = text.split('\n')
    if final_nl:
        lines.pop()
    recs, styles = [], []
    for k, line in enumerate(lines, 1):
        if not line:
            raise L10nError('%s line %d: empty line (not supported by the l10n format)' % (path, k))
        r = json.loads(line)
        if not isinstance(r, dict):
            raise L10nError('%s line %d: not a JSON object' % (path, k))
        st = None
        for name, sep in STYLES.items():
            if json.dumps(r, ensure_ascii=False, separators=sep) == line:
                st = name
                break
        if st is None:
            raise L10nError('%s line %d: cannot reproduce the line with json.dumps (ensure_ascii=False, compact or spaced '
                            'separators): %s' % (path, k, line[:100]))
        recs.append(r)
        styles.append(st)
    return recs, styles, final_nl


# ============================================================================================ export
def canon_order(keys):
    ks = list(keys)
    known = [k for k in CANON if k in ks]
    return known + [k for k in ks if k not in CANON]


def to_l10n(rec, kind, problems, where):
    """working record -> l10n record (dict with the keys in output order).  Problems (Japanese that would leak, unencodable text)
    are appended to `problems` as strings."""
    rid = rec.get('id')
    if not isinstance(rid, str) or '#' not in rid:
        problems.append('%s: record without a usable id' % where)
        return None
    for k in RESERVED:
        if k in rec:
            problems.append('%s: the working record uses the reserved key %r' % (rid, k))
            return None
    ja = rec.get('ja')
    if not isinstance(ja, str):
        problems.append('%s: no ja text' % rid)
        return None
    try:
        raw = encode_text(ja)
    except UnicodeEncodeError as e:
        problems.append('%s: ja cannot be encoded as cp932 (%s)' % (rid, e))
        return None
    src = split_id(rid)[0]
    codec = codec_of(src)
    codec_override = None
    if CODECS[codec](raw) != ja:
        other = 'common' if codec == 'textdb' else 'textdb'
        if CODECS[other](raw) == ja:
            codec_override = other
        else:
            problems.append('%s: ja does not round-trip through the cp932 codecs' % rid)
            return None
    out = {'id': rid, 'jah': jah(raw)}
    en = rec.get('en')
    if 'en' in rec and not isinstance(en, str):
        problems.append('%s: en is not a string' % rid)
        return None
    if en and en == ja:
        out['same'] = True
    elif en:
        if JP_RE.search(en):
            problems.append('%s: Japanese characters in en (%r)' % (rid, en[:40]))
            return None
        out['en'] = en
    need_ko = list(rec) != canon_order(rec) or 'en' not in rec or (kind == 'main' and 'refs' not in rec)
    for k in canon_order(rec):
        if k in ('id', 'ja', 'en'):
            continue
        v = rec[k]
        if isinstance(v, str) and JP_RE.search(v):
            problems.append('%s: Japanese characters in %s (%r)' % (rid, k, v[:40]))
            return None
        if k == 'refs' and v is None and not need_ko and kind == 'main':
            continue                       # compaction: a missing `refs` of a main record is null
        out[k] = v
    if need_ko:
        out['ko'] = list(rec)
    if codec_override:
        out['codec'] = codec_override
    return out


def dumps(obj, style):
    return json.dumps(obj, ensure_ascii=False, separators=STYLES[style])


def export_file(path, kind, problems):
    """-> (text of the l10n file, number of records) for one working file."""
    recs, styles, final_nl = read_working(path)
    name = os.path.basename(path)
    file_style = styles[0] if styles else 'compact'
    seen = set()
    outs = []
    for k, (r, st) in enumerate(zip(recs, styles), 1):
        o = to_l10n(r, kind, problems, '%s:%d' % (name, k))
        if o is None:
            continue
        if o['id'] in seen:
            problems.append('%s: duplicate id %s' % (name, o['id']))
            continue
        seen.add(o['id'])
        if st != file_style:
            o['sty'] = st
        outs.append(o)
    head = {'l10n': FORMAT, 'kind': kind, 'style': file_style, 'n': len(recs), 'final_newline': final_nl}
    # compaction 1: one source per file -> the ids are bare hex offsets and the header names the source
    srcs = {split_id(o['id'])[0] for o in outs}
    if len(srcs) == 1:
        src = next(iter(srcs))
        head['src'] = src
        for o in outs:
            o['id'] = o['id'].rsplit('#', 1)[1]
    # compaction 2: a ctx text that occurs at least CTX_MIN times is stored once in the header and referenced by index
    cnt = {}
    for o in outs:
        c = o.get('ctx')
        if isinstance(c, str) and len(c) >= CTX_LEN:
            cnt[c] = cnt.get(c, 0) + 1
    table = sorted((c for c, n in cnt.items() if n >= CTX_MIN), key=lambda c: (-cnt[c], c))
    if table:
        head['ctx'] = table
        idx = {c: i for i, c in enumerate(table)}
        for o in outs:
            c = o.get('ctx')
            if isinstance(c, str) and c in idx:
                o['ctx'] = idx[c]
    lines = [dumps(o, 'compact') for o in outs]
    return dumps(head, 'compact') + '\n' + '\n'.join(lines) + ('\n' if lines else ''), len(recs)


def working_files(tdb):
    """[(relative l10n name, path, kind)] for translation/*.jsonl ('main') and translation/refit/*.jsonl ('refit')."""
    out = []
    for fn in sorted(os.listdir(tdb)):
        if fn.endswith('.jsonl'):
            out.append((fn, os.path.join(tdb, fn), 'main'))
    rdir = os.path.join(tdb, 'refit')
    if os.path.isdir(rdir):
        for fn in sorted(os.listdir(rdir)):
            if fn.endswith('.jsonl') and not fn.startswith('_'):
                out.append(('refit/' + fn, os.path.join(rdir, fn), 'refit'))
    return out


def slurp(path):
    with open(path, 'rb') as f:
        return f.read()


def atomic_write(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.tmp'
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def read_release_hashes():
    import verify_source_disc as V
    exp, rel = V.load_expected()
    return exp, rel


def build_manifest(outputs, out_dir, log):
    """MANIFEST.json of the committed form: format, hash definition, game id, expected disc hashes, per-file counts and hashes."""
    exp, rel = read_release_hashes()
    files = {}
    totals = {'records': 0, 'files': 0}
    for name, (data, n) in sorted(outputs.items()):
        files[name] = {'records': n, 'sha256': sha256_hex(data)}
        totals['records'] += n
        totals['files'] += 1
    man = {
        'l10n_format': FORMAT,
        'game': {'title': rel.get('title', ''), 'product': rel.get('product', GAME_PRODUCT)},
        'hash': {'algorithm': HASH_ALGO, 'input': 'raw cp932 bytes of the string as stored on the disc, without the terminator',
                 'truncate_bytes': HASH_BYTES, 'encoding': 'hex'},
        'disc': {k: {h: exp[k][h] for h in ('size', 'crc32', 'md5', 'sha1', 'sha256') if h in exp[k]} for k in sorted(exp)},
        'disc_files': DISC_FILES_NAME,
        'files': files,
        'totals': totals,
    }
    dfp = os.path.join(out_dir, DISC_FILES_NAME)
    if os.path.isfile(dfp):
        man['disc_files_sha256'] = sha256_hex(slurp(dfp))
    return (json.dumps(man, indent=1, sort_keys=True) + '\n').encode('utf-8')


def cmd_export(a, log=print):
    tdb, out = os.path.abspath(a.tdb), os.path.abspath(a.out)
    if not os.path.isdir(tdb):
        raise L10nError('no such folder: %s' % tdb)
    problems = []
    outputs = {}
    t0 = time.time()
    for name, path, kind in working_files(tdb):
        if a.only and not any(o in name for o in a.only):
            continue
        try:
            text, n = export_file(path, kind, problems)
        except L10nError as e:
            problems.append(str(e))
            continue
        outputs[name] = (text.encode('utf-8'), n)
    leak = [n for n, (d, _) in outputs.items() if JP_RE.search(d.decode('utf-8'))]
    if leak:
        problems.append('Japanese characters in the output of %s (bug)' % ', '.join(leak[:5]))
    if problems:
        for p in problems[:50]:
            log('ERROR: ' + p)
        if len(problems) > 50:
            log('... and %d more' % (len(problems) - 50))
        log('nothing written')
        return 1
    stale = []
    if os.path.isdir(out) and not a.only:
        for name, path, kind in working_files(out):
            if name not in outputs:
                stale.append(name)
    for name, (data, n) in outputs.items():
        p = os.path.join(out, *name.split('/'))
        if os.path.isfile(p) and slurp(p) == data:
            continue
        atomic_write(p, data)
    if not a.only:
        dfsrc = getattr(a, 'disc_files', None) or os.path.join(DEF_L10N, DISC_FILES_NAME)     # the file manifest of the disc travels with the data
        dfdst = os.path.join(out, DISC_FILES_NAME)
        if os.path.isfile(dfsrc) and os.path.abspath(dfsrc) != os.path.abspath(dfdst):
            atomic_write(dfdst, slurp(dfsrc))
        atomic_write(os.path.join(out, MANIFEST_NAME), build_manifest(outputs, out, log))
    tot = sum(n for _, n in outputs.values())
    log('exported %d files, %d records, %s bytes (%.1f s)' % (len(outputs), tot, '{:,}'.format(sum(len(d) for d, _ in outputs.values())),
                                                              time.time() - t0))
    if stale:
        log('note: %d file(s) in %s have no working-form counterpart: %s' % (len(stale), out, ', '.join(stale[:5])))
    return 0


# ============================================================================================ sources of raw bytes
class Mismatch:
    __slots__ = ('file', 'id', 'kind', 'detail')

    def __init__(self, file, rid, kind, detail=''):
        self.file, self.id, self.kind, self.detail = file, rid, kind, detail

    def line(self):
        return '%s  %s  %s%s' % (self.file, self.id, self.kind, (': ' + self.detail) if self.detail else '')


class DiscReader:
    """Raw bytes of the player's disc: whole files from an extracted/ folder (else read straight from the disc image) and the
    BCAST.BIN header sectors (always read from the disc image: the 630 MB file is not extracted)."""

    def __init__(self, disc=None, extracted=None):
        self.disc = disc
        self.extracted = extracted
        self._cache = {}
        self._bcast_lba = None

    def file(self, source):
        d = self._cache.get(source)
        if d is not None:
            return d
        data = None
        if self.extracted:
            p = os.path.join(self.extracted, *source.split('/'))
            if os.path.isfile(p):
                with open(p, 'rb') as f:
                    data = f.read()
        if data is None:
            if self.disc is None:
                raise L10nError('%s is not in the extracted folder and no disc image was given' % source)
            data = self.disc.read_file('/' + source)
        if len(self._cache) > 3:
            self._cache.pop(next(iter(self._cache)))
        self._cache[source] = data
        return data

    def bcast_header(self, sector):
        if self.disc is None:
            raise L10nError('%s can only be read from the disc image (--disc)' % BCAST_SOURCE)
        if self._bcast_lba is None:
            self._bcast_lba = self.disc.find('/' + BCAST_SOURCE)[0]
        return self.disc.read(self._bcast_lba + sector, SECTOR)


def cstr(b):
    i = b.find(b'\0')
    return b if i < 0 else b[:i]


def bcast_raw(header, seg_off):
    """The text of the segment at `seg_off` of a BCAST clip header (docs/text-sources.md section 6): the segment table is the u32
    list at 0x60 (ended by 0); a segment owns the bytes up to the next table entry, the last one up to the end of the sector."""
    if header[:16] != b'PCM FILE START  ':
        return None
    offs = []
    for i in range(BCAST_TABLE, BCAST_TEXT0, 4):
        v = int.from_bytes(header[i:i + 4], 'little')
        if v == 0:
            break
        offs.append(v)
    if seg_off not in offs:
        return None
    k = offs.index(seg_off)
    end = offs[k + 1] if k + 1 < len(offs) else SECTOR
    return cstr(header[seg_off:end])


def ini_raw(data, off):
    """The value of a `N="text"` line of MESSAGE.INI starting at `off` (the first byte after the opening quote)."""
    e = data.find(b'\n', off)
    e = len(data) if e < 0 else e
    if data[e - 1:e] == b'\r':
        e -= 1
    if e - 1 < off or data[e - 1:e] != b'"':
        return None
    return data[off:e - 1]


def raw_of(o, reader):
    """Raw bytes of the string an l10n record names, or (None, reason)."""
    rid = o['id']
    src, off = split_id(rid)
    try:
        if src == BCAST_SOURCE:
            h = reader.bcast_header(off // SECTOR)
            r = bcast_raw(h, off % SECTOR)
            return (r, None) if r is not None else (None, 'no text segment at this offset of the clip header')
        data = reader.file(src)
    except L10nError as e:
        return None, str(e)
    except Exception as e:                       # unreadable sector / file
        return None, '%s: %s' % (type(e).__name__, e)
    if off >= len(data):
        return None, 'offset %#x is past the end of %s (%d bytes)' % (off, src, len(data))
    if src == INI_SOURCE:
        r = ini_raw(data, off)
        return (r, None) if r is not None else (None, 'no INI value ending in a quote at this offset')
    if src.endswith('BPINFO.BIN'):
        return cstr(data[off:off + BPINFO_NAME]), None
    if o.get('fmt') == 'gap' and o.get('cont'):
        n = o.get('max_bytes')
        if not isinstance(n, int) or off + n > len(data):
            return None, 'bad span for a continued gap record'
        return data[off:off + n], None
    e = data.find(b'\0', off)
    return data[off:e if e >= 0 else len(data)], None


# ============================================================================================ import
def from_l10n(o, ja):
    """l10n record + the Japanese -> working record with the keys in the original order."""
    base = {k: v for k, v in o.items() if k not in RESERVED and k not in ('id', 'en', 'jah')}
    if 'ko' in o:
        order = o['ko']
    else:
        order = canon_order(['id', 'ja', 'en'] + list(base))
    vals = dict(base)
    vals['id'] = o['id']
    vals['ja'] = ja
    vals['en'] = ja if o.get('same') else o.get('en', '')
    return {k: vals[k] for k in order}


def read_l10n_file(path):
    """-> (header, [records])."""
    raw = slurp(path).decode('utf-8')
    lines = raw.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        raise L10nError('%s is empty' % path)
    head = json.loads(lines[0])
    if head.get('l10n') != FORMAT:
        raise L10nError('%s: unsupported l10n format %r (this tool reads format %d)' % (path, head.get('l10n'), FORMAT))
    recs = [json.loads(l) for l in lines[1:]]
    src, table = head.get('src'), head.get('ctx')
    for o in recs:                                   # undo the compaction of export_file
        if src is not None and '#' not in o['id']:
            o['id'] = src + '#' + o['id']
        c = o.get('ctx')
        if isinstance(c, int) and not isinstance(c, bool):
            o['ctx'] = table[c]
        if head.get('kind') == 'main' and 'refs' not in o and 'ko' not in o:
            o['refs'] = None
    return head, recs


def import_main(head, recs, name, reader, report, ja_wanted, ja_store):
    """-> list of working records (None when a record failed)."""
    out = []
    ok = True
    for o in recs:
        rid = o.get('id')
        raw, why = raw_of(o, reader)
        if raw is None:
            report.append(Mismatch(name, rid, 'unreadable', why))
            ok = False
            continue
        h = jah(raw)
        if h != o.get('jah'):
            report.append(Mismatch(name, rid, 'hash mismatch', 'disc bytes hash to %s, data says %s (%d bytes)' % (h, o.get('jah'), len(raw))))
            ok = False
            continue
        dec = CODECS[o.get('codec') or codec_of(split_id(rid)[0])]
        ja = dec(raw)
        w = from_l10n(o, ja)
        if rid in ja_wanted:
            ja_store[rid] = ja
        out.append((w, o.get('sty')))
    return out if ok else None


def import_refit(head, recs, name, report, ja_store, main_failed=False, deps=None):
    out = []
    ok = True
    for o in recs:
        rid = o.get('id')
        ja = ja_store.get(rid)
        if ja is None and main_failed:
            if deps is not None:
                deps.append(rid)                     # its main record failed above: not a separate problem
            ok = False
            continue
        if ja is None:
            report.append(Mismatch(name, rid, 'unknown id', 'no record with this id in the main data (or it was not imported)'))
            ok = False
            continue
        if jah(encode_text(ja)) != o.get('jah'):
            report.append(Mismatch(name, rid, 'hash mismatch', 'the main record has another Japanese text than this overlay'))
            ok = False
            continue
        out.append((from_l10n(o, ja), o.get('sty')))
    return out if ok else None


def render(head, items):
    style = head.get('style', 'compact')
    lines = [dumps(w, sty or style) for w, sty in items]
    return ('\n'.join(lines) + ('\n' if head.get('final_newline', True) and lines else '')).encode('utf-8')


def l10n_files(l10n_dir):
    out = []
    for fn in sorted(os.listdir(l10n_dir)):
        if fn.endswith('.jsonl'):
            out.append((fn, os.path.join(l10n_dir, fn), 'main'))
    rdir = os.path.join(l10n_dir, 'refit')
    if os.path.isdir(rdir):
        for fn in sorted(os.listdir(rdir)):
            if fn.endswith('.jsonl'):
                out.append(('refit/' + fn, os.path.join(rdir, fn), 'refit'))
    return out


def check_manifest(l10n_dir):
    """The data must have been made for the disc that tools/release.toml names."""
    p = os.path.join(l10n_dir, MANIFEST_NAME)
    if not os.path.isfile(p):
        raise L10nError('%s is missing' % p)
    man = json.loads(slurp(p).decode('utf-8'))
    if man.get('l10n_format') != FORMAT:
        raise L10nError('%s: unsupported l10n format %r' % (p, man.get('l10n_format')))
    exp, _ = read_release_hashes()
    for k, h in exp.items():
        if (man.get('disc') or {}).get(k, {}).get('sha256') != h['sha256']:
            raise L10nError('%s names a different source disc than tools/release.toml ([source.%s]); the data and the tool '
                            'versions do not belong together' % (p, k))
    return man


def verify_inputs(a, log):
    """Gate: the disc image / the extracted folder must be the recorded dump.  Returns (disc or None)."""
    import verify_source_disc as V
    disc = None
    if a.disc:
        if not a.no_verify:
            res = V.verify_disc(a.disc, log=log)
            log(res.text())
            if not res.ok:
                raise SystemExit(3)
        try:
            disc = V.SourceDisc(a.disc)
        except V.VerifyError as e:
            raise L10nError(str(e))
    if a.extracted and not a.no_verify:
        res = V.verify_extracted(a.extracted, log=log)
        log(res.text())
        if not res.ok:
            raise SystemExit(3)
    return disc


def cmd_import(a, log=print):
    l10n_dir, out = os.path.abspath(a.l10n), os.path.abspath(a.out)
    if not os.path.isdir(l10n_dir):
        raise L10nError('no such folder: %s' % l10n_dir)
    if not a.disc and not a.extracted and getattr(a, 'reader', None) is None:
        if os.path.isdir(DEF_EXTRACTED):
            a.extracted = DEF_EXTRACTED
        else:
            raise L10nError('give --disc IMAGE (and optionally --extracted DIR)')
    if not a.no_verify and not a.only:
        man = check_manifest(l10n_dir)
        listed = set(man.get('files') or {})
        have = {f[0] for f in l10n_files(l10n_dir)}
        if listed - have:                                  # an incomplete checkout must not give a silently partial translation
            miss = sorted(listed - have)
            raise L10nError('%s lists %d file(s) that are missing from %s: %s%s' % (
                MANIFEST_NAME, len(miss), l10n_dir, ', '.join(miss[:5]), ' ...' if len(miss) > 5 else ''))
        if have - listed:
            log('note: %d l10n file(s) are not in %s (not regenerated by export?): %s' % (
                len(have - listed), MANIFEST_NAME, ', '.join(sorted(have - listed)[:5])))
    reader = getattr(a, 'reader', None)                      # tests inject a reader; normally the disc / extracted folder is used
    disc = None if reader is not None else verify_inputs(a, log)
    if reader is None:
        reader = DiscReader(disc, os.path.abspath(a.extracted) if a.extracted else None)
    files = [f for f in l10n_files(l10n_dir) if not a.only or any(o in f[0] for o in a.only)]
    refit_ids = set()
    for name, path, kind in files:
        if kind == 'refit':
            refit_ids.update(o['id'] for o in read_l10n_file(path)[1])
    report, ja_store, written, same_n, skipped_n, bad_files = [], {}, 0, 0, 0, []
    deps = []
    outputs = []
    t0 = time.time()
    nrec = 0
    for name, path, kind in files:
        if kind != 'main':
            continue
        head, recs = read_l10n_file(path)
        if head.get('n') != len(recs):
            raise L10nError('%s: header says %s records, the file has %d (truncated?)' % (name, head.get('n'), len(recs)))
        before = len(report)
        items = import_main(head, recs, name, reader, report, refit_ids, ja_store)
        nrec += len(recs)
        if items is None:
            bad_files.append(name)
            if not a.keep_going:
                break
            continue
        outputs.append((name, render(head, items)))
    if not (bad_files and not a.keep_going):
        for name, path, kind in files:
            if kind != 'refit':
                continue
            head, recs = read_l10n_file(path)
            items = import_refit(head, recs, name, report, ja_store, bool(bad_files), deps)
            nrec += len(recs)
            if items is None:
                bad_files.append(name)
                if not a.keep_going:
                    break
                continue
            outputs.append((name, render(head, items)))
    if report:
        show = report if a.keep_going else report[:50]
        full = [m.line() for m in report]
        if a.report:
            atomic_write(os.path.abspath(a.report), ('\n'.join(full) + '\n').encode('utf-8'))
            log('full list of %d problems written to %s' % (len(report), a.report))
        by_kind = {}
        for m in report:
            by_kind[m.kind] = by_kind.get(m.kind, 0) + 1
        for m in show[:a.max_report]:
            log('MISMATCH ' + m.line())
        if len(show) > a.max_report:
            log('... %d more (use --report FILE for the full list)' % (len(show) - a.max_report))
        if deps:
            log('(%d refit overlay record(s) not checked because their main record failed)' % len(deps))
        log('SUMMARY: %d problem(s) in %d file(s) (%s); nothing was written for those files; the disc may be another game revision '
            'or the l10n data is out of date' % (len(report), len(bad_files), ', '.join('%s %d' % kv for kv in sorted(by_kind.items()))))
    for name, data in outputs:
        p = os.path.join(out, *name.split('/'))
        if os.path.isfile(p):
            if slurp(p) == data:
                same_n += 1
                continue
            if not a.force:
                log('REFUSED to overwrite %s (differs from the import; use --force or another --out)' % p)
                skipped_n += 1
                continue
        atomic_write(p, data)
        written += 1
    log('imported %d records from %d file(s): %d written, %d unchanged, %d refused (%.1f s)' % (
        nrec, len(files), written, same_n, skipped_n, time.time() - t0))
    if disc:
        disc.close()
    return 1 if report or skipped_n else 0


# ============================================================================================ verify (round trip)
def first_diff(a, b):
    la, lb = a.split(b'\n'), b.split(b'\n')
    for i, (x, y) in enumerate(zip(la, lb), 1):
        if x != y:
            return 'line %d differs' % i
    return 'length differs (%d vs %d lines)' % (len(la), len(lb))


def cmd_verify(a, log=print):
    tdb = os.path.abspath(a.tdb)
    work = os.path.abspath(a.work)
    if not os.path.abspath(work).startswith(os.path.join(ROOT, 'build') + os.sep) and not a.any_work:
        raise L10nError('the scratch folder must be under build/ (got %s)' % work)
    wl, wt = os.path.join(work, 'l10n'), os.path.join(work, 'translation')
    ns = argparse.Namespace
    import shutil
    for sub in ('l10n', 'l10n2', 'translation', 'snapshot'):         # scratch folders of an earlier run (only these four names)
        if os.path.isdir(os.path.join(work, sub)):
            shutil.rmtree(os.path.join(work, sub))
    # other agents may be editing the working form while this runs: take a snapshot first so that export and comparison see
    # one state
    snap = os.path.join(work, 'snapshot')
    for name, path, kind in working_files(tdb):
        if a.only and not any(o in name for o in a.only):
            continue
        dst = os.path.join(snap, *name.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(path, dst)
    tdb = snap
    log('== export %s -> %s' % (a.tdb, wl))
    r = cmd_export(ns(tdb=tdb, out=wl, only=a.only), log)
    if r:
        return r
    if a.full:
        # determinism: a second export into another folder must be byte-identical
        wl2 = os.path.join(work, 'l10n2')
        cmd_export(ns(tdb=tdb, out=wl2, only=a.only), lambda *x: None)
        bad = []
        for name, path, kind in l10n_files(wl):
            if slurp(path) != slurp(os.path.join(wl2, *name.split('/'))):
                bad.append(name)
        log('determinism (two exports): %s' % ('IDENTICAL' if not bad else 'DIFFERENT: %s' % bad[:5]))
        if bad:
            return 1
    log('== no Japanese in the committed form')
    n = 0
    for name, path, kind in l10n_files(wl):
        if JP_RE.search(slurp(path).decode('utf-8')):
            log('ERROR: Japanese characters in %s' % name)
            n += 1
    log('Japanese scan of %d files: %s' % (len(l10n_files(wl)), 'CLEAN' if not n else 'FAILED'))
    if n:
        return 1
    log('== import %s -> %s' % (wl, wt))
    ia = ns(l10n=wl, out=wt, disc=a.disc, extracted=a.extracted, keep_going=True, report=os.path.join(work, 'mismatches.txt'),
            force=True, no_verify=a.no_verify, only=a.only, max_report=50)
    r = cmd_import(ia, log)
    if r:
        return r
    log('== compare with the working form (byte for byte)')
    bad = missing = same = 0
    for name, path, kind in working_files(tdb):
        if a.only and not any(o in name for o in a.only):
            continue
        p2 = os.path.join(wt, *name.split('/'))
        if not os.path.isfile(p2):
            log('MISSING in the import: %s' % name)
            missing += 1
            continue
        d1, d2 = slurp(path), slurp(p2)
        if d1 != d2:
            log('DIFFERENT %s (%s)' % (name, first_diff(d1, d2)))
            bad += 1
        else:
            same += 1
    log('round trip: %d identical, %d different, %d missing -> %s' % (same, bad, missing, 'PASS' if not (bad or missing) else 'FAIL'))
    return 1 if (bad or missing) else 0


# ============================================================================================ stats
def cmd_stats(a, log=print):
    for label, d, loader in (('l10n', a.l10n, 'l10n'), ('working', a.tdb, 'work')):
        if not os.path.isdir(d):
            log('%s: %s does not exist' % (label, d))
            continue
        tot = {'files': 0, 'records': 0, 'bytes': 0, 'en': 0, 'empty': 0, 'same': 0, 'skip': 0}
        fm = {}
        for name, path, kind in (l10n_files(d) if loader == 'l10n' else working_files(d)):
            data = slurp(path)
            tot['files'] += 1
            tot['bytes'] += len(data)
            lines = data.decode('utf-8').split('\n')
            if lines and lines[-1] == '':
                lines.pop()
            if loader == 'l10n':
                lines = lines[1:]
            for line in lines:
                r = json.loads(line)
                if kind == 'main':
                    tot['records'] += 1
                    fm[r.get('fmt', '')] = fm.get(r.get('fmt', ''), 0) + 1
                    if r.get('same') or (loader == 'work' and r.get('en') and r.get('en') == r.get('ja')):
                        tot['same'] += 1
                    elif r.get('en'):
                        tot['en'] += 1
                    elif loader == 'l10n' or 'en' in r:
                        tot['empty'] += 1
                    if r.get('skip'):
                        tot['skip'] += 1
                else:
                    tot.setdefault('refit', 0)
                    tot['refit'] += 1
        log('%s (%s): %d files, %d main records (%d with English, %d identical to the Japanese, %d without English), '
            '%d skip, %s refit records, %s bytes' % (label, d, tot['files'], tot['records'], tot['en'], tot['same'], tot['empty'],
                                                      tot['skip'], tot.get('refit', 0), '{:,}'.format(tot['bytes'])))
        log('   fmt: %s' % ', '.join('%s=%d' % (k or 'overlay', v) for k, v in sorted(fm.items())))
    return 0


# ============================================================================================ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('export')
    p.add_argument('--tdb', default=DEF_TDB)
    p.add_argument('--out', default=DEF_L10N)
    p.add_argument('--disc-files', help='file manifest of the disc to ship with the data (default l10n/disc-files.tsv)')
    p.add_argument('--only', nargs='*')
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser('import')
    p.add_argument('--l10n', default=DEF_L10N)
    p.add_argument('--out', default=DEF_TDB)
    p.add_argument('--disc', help='.cue / .gdi / volume .iso of your own dump (needed for BCAST)')
    p.add_argument('--extracted', help='folder made by tools/extract.py (default: extracted/ when --disc is not given)')
    p.add_argument('--keep-going', action='store_true', help='do not stop at the first bad file: list every mismatch')
    p.add_argument('--report', help='write the full list of problems to this file')
    p.add_argument('--max-report', type=int, default=200)
    p.add_argument('--force', action='store_true', help='replace an existing, different output file')
    p.add_argument('--no-verify', action='store_true', help='skip the disc / manifest hash check (development only)')
    p.add_argument('--only', nargs='*')
    p.set_defaults(fn=cmd_import)
    p = sub.add_parser('verify')
    p.add_argument('--tdb', default=DEF_TDB)
    p.add_argument('--work', default=os.path.join(ROOT, 'build', 'l10n_rt'))
    p.add_argument('--disc')
    p.add_argument('--extracted')
    p.add_argument('--full', action='store_true')
    p.add_argument('--no-verify', action='store_true')
    p.add_argument('--any-work', action='store_true')
    p.add_argument('--only', nargs='*')
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser('stats')
    p.add_argument('--l10n', default=DEF_L10N)
    p.add_argument('--tdb', default=DEF_TDB)
    p.set_defaults(fn=cmd_stats)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except L10nError as e:
        print('error: %s' % e, file=sys.stderr)
        return 2
    except Exception as e:
        import verify_source_disc as V
        if not isinstance(e, V.VerifyError):
            raise
        # an unreadable / unknown / incomplete disc image (missing track file, not a cue/gdi/iso): a clean message, no traceback
        print('error: %s' % e, file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
