"""textfmt_bpinfo: ETC_DATA/BPINFO.BIN and ATFIRST/BPINFO.BIN (player database, 5321 players).

Format (PROVEN: file length == 64 + count*92 for both copies; names decode for all 5321):
  0x00  u16 count (5321) then a small header table (u16s, 0x40 bytes in total)
  0x40  count records of 92 (0x5c) bytes
        rec+0   char name[14]  cp932, "Surname Given" (full-width kanji / half-width katakana
                               / kana), NUL padded; at most 13 chars + NUL observed
        rec+14  ...            numeric stats (not text; byte 14 is non-zero in every record)
The two copies have identical name fields (326 byte differences, all in stats).
In-place length limit: 14 bytes including the terminating NUL -> 13 ASCII chars.
UNKNOWN: whether the game copies the name into a buffer larger than 14 bytes; the
92-byte stride is fixed by the code so names cannot simply be lengthened.

API: extract(data|path, source) -> entries ; apply(data, entries) -> bytes
CLI: python -I -X utf8 tools/textfmt_bpinfo.py [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textfmt_common as C

HDR = 0x40
STRIDE = 92
NAME = 14


def _count(data):
    cnt = struct.unpack_from('<H', data, 0)[0]
    if HDR + cnt * STRIDE != len(data):
        raise ValueError('BPINFO: size/count mismatch')
    return cnt


def extract(data, source='ETC_DATA/BPINFO.BIN'):
    if isinstance(data, str):
        data = open(data, 'rb').read()
    out = []
    for i in range(_count(data)):
        off = HDR + i * STRIDE
        f = data[off:off + NAME]
        z = f.find(b'\x00')
        name = f if z < 0 else f[:z]
        if z >= 0 and any(f[z:]):
            raise ValueError('BPINFO: non-zero tail in name field at %x' % off)
        out.append({'id': '%s#%x' % (source, off), 'ja': C.decode_text(name), 'en': '',
                    'max_bytes': NAME, 'refs': None, 'ctx': 'player #%d name' % i})
    return out


def apply(data, entries):
    buf = bytearray(data)
    for e in entries:
        en = e.get('en')
        if not en:
            continue
        off = int(e['id'].rsplit('#', 1)[1], 16)
        b = C.encode_text(en)
        if len(b) > NAME - 1:
            raise ValueError('%s: name %r is %d bytes, max %d' % (e['id'], en, len(b), NAME - 1))
        buf[off:off + NAME] = b + b'\x00' * (NAME - len(b))
    return bytes(buf)


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d1 = open(os.path.join(root, 'extracted', 'ETC_DATA', 'BPINFO.BIN'), 'rb').read()
    d2 = open(os.path.join(root, 'extracted', 'ATFIRST', 'BPINFO.BIN'), 'rb').read()
    ents = extract(d1, 'ETC_DATA/BPINFO.BIN')
    ents2 = extract(d2, 'ATFIRST/BPINFO.BIN')
    # one DB serves both copies: the name fields are identical, offsets equal
    assert [(e['id'].split('#')[1], e['ja']) for e in ents] == [(e['id'].split('#')[1], e['ja']) for e in ents2]
    for data in (d1, d2):
        assert apply(data, ents) == data
        assert apply(data, [dict(e, en=e['ja']) for e in ents if len(C.encode_text(e['ja'])) <= 13]) == data
    jp = sum(1 for e in ents for ch in e['ja'] if ord(ch) > 0x2000)
    print('BPINFO: %d names, %d non-ASCII chars, both copies identical in names, round trips OK' % (len(ents), jp))
    if '--write' in sys.argv:
        p = os.path.join(root, 'translation', 'ETC_DATA__BPINFO.BIN.jsonl')
        C.write_jsonl(p, C.merge_existing(p, ents))
        print('wrote', p, '(apply the same entries to ATFIRST/BPINFO.BIN as well)')
