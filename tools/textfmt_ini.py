"""textfmt_ini: DPETC/MESSAGE.INI (Dream Passport browser UI strings).

Format (PROVEN by the round trip below): plain cp932 text, CRLF lines,
  `<number>="<text>"`   one string per line (text may itself contain " and <br>/<font> markup;
                         the value runs from the first quote to the LAST quote on the line)
  `#...`                comments (also commented-out strings such as `#16="..."`, not extracted)
Everything else (blank lines, `[Text]`, the odd `<---! ... --->` line) is kept verbatim.
The file is rebuilt line by line, so there is NO in-place length limit (max_bytes = null);
whether the browser has a buffer limit is UNKNOWN (2_DP.BIN not analysed for that).

API: extract(data|path, source='DPETC/MESSAGE.INI') -> list of entries
     apply(data, entries) -> bytes       (empty 'en' keeps the original)
CLI: python -I -X utf8 tools/textfmt_ini.py [--write]   (round trip + writes translation/DPETC__MESSAGE.INI.jsonl)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textfmt_common as C

SOURCE = 'DPETC/MESSAGE.INI'
_LINE = re.compile(rb'^(\d+)="(.*)"$', re.S)


def _lines(data):
    """yield (offset, line_bytes_without_eol, eol_bytes)"""
    pos = 0
    n = len(data)
    while pos < n:
        j = data.find(b'\n', pos)
        if j < 0:
            yield pos, data[pos:], b''
            return
        eol = b'\r\n' if j > pos and data[j - 1] == 0x0D else b'\n'
        yield pos, data[pos:j + 1 - len(eol)], eol
        pos = j + 1


def extract(data, source=SOURCE):
    if isinstance(data, str):
        data = open(data, 'rb').read()
    out = []
    for off, line, eol in _lines(data):
        m = _LINE.match(line)
        if not m:
            continue
        voff = off + m.start(2)
        out.append({'id': '%s#%x' % (source, voff), 'ja': C.decode_text(m.group(2)), 'en': '',
                    'max_bytes': None, 'refs': None, 'ctx': 'key %d' % int(m.group(1))})
    return out


def apply(data, entries, source=SOURCE):
    byoff = {}
    for e in entries:
        if e.get('en'):
            byoff[int(e['id'].rsplit('#', 1)[1], 16)] = e['en']
    if not byoff:
        return bytes(data)
    out = bytearray()
    for off, line, eol in _lines(data):
        m = _LINE.match(line)
        if m and (off + m.start(2)) in byoff:
            line = line[:m.start(2)] + C.encode_text(byoff[off + m.start(2)]) + line[m.end(2):]
        out += line + eol
    return bytes(out)


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(root, 'extracted', 'DPETC', 'MESSAGE.INI')
    data = open(src, 'rb').read()
    ents = extract(data)
    assert apply(data, ents) == data, 'identity round trip failed'
    for e in ents:
        assert C.encode_text(e['ja']) == C.encode_text(C.decode_text(C.encode_text(e['ja'])))
    # apply with ja as en must also be identity (checks decode/encode losslessness)
    assert apply(data, [dict(e, en=e['ja']) for e in ents]) == data, 'ja->bytes not lossless'
    print('MESSAGE.INI: %d strings, %d JP chars, identity + ja==en round trips OK' % (
        len(ents), sum(len(re.findall('[぀-ヿ一-鿿＀-￯]', e['ja'])) for e in ents)))
    if '--write' in sys.argv:
        p = os.path.join(root, 'translation', 'DPETC__MESSAGE.INI.jsonl')
        C.write_jsonl(p, C.merge_existing(p, ents))
        print('wrote', p)
