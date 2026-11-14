"""Pixel widths of English strings with the proportional font table (tools/fontpatch.py) -- used by docs/layout-issues.md.

    python -I -X utf8 tools/re/layout/prop_widths.py            # person names, sponsor names, region labels
    python -I -X utf8 tools/re/layout/prop_widths.py "text" ... # widths of the given strings

Plain font: every ASCII char is 12 px.  Proportional: table[byte] px (space 6, digits 12).  Does not write anything.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import fontpatch as FPT  # noqa: E402


def table():
    overrides = None
    ap = os.path.join(ROOT, 'translation', 'font', 'advance.json')
    if os.path.exists(ap):
        with open(ap, encoding='utf8') as f:
            overrides = FPT.parse_overrides(json.load(f))
    out, rep = FPT.make_patches(FPT.read_extracted, paths=[], overrides=overrides)
    return rep['table']


def px(t, s):
    return sum(t[ord(c)] for c in s)


def main():
    t = table()
    if len(sys.argv) > 1:
        for s in sys.argv[1:]:
            print('%4d px prop  %4d px plain  %r' % (px(t, s), 12 * len(s), s))
        return
    names = set()
    with open(os.path.join(ROOT, 'translation', 'ETC_DATA__BPINFO.BIN.jsonl'), encoding='utf8') as f:
        for line in f:
            r = json.loads(line)
            if r.get('en'):
                names.add(r['en'])
    w = sorted(px(t, n) for n in names)
    print('BPINFO names: %d distinct; plain max %d chars = %d px; proportional px: median %d, p95 %d, max %d' % (
        len(names), max(len(n) for n in names), 12 * max(len(n) for n in names), w[len(w) // 2], w[int(len(w) * .95)], w[-1]))
    for n in ('Isao Nakagaki', 'I. Nakagaki', 'Takami Hirano', 'Mamoru Nakaie'):
        print('  %-16s %4d px prop / %4d px plain' % (n, px(t, n), 12 * len(n)))
    print('sponsor name = town (7 chars) + suffix, proportional px:')
    for suf in ('Steamship', 'Shipping', 'Civic Society', 'Society', 'Fisheries', 'Fishery', 'Livestock', 'Farming', 'Builders', 'Painters'):
        for town in ('Aogashi', 'Asahik.'):
            s = town + ' ' + suf
            print('  %-24s %4d px prop / %4d px plain' % (s, px(t, s), 12 * len(s)))
    print('region labels (leading blank + text):')
    for s in ('Tohoku', 'Kansai', 'Kyushu', 'Hokkaido'):
        print('  %-10s %4d px prop / %4d px plain' % (s, px(t, ' ' + s) if False else px(t, s) + t[0x20], 12 * (len(s) + 1)))


if __name__ == '__main__':
    main()
