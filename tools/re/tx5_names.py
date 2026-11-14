"""tx5: English for the 'name' clips of BCAST.BIN (player callouts: segment 0 = reading, segments 1.. = kanji variants of the same
surname, or half-width katakana foreign names with a surname-only second segment).

  * hiragana reading -> Hepburn, no macrons, long vowels not marked (docs/style-guide.md 7), capitalised; every kanji variant of the
    clip gets the same romanisation (they are homophones; whichever the game picks reads right)
  * half-width katakana -> the English of the same katakana word elsewhere in the DB (the player-name pools, translation/*.jsonl:
    5,574 of 5,584 clips resolved); two tokens 'Family Given' are written 'Given Family' (style guide 7)
  * the few fictional ones not in the DB: FIXED below

    python -I -X utf8 tools/re/tx5_names.py [--write]     -> build/tx5/results/names.tsv  (id<TAB>en), report of unresolved clips
"""
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'build', 'tx5', 'results', 'names.tsv')

FIXED = {
    'ﾊﾘｹｰﾝ': 'Hurricane', 'ｽｰﾊﾟｰﾊﾟｻｰ': 'Super Passer', 'ﾐﾗｸﾙﾊﾟｻｰ': 'Miracle Passer', 'ﾜﾝﾀﾞｰﾊﾟｻｰ': 'Wonder Passer',
    'ｴﾙ･ﾌﾟﾘﾝｼﾞﾍﾟ': 'El Principe',
}

_H = {}
_rows = ('あいうえお a i u e o', 'かきくけこ ka ki ku ke ko', 'さしすせそ sa shi su se so', 'たちつてと ta chi tsu te to',
         'なにぬねの na ni nu ne no', 'はひふへほ ha hi fu he ho', 'まみむめも ma mi mu me mo', 'らりるれろ ra ri ru re ro',
         'がぎぐげご ga gi gu ge go', 'ざじずぜぞ za ji zu ze zo', 'だぢづでど da ji zu de do', 'ばびぶべぼ ba bi bu be bo',
         'ぱぴぷぺぽ pa pi pu pe po')
for row in _rows:
    kana, *rom = row.split()
    for k, r in zip(kana, rom):
        _H[k] = r
_H.update({'や': 'ya', 'ゆ': 'yu', 'よ': 'yo', 'わ': 'wa', 'を': 'o', 'ん': 'n', 'ゐ': 'i', 'ゑ': 'e', 'ゔ': 'vu',
           'ぁ': 'a', 'ぃ': 'i', 'ぅ': 'u', 'ぇ': 'e', 'ぉ': 'o'})
_Y = {'ゃ': 'a', 'ゅ': 'u', 'ょ': 'o'}


def hira_to_roman(s):
    out = []
    i = 0
    dbl = False
    while i < len(s):
        c = s[i]
        if c == 'っ':
            dbl = True
            i += 1
            continue
        if c == 'ー':
            i += 1
            continue
        if i + 1 < len(s) and s[i + 1] in _Y and c in _H:
            base = _H[c]
            y = _Y[s[i + 1]]
            if base in ('shi', 'chi', 'ji'):
                r = base[:-1] + y
            elif base.endswith('i'):
                r = base[:-1] + 'y' + y
            else:
                r = base + 'y' + y
            i += 2
        elif c in _H:
            r = _H[c]
            i += 1
        else:
            raise ValueError('cannot romanise %r in %r' % (c, s))
        if dbl:
            r = ('t' + r) if r.startswith('ch') else (r[0] + r)
            dbl = False
        out.append(r)
    r = ''.join(out)
    r = re.sub(r'n(?=[aiueoy])', 'n', r)                  # syllabic n kept as n (no apostrophe in ASCII)
    r = r.replace('ou', 'o').replace('oo', 'o').replace('uu', 'u').replace('oh', 'o')
    return r.capitalize()


_COMBO = {'ふぁ': 'fa', 'ふぃ': 'fi', 'ふぇ': 'fe', 'ふぉ': 'fo', 'てぃ': 'ti', 'でぃ': 'di', 'うぃ': 'wi', 'うぇ': 'we',
          'うぉ': 'wo', 'ゔぁ': 'va', 'ゔぃ': 'vi', 'ゔぇ': 've', 'ゔぉ': 'vo', 'しぇ': 'she', 'ちぇ': 'che', 'じぇ': 'je',
          'つぁ': 'tsa', 'つぇ': 'tse', 'つぉ': 'tso', 'とぅ': 'tu', 'どぅ': 'du', 'ぐぁ': 'gwa'}


