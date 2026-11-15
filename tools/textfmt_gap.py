"""textfmt_gap: player-visible Japanese strings of the SH-4 overlays that the pointer / orphan scan of tools/textdb.py misses.

Found by the tx5 skeptic pass (tools/re/tx5s_gap2.py: every NUL-bounded cp932 string of every overlay that no record covers).  Two causes:

  * a NUL-terminated string the scan rejects (RECON `=w/#sname#さん、おめでとうございます！ ...` contains pointer-looking
    bytes; TRAINING `今回の試合で使うｼｽﾃﾑを決定します。` mixes half-width kana; NENREP labels and a prose orphan with
    `@Y/ #tk01#` markup; HELP `@R/選ばれていない@`; HOMETOWN `%s%sです。`)                    -> cont = False
  * the HEAD of a prose string that has a pointer INTO it: `今年の観客数はまずまずといった\\n所でしょうか。\\nまだ頑張れる余地は有る`
    is one 68-byte run which continues, without a NUL, into the pointer-referenced tail record `はずです。` (NENREP annual
    report).  textdb pass 1 accepted the tail as a string, pass 2 then dropped the whole run because it contains covered
    bytes, so the head never became a record and showed in Japanese.                          -> cont = True

The table GAPS below is curated (PROVEN by reading the bytes, see docs/uncovered-text.md section 9); `extract` re-checks every
entry against the image and silently skips one that no longer matches or overlaps a `exclude` range.

Record: {"id": "<source>#<hex off>", "ja", "en", "max_bytes", "refs": null, "ctx": "gap ...", "fmt": "gap", "cont": bool}
  cont False: max_bytes = span + 1 (string + NUL); English + NUL is written in place and the rest of the slot is zero.
  cont True : max_bytes = span (no NUL slot: the next byte is the first byte of the next record, which continues the text);
              the English (at most span - 1 bytes) is written padded with spaces to exactly `span` bytes.  When the English
              holds a line break the padding goes in front of its LAST line break (trailing blanks of a line are invisible),
              else at the end.  A Japanese head that ends with a line break keeps one.
Never relocated, never grows (like fmt recarr).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textfmt_common as C  # noqa: E402

# source -> [(offset, span, cont[, slot])]   span = bytes of the text WITHOUT the NUL (cont: up to the start of the next record);
# slot (cont False only, optional) = span + NUL + the all-zero padding behind it that the record may use (max_bytes = slot)
GAPS = {
    'FLOW_PRG/NENREP.BIN': [
        (0x23298, 12, False),    # @Y/元チーム@
        (0x232b4, 12, False),    # @Y/新チーム@
        (0x232d8, 12, False),    # @Y/クラブ名@
        (0x2338a, 24, True),     # 今年は@P/#tk00#@で優勝で  | きて\n大変充実した...  (0x233a2)
        (0x23487, 41, True),     # 今年は残念な事に負け越してしまいました。\n | このままでは... (0x234b0)
        (0x235e4, 68, True),     # 今年の観客数は...まだ頑張れる余地は有る | はずです。 (0x23628)
        (0x23633, 37, True),     # お世辞にも盛況とは言えませんね。\nこの | ままだと... (0x23658)
        (0x23a1c, 26, True),     # 残念ながら、今年は赤字を出 | してしまい... (0x23a36)
        (0x23c0a, 14, True),     # 今年の日本代表 | は@P/#tk00#@... (0x23c18)
        (0x23c65, 43, True),     # @P/#tk00#@では、非常に\n良い成績を収める事が | 出来ましたね。 (0x23c90)
        (0x23d1c, 16, True),     # 今年行われた人事 | 活動の、... (0x23d2c)
        (0x23d58, 12, True),     # 今年は有力選 | 手が多数移籍したようですね。... (0x23d64)
        (0x23ddc, 4, True),      # 今年 | は世界的なニュースとなる... (0x23de0)
        (0x23e12, 45, False),    # ここでは@Y/#tk01#@の状況を見る事が\n出来ます。
        (0x24628, 24, False),    # @Y/Ｊリーグ  DIVISION 1@
        (0x24644, 24, False),    # @Y/Ｊリーグ  DIVISION 2@
        (0x24660, 18, False),    # @Y/クラブ参加大会@
        # the annual report's own copy of the money formats (data block 0x24efc..0x24f33; the first one, `@R/%s億%s万円@`, is the tail of record
        # #24ef8 behind its 4 byte float 0.7).  Slots = string + NUL + zero pad (8 / 12 bytes); docs/number-formats.md s12 (skm7), stage 8b
        (0x24f0c, 10, False, 12),   # %s億%s万円
        (0x24f18, 10, False, 12),   # @R/%s万円@
        (0x24f24, 6, False, 8),     # %s万円
        (0x24f2c, 4, False, 8),     # %s円
        # the annual report's people formats (data block 0x24f34..0x24f8b, loaded by the number function at 0xe3cc through 8 literal-pool words; the money
        # formats above are the same function family).  `real(fmt, hi, lo)` prints the visible text: hi = V / 10000 padded with spaces to the mode (3),
        # lo = V % 10000 zero padded to 4 digits; hi == 0: `real(fmt, lo)` with lo space padded to 4.  The four formats that end in `@` without `@R/`
        # (`-%s...@`, `%s...@`) go to the debug printf 0x8c0111b4 only (gated by a flag byte that is 0); they get short English to fit their slots.
        (0x24f34, 12, False, 16),   # @R/%s万%s人@   (red, negative, hi > 0)
        (0x24f44, 10, False, 12),   # -%s万%s人@     (debug printf only)
        (0x24f50, 8, False, 12),    # %s万%s人      (hi > 0)
        (0x24f5c, 9, False, 12),    # %s万%s人@     (debug printf only)
        (0x24f68, 8, False, 12),    # @R/%s人@       (red, negative, hi == 0)
        (0x24f74, 6, False, 8),     # -%s人@         (debug printf only)
        (0x24f7c, 4, False, 8),     # %s人          (hi == 0)
        (0x24f84, 5, False, 8),     # %s人@         (debug printf only)
    ],
    'FLOW_PRG/RECON.BIN': [(0x214fd, 105, False)],      # =w/#sname#さん、おめでとうございます！ ...契約を結びました。=
    'FLOW_PRG/TRAINING.BIN': [(0x44d89, 57, False),     # 今回の試合で使うｼｽﾃﾑを決定します。
                              (0x44dc3, 59, False)],    # 今回の試合で使うｼｽﾃﾑを変更しました。
    'FLOW_PRG/HELP.BIN': [(0x8ab8, 18, False)],         # @R/選ばれていない@
    'ATFIRST/HELP.BIN': [(0x8ab8, 18, False)],
    'FLOW_PRG/HOMETOWN.BIN': [(0x47060, 10, False)],    # %s%sです。
    # match preview stadium line `%sｽﾀｼﾞｱﾑ` (s7t): 8 bytes + NUL + 3 zero pad bytes = a 12-byte slot -> '%s Stadium' (11 bytes) fits
    'FLOW_PRG/SCHE0.BIN': [(0x39574, 8, False, 12)],
    'FLOW_PRG/SCHE1.BIN': [(0x39574, 8, False, 12)],
}


def _off(rec):
    return int(rec['id'].rsplit('#', 1)[1], 16)


def extract(data, source, exclude=None):
    """-> gap records of `source` (en empty), sorted by offset.  An entry is skipped when its bytes do not decode, when the
    NUL (cont False) is missing, or when it overlaps a range of `exclude` ([(a, b)])."""
    ex = sorted(exclude or [])
    out = []
    for ent in GAPS.get(source, ()):
        off, span, cont = ent[:3]
        slot = ent[3] if len(ent) > 3 else span + 1
        raw = bytes(data[off:off + span])
        if len(raw) != span or b'\0' in raw or (not cont and data[off + span:off + span + 1] != b'\0'):
            continue
        if not cont and any(data[off + span:off + slot]):
            continue
        mb = span if cont else slot
        if any(a < off + mb and off < b for a, b in ex):
            continue
        ctx = ('gap head: the text continues into the next record, no NUL stride-table(in-place only)' if cont
               else 'gap string: no pointer found by textdb, in place only stride-table(in-place only)')
        rec = {'id': '%s#%x' % (source, off), 'ja': C.decode_text(raw), 'en': '', 'max_bytes': mb, 'refs': None, 'ctx': ctx,
               'fmt': 'gap'}
        if cont:
            rec['cont'] = True
        out.append(rec)
    return out


def render(ja, en, span, cont, limit=None):
    """bytes written for one record: `span` bytes (cont) or len(en) + NUL padded with zeros to span + 1 (not cont)."""
    b = C.encode_text(en)
    if not cont:
        cap = span if limit is None else limit
        if len(b) > cap:
            raise ValueError('%r is %d bytes, the slot holds %d' % (en, len(b), cap))
        return b + b'\0' * (max(span, len(b)) + 1 - len(b))
    jb = C.encode_text(ja)
    tail = b'\n' if jb.endswith(b'\n') else b''
    core = b[:-1] if (tail and b.endswith(b'\n')) else b
    if len(core) + len(tail) > span - 1:
        raise ValueError('%r is %d bytes, the slot holds %d' % (en, len(core) + len(tail), span - 1))
    pad = span - len(core) - len(tail)
    k = core.rfind(b'\n')
    if k >= 0:
        core = core[:k] + b' ' * pad + core[k:]
    else:
        core = core + b' ' * pad
    return core + tail


def apply(data, entries):
    buf = bytearray(data)
    for e in entries:
        en = e.get('en')
        if not en:
            continue
        off = _off(e)
        cont = bool(e.get('cont'))
        jb = C.encode_text(e['ja'])
        span = e['max_bytes'] if cont else len(jb)
        limit = None if cont else e['max_bytes'] - 1
        if len(jb) != span or bytes(buf[off:off + span]) != jb or (not cont and buf[off + span] != 0):
            raise ValueError('%s: field no longer holds the Japanese text' % e['id'])
        out = render(e['ja'], en, span, cont, limit)
        buf[off:off + len(out)] = out
    return bytes(buf)


def main(argv):
    root = os.path.dirname(HERE)
    for src in sorted(GAPS):
        data = open(os.path.join(root, 'extracted', *src.split('/')), 'rb').read()
        for r in extract(data, src):
            print('%s%s  %s' % (r['id'], ' cont' if r.get('cont') else '', r['ja'].replace('\n', '/')))
        n = len(GAPS[src]) - len(extract(data, src))
        if n:
            print('  (%d entries of %s skipped)' % (n, src))


if __name__ == '__main__':
    main(sys.argv[1:])
