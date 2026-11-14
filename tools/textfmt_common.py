"""Shared helpers for the textfmt_* extractors/patchers (owner: datatext).

Translation DB convention (JSON Lines, one file per source):
  {"id": "<source path>#<hex offset>", "ja": "...", "en": "", "max_bytes": N,
   "refs": N|null, "ctx": "..."}

ja/en text encoding
  * the file text is cp932 (Shift-JIS).  0x0a is written as "\\n".
  * every byte that is not plain printable cp932 text is written as an explicit
    <XX> token (XX = two UPPER-case hex digits): control bytes, invalid
    cp932 sequences and cp932 sequences that do not round-trip.
  * a literal '<' that would be followed by '[0-9A-F]{2}>' is written as <3C>
    so that the token grammar stays unambiguous.
  decode_text/encode_text are exact inverses for every byte string
  (encode_text(decode_text(b)) == b) -- verified by the per-format round trips.
English text is plain ASCII (any cp932-encodable char is accepted).
"""
import json
import os
import re

_TOK = re.compile(r'<([0-9A-F]{2})>')


def decode_text(b: bytes) -> str:
    out = []
    i = 0
    n = len(b)
    while i < n:
        c = b[i]
        if c == 0x0A:
            out.append('\n')
            i += 1
        elif 0x20 <= c < 0x7F:
            ch = chr(c)
            if ch == '<' and re.match(r'[0-9A-F]{2}>', b[i + 1:i + 4].decode('latin1')):
                out.append('<3C>')
            else:
                out.append(ch)
            i += 1
        elif 0xA1 <= c <= 0xDF:           # half-width katakana, single byte
            out.append(bytes([c]).decode('cp932'))
            i += 1
        elif (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i + 1 < n:
            pair = b[i:i + 2]
            try:
                s = pair.decode('cp932')
                if len(s) == 1 and s.encode('cp932') == pair and s >= '\u0080' and s != '�':
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


def encode_text(s: str) -> bytes:
    out = bytearray()
    pos = 0
    for m in _TOK.finditer(s):
        out += _enc_plain(s[pos:m.start()])
        out.append(int(m.group(1), 16))
        pos = m.end()
    out += _enc_plain(s[pos:])
    return bytes(out)


def _enc_plain(s: str) -> bytes:
    out = bytearray()
    for ch in s:
        if ch == '\n':
            out.append(0x0A)
        else:
            out += ch.encode('cp932')
    return bytes(out)


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf8') as f:
        return [json.loads(l) for l in f if l.strip()]


KEYS = ('id', 'ja', 'en', 'max_bytes', 'refs', 'ctx')     # the extractor's own fields, always written, in this order


def write_jsonl(path, entries):
    """Deterministic writer: the fixed keys first (in KEYS order, None when missing), then every other key of the entry
    in its own order -- `skip`, `orphan` and any field a tool added are preserved, not dropped.  One entry per line, LF
    newlines.  Atomic: <path>.tmp is written completely and then replaces <path> (a failure leaves the old file)."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf8', newline='\n') as f:
            for e in entries:
                rec = {k: e.get(k) for k in KEYS}
                rec.update((k, v) for k, v in e.items() if k not in rec)
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def merge_existing(path, entries):
    """Carry over an existing DB file's translation work (matching on id, and only while `ja` is unchanged) so that
    re-running an extractor never destroys it: a non-empty 'en', the `skip` flag and every other extra key of the old
    record (anything but the extractor's own fields).  Fields the extractor produces always win."""
    old = {e['id']: e for e in read_jsonl(path)}
    for e in entries:
        o = old.get(e['id'])
        if not o or o.get('ja') != e['ja']:
            continue
        if o.get('en'):
            e['en'] = o['en']
        for k, v in o.items():
            if k not in KEYS and k not in e:
                e[k] = v
    return entries
