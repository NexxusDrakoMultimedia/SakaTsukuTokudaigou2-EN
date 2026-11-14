"""textfmt_ptrblob: Shift-JIS strings in a flat SH-4 memory image, located through
absolute 32-bit pointers (same mechanism as FLOW_PRG overlays, see docs/formats.md s2).

Used here for: ATFIRST/HELP.BIN, ATFIRST/TITLE.BIN (overlays that are NOT in FLOW_PRG;
ATFIRST/FACEMDUL.BIN was tried: only 3 noise hits, contains no text), 2_DP.BIN and 1ST_READ.BIN (main programs, base 0x8C010000).
It is generic: any image + base address works.

A string = NUL-terminated cp932 text starting at an image offset that some aligned
32-bit word of the image points at (word == base + offset).  Only strings with
Japanese content (>=1 kana or >=2 double-byte chars) are extracted.  Optionally
(unref=True) NUL-preceded kana-heavy strings that no word points at are added with
refs=0 (data accessed by index/computation - UNKNOWN how they are referenced).

max_bytes (in-place capacity) = strlen+1 plus following NUL padding, but never beyond
the next 4-byte boundary, the next non-zero byte, or the next pointed string.

apply(): en fits in place -> written in place, NUL padded to max_bytes.
         otherwise, if relocate=True and refs>0: the new string is APPENDED to the end of the
         image (4-byte aligned) and every aligned word == base+old_offset is rewritten.
         The image grows; whether the loader tolerates that (read size, BSS right after the
         image) is UNKNOWN/untested on hardware - the caller must check.
         unref strings can only be patched in place.

API  : extract(data, base, source, unref=False) -> entries
       apply(data, entries, base, relocate=True) -> bytes
CLI  : python -I -X utf8 tools/textfmt_ptrblob.py [--write]  (round trips for all configured files)
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textfmt_common as C

WRITE = {'2_DP.BIN', '1ST_READ.BIN'}      # 1ST_READ.BIN added by the coverage audit (docs/uncovered-text.md): textdb skips it
# (extracted path, base, output prefix, include unreferenced strings)
FILES = [
    ('2_DP.BIN', 0x8C010000, 'ROOT', False),          # unref strings there = IME dictionary, skipped
    # overlay-agent (tools/textdb.py) already owns these; listed for cross-checking only,
    # --write does NOT write them (see WRITE below)
    ('ATFIRST/HELP.BIN', 0x8CB60000, 'ATFIRST', True),
    ('ATFIRST/TITLE.BIN', 0x8C6D0000, 'ATFIRST', True),
    ('1ST_READ.BIN', 0x8C010000, 'ROOT', True),
]

_DB = rb'[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]'
_TEXT = re.compile(rb'(?:' + _DB + rb'|[\x0a\x20-\x7e]|[\xa1-\xdf])+')
_KANA = re.compile('[぀-ヿ]')
_KJ = re.compile('[぀-ヿ一-鿿＀-￯　-〿]')


def _words(data):
    n = len(data) // 4
    d = {}
    for i, w in enumerate(struct.unpack('<%dI' % n, data[:n * 4])):
        d.setdefault(w, []).append(i * 4)
    return d


def _cstr_at(data, off):
    """return the bytes of the NUL-terminated text at off if fully valid cp932 text, else None"""
    if off < 0 or off >= len(data):
        return None
    z = data.find(b'\x00', off)
    if z < 0 or z == off:
        return None
    m = _TEXT.fullmatch(data, off, z)
    if not m:
        return None
    return data[off:z]


def _lvl2(ch):
    """True for a JIS level-2 kanji (cp932 lead 0x98 trail>=0x9f, or lead >= 0x99) - rare in real text"""
    try:
        e = ch.encode('cp932')
    except Exception:
        return True
    return len(e) == 2 and (e[0] > 0x98 or (e[0] == 0x98 and e[1] >= 0x9f))


def _okchar(c):
    o = ord(c)
    return (o < 0x80 or c == chr(10) or 0xff61 <= o <= 0xff9f or 0x3000 <= o <= 0x30ff
            or 0x4e00 <= o <= 0x9fff or 0xff00 <= o <= 0xff60 or 0xffe0 <= o <= 0xffe6
            or 0x2010 <= o <= 0x2030 or 0x25a0 <= o <= 0x25ef or 0x2190 <= o <= 0x2199)


def _japanese(b):
    """strict filter against pointers into code/data that merely look like cp932:
    needs a kana or >=2 level-1 kanji, <=10% level-2 kanji, no exotic symbols."""
    try:
        s = b.decode('cp932')
    except Exception:
        return False
    kana = len(_KANA.findall(s))
    kanji = [c for c in s if 0x4e00 <= ord(c) <= 0x9fff]
    l2 = sum(1 for c in kanji if _lvl2(c))
    if l2 and (l2 * 10 > len(kanji) or (len(kanji) == 1 and not kana)):
        return False
    if not all(_okchar(c) for c in s):
        return False
    return kana >= 1 or len(kanji) - l2 >= 2



def detect_base(data):
    """same stub heuristic as tools/overlay.py (most-voted 0x8cXX0000 literal in the first 256 bytes)"""
    import overlay
    return overlay.unpack_overlay(data)['load_addr']


def extract(data, base, source, unref=False):
    if isinstance(data, str):
        data = open(data, 'rb').read()
    W = _words(data)
    n = len(data)
    targets = {}
    for w, pos in W.items():
        o = w - base
        if 0 <= o < n:
            targets[o] = len(pos)
    ptr_offsets = sorted(targets)
    found = {}
    for o in ptr_offsets:
        b = _cstr_at(data, o)
        if b is not None and _japanese(b):
            found[o] = (b, targets[o])
    if unref:
        for m in re.finditer(rb'(?<=\x00)' + _TEXT.pattern + rb'(?=\x00)', data):
            o = m.start()
            if o in found:
                continue
            b = m.group()
            if len(b) < 3 or not _japanese(b):
                continue
            s = b.decode('cp932', 'replace')
            if len(_KANA.findall(s)) * 10 < len(s) * 4:
                continue
            found[o] = (b, 0)
    # in-place capacity
    import bisect
    starts = sorted(set(found) | set(ptr_offsets))
    out = []
    for o in sorted(found):
        b, refs = found[o]
        end = o + len(b) + 1                       # after terminator
        cap_end = end
        # zero padding up to next 4-byte boundary
        al = (end + 3) & ~3
        j = end
        while j < al and j < n and data[j] == 0:
            j += 1
        if j == al:
            cap_end = al
        # never run into another pointed target
        k = bisect.bisect_right(starts, o)
        if k < len(starts) and starts[k] < cap_end:
            cap_end = max(end, starts[k])
        ctx = 'ptr' if refs else 'unref'
        # tail sharing: another pointed target inside the string body
        if k < len(starts) and starts[k] < end:
            ctx += ' shares-tail'
            cap_end = end
        out.append({'id': '%s#%x' % (source, o), 'ja': C.decode_text(b), 'en': '',
                    'max_bytes': cap_end - o, 'refs': refs, 'ctx': ctx})
    return out


def apply(data, entries, base, relocate=True):
    buf = bytearray(data)
    for e in entries:
        en = e.get('en')
        if not en:
            continue
        off = int(e['id'].rsplit('#', 1)[1], 16)
        b = C.encode_text(en) + b'\x00'
        cap = e['max_bytes']
        if len(b) <= cap:
            buf[off:off + cap] = b + b'\x00' * (cap - len(b))
            continue
        if not relocate or not e.get('refs'):
            raise ValueError('%s: %d bytes > max_bytes %d (relocate=%s refs=%s)' % (
                e['id'], len(b), cap, relocate, e.get('refs')))
        while len(buf) % 4:
            buf.append(0)
        new = len(buf)
        buf += b
        old_va = base + off
        new_va = base + new
        # rewrite every aligned word that equals old_va (scan only the original image part)
        pat = struct.pack('<I', old_va)
        i = 0
        cnt = 0
        while True:
            i = buf.find(pat, i)
            if i < 0:
                break
            if i % 4 == 0 and i < len(data):
                buf[i:i + 4] = struct.pack('<I', new_va)
                cnt += 1
                i += 4
            else:
                i += 1
        if cnt != e['refs']:
            raise ValueError('%s: expected %d pointers, patched %d' % (e['id'], e['refs'], cnt))
    return bytes(buf)


def _src(root, rel):
    return open(os.path.join(root, 'extracted', rel), 'rb').read()


def selftest(data, base, ents):
    """identity, ja==en identity, and a relocation/in-place mutation check"""
    assert apply(data, ents, base) == data
    assert apply(data, [dict(e, en=e['ja']) for e in ents], base) == data, 'ja->bytes not lossless'
    # mutation: lengthen 3 pointed strings (relocated), shorten the 4th (in place)
    ptr = [e for e in ents if e['refs'] and 'shares-tail' not in e['ctx']][:4]
    if len(ptr) == 4:
        muts = [dict(ptr[0], en='ア' * (ptr[0]['max_bytes'] // 2 + 3)),
                dict(ptr[1], en='イ' * (ptr[1]['max_bytes'] // 2 + 7)),
                dict(ptr[2], en='ウ' * (ptr[2]['max_bytes'] // 2 + 1)),
                dict(ptr[3], en='エエ')]
        new = apply(data, muts, base)
        assert len(new) > len(data)
        text2 = {e['ja'] for e in extract(new, base, 'T')}
        for m in muts:
            assert m['en'] in text2, 'mutated string not found again'
        # untouched strings still decode identically
        untouched = {e['ja'] for e in ents if e['refs']} - {e['ja'] for e in ptr}
        assert untouched <= text2, 'untouched strings changed'
    return True


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None      # e.g. --write --only 1ST_READ.BIN
    for rel, base, pref, unref in FILES:
        if only and rel != only:
            continue
        data = _src(root, rel)
        if base is None:
            base = detect_base(data)
        ents = extract(data, base, rel, unref=unref)
        selftest(data, base, ents)
        nptr = sum(1 for e in ents if e['refs'])
        jp = sum(len(_KJ.findall(e['ja'])) for e in ents)
        print('%-22s base %08x: %5d strings (%d pointed, %d unref), %6d JP chars, round trips OK' % (
            rel, base, len(ents), nptr, len(ents) - nptr, jp))
        if '--write' in sys.argv and rel in WRITE:
            p = os.path.join(root, 'translation', '%s__%s.jsonl' % (pref, os.path.basename(rel)))
            C.write_jsonl(p, C.merge_existing(p, ents))
