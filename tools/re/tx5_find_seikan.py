"""tx5: hunt for the HOME/AWAY label text (静観) in encodings / splits the plain cp932 search misses:
  1. '静' and '観' within 8 bytes of each other (control bytes in between), cp932
  2. UTF-16LE / UTF-16BE / UTF-8 / EUC-JP / JIS of 静観
  3. the glyph indices of 静 and 観 in FONT.BIN's full-width table (tools/font.py code order) as u16 LE / BE
over extracted/ and build/unpacked/ (read-only).   python -I -X utf8 tools/re/tx5_find_seikan.py"""
import os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
pats = {
    'cp932 near': re.compile(rb'\x90\xc3.{0,8}\x8a\xcf', re.S),
    'cp932 near rev': re.compile(rb'\x8a\xcf.{0,8}\x90\xc3', re.S),
    'utf16le': re.compile(re.escape('静観'.encode('utf-16-le'))),
    'utf16be': re.compile(re.escape('静観'.encode('utf-16-be'))),
    'utf8': re.compile(re.escape('静観'.encode('utf8'))),
    'euc': re.compile(re.escape('静観'.encode('euc-jp'))),
    'jis': re.compile(re.escape('静観'.encode('iso2022_jp'))),
}
hits = {}
for base in ('extracted', os.path.join('build', 'unpacked')):
    for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
        for n in fn:
            p = os.path.join(dp, n)
            try:
                if os.path.getsize(p) > 80_000_000:
                    continue
                d = open(p, 'rb').read()
            except OSError:
                continue
            for k, rx in pats.items():
                m = rx.search(d)
                if m:
                    hits.setdefault(k, []).append((os.path.relpath(p, ROOT).replace('\\', '/'), m.start()))
for k, v in hits.items():
    print(k, len(v), v[:12])