def kata_to_roman(s):
    """Fallback for foreign names that no DB record carries: phonetic Hepburn of the katakana (machine romanisation)."""
    import unicodedata
    s = unicodedata.normalize('NFKC', s)
    h = ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)
    h = h.replace('･', '').replace('・', '')
    for k, v in _COMBO.items():
        h = h.replace(k, '\0' + v + '\0')
    parts = h.split('\0')
    out = ''
    for i, p in enumerate(parts):
        out += p if i % 2 else (hira_to_roman(p).lower() if p else '')
    return out.capitalize()


def load_lexicon():
    """hw katakana word -> English, taken from the DB; the LONGEST variant wins (the pools also hold slot-forced short forms)."""
    lex = collections.defaultdict(collections.Counter)
    for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
        if 'BCAST' in os.path.basename(p):
            continue
        for ln in open(p, encoding='utf8'):
            if ln.strip():
                r = json.loads(ln)
                if r.get('en') and re.fullmatch(r'[｡-ﾟ]+', r['ja']):
                    lex[r['ja']][r['en']] += 1
    return {k: max(v, key=lambda e: (len(e), v[e])) for k, v in lex.items()}


FALLBACK_USED = set()


def hw_name(ja, lex, unresolved):
    toks = [t for t in re.split(r'[ 　]+', ja.strip()) if t]
    en = []
    for t in toks:
        if t in FIXED:
            en.append(FIXED[t])
        elif t in lex:
            en.append(lex[t])
        elif re.fullmatch(r'[｡-ﾟァ-ヶー･・]+', t):
            try:
                en.append(kata_to_roman(t))
                FALLBACK_USED.add(t)
            except ValueError:
                unresolved.add(t)
                return None
        else:
            unresolved.add(t)
            return None
    if len(en) == 2:
        en = [en[1], en[0]]
    return ' '.join(en)


def main():
    lex = load_lexicon()
    recs = [json.loads(l) for l in open(os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl'), encoding='utf8')]
    byclip = collections.OrderedDict()
    for r in recs:
        m = re.match(r'clip (name\\\S+) seg (\d+)/', r['ctx'])
        if m:
            byclip.setdefault(m.group(1), []).append(r)
    res = {}
    unresolved = set()
    unk = []
    for clip, rs in byclip.items():
        s0 = rs[0]['ja'].strip()
        if re.fullmatch(r'[ぁ-ゖー]+', s0):
            try:
                en = hira_to_roman(s0)
            except ValueError as e:
                unk.append((clip, str(e)))
                continue
            for r in rs:
                res[r['id']] = en
        else:
            for r in rs:
                e = hw_name(r['ja'], lex, unresolved)
                if e is None:
                    # a kanji / other variant: reuse the first segment's result when it resolved
                    e0 = res.get(rs[0]['id'])
                    if e0 and not re.search(r'[｡-ﾟ]', r['ja']):
                        e = e0
                if e:
                    res[r['id']] = e
                else:
                    unk.append((clip, r['ja']))
    for k, v in list(res.items()):               # too long for the 15-character slot: keep the family-name part
        if len(v) > 15:
            w = v.split(' ')
            res[k] = w[-1] if len(w) > 1 and len(w[-1]) <= 15 else v[:15]
    print('machine-romanised katakana tokens (not in the DB):', len(FALLBACK_USED), sorted(FALLBACK_USED)[:40])
    print('name clips', len(byclip), 'records resolved', len(res), 'of', sum(len(v) for v in byclip.values()))
    print('unresolved', unk[:30], sorted(unresolved)[:30])
    longest = sorted(res.values(), key=len)[-8:]
    print('longest', longest, 'over 15:', sum(1 for v in res.values() if len(v) > 15))
    if '--write' in sys.argv:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, 'w', encoding='utf8', newline='\n') as f:
            for k, v in res.items():
                f.write('%s\t%s\n' % (k, v))
        print('wrote', OUT)


if __name__ == '__main__':
    main()
