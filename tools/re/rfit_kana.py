"""rfit_kana: half-width katakana -> Hepburn romanisation (docs/style-guide.md 7.1) for the refit generator.

    python -I -X utf8 tools/re/rfit_kana.py ｲｼﾊﾗ ｱﾝﾄﾞｳ ...

hepburn(ja) -> str | None.  Rules: shi / chi / tsu / fu / ji, syllabic n stays `n` (also before b / m / p), the long vowel
mark and the long vowels `ou` `oo` `uu` are not written (Ito, Ono, Yuki), a sokuon doubles the next consonant (`tch` before
ch), small ya / yu / yo and the foreign extensions (ｳｨ ｼｪ ｼﾞｪ ﾁｪ ﾌｧ ﾃｨ ...) are handled; the result is capitalised.  Returns None
for anything that is not half-width kana / blank (the caller then leaves the string alone).  Pure, no I/O.
"""
import sys

BASE = {
    'ｱ': 'a', 'ｲ': 'i', 'ｳ': 'u', 'ｴ': 'e', 'ｵ': 'o',
    'ｶ': 'ka', 'ｷ': 'ki', 'ｸ': 'ku', 'ｹ': 'ke', 'ｺ': 'ko',
    'ｻ': 'sa', 'ｼ': 'shi', 'ｽ': 'su', 'ｾ': 'se', 'ｿ': 'so',
    'ﾀ': 'ta', 'ﾁ': 'chi', 'ﾂ': 'tsu', 'ﾃ': 'te', 'ﾄ': 'to',
    'ﾅ': 'na', 'ﾆ': 'ni', 'ﾇ': 'nu', 'ﾈ': 'ne', 'ﾉ': 'no',
    'ﾊ': 'ha', 'ﾋ': 'hi', 'ﾌ': 'fu', 'ﾍ': 'he', 'ﾎ': 'ho',
    'ﾏ': 'ma', 'ﾐ': 'mi', 'ﾑ': 'mu', 'ﾒ': 'me', 'ﾓ': 'mo',
    'ﾔ': 'ya', 'ﾕ': 'yu', 'ﾖ': 'yo',
    'ﾗ': 'ra', 'ﾘ': 'ri', 'ﾙ': 'ru', 'ﾚ': 're', 'ﾛ': 'ro',
    'ﾜ': 'wa', 'ｦ': 'o', 'ﾝ': 'n',
}
VOICED = {
    'ｶ': 'ga', 'ｷ': 'gi', 'ｸ': 'gu', 'ｹ': 'ge', 'ｺ': 'go',
    'ｻ': 'za', 'ｼ': 'ji', 'ｽ': 'zu', 'ｾ': 'ze', 'ｿ': 'zo',
    'ﾀ': 'da', 'ﾁ': 'ji', 'ﾂ': 'zu', 'ﾃ': 'de', 'ﾄ': 'do',
    'ﾊ': 'ba', 'ﾋ': 'bi', 'ﾌ': 'bu', 'ﾍ': 'be', 'ﾎ': 'bo',
    'ｳ': 'vu',
}
SEMI = {'ﾊ': 'pa', 'ﾋ': 'pi', 'ﾌ': 'pu', 'ﾍ': 'pe', 'ﾎ': 'po'}
SMALL = {'ｧ': 'a', 'ｨ': 'i', 'ｩ': 'u', 'ｪ': 'e', 'ｫ': 'o', 'ｬ': 'ya', 'ｭ': 'yu', 'ｮ': 'yo'}
VOW = 'aiueo'


def _mora(first, small, voiced, semi):
    """romaji of kana `first` (+ voiced / semi mark) followed by small kana `small` ('' if none)"""
    if semi:
        b = SEMI.get(first)
    elif voiced:
        b = VOICED.get(first)
    else:
        b = BASE.get(first)
    if b is None:
        return None
    if not small:
        return b
    s = SMALL.get(small)
    if s is None:
        return None
    cons = b[:-1] if len(b) > 1 else ''
    if s in ('ya', 'yu', 'yo'):                    # ｷｬ -> kya, ｼｬ -> sha, ﾁｬ -> cha, ｼﾞｬ -> ja
        if b in ('shi', 'chi', 'ji'):
            return {'shi': 'sh', 'chi': 'ch', 'ji': 'j'}[b] + s[1:]
        return cons + s
    v = s                                           # ｳｨ ｼｪ ﾌｧ ﾃｨ ...
    if b == 'u' and first == 'ｳ':
        return 'w' + v if not voiced else 'v' + v
    if b in ('shi', 'chi', 'ji'):
        return {'shi': 'sh', 'chi': 'ch', 'ji': 'j'}[b] + v
    if b == 'fu':
        return 'f' + v
    if b in ('te', 'to') or (first == 'ﾃ'):
        return ('d' if voiced else 't') + v if first == 'ﾃ' else cons + v
    return cons + v


def hepburn(ja):
    if not ja:
        return None
    out = []
    i = 0
    n = len(ja)
    pending_sokuon = False
    while i < n:
        c = ja[i]
        if c == ' ':
            out.append(' ')
            i += 1
            continue
        if c == 'ｰ':
            i += 1
            continue
        if c == 'ｯ':
            pending_sokuon = True
            i += 1
            continue
        if c not in BASE:
            return None
        j = i + 1
        voiced = semi = False
        if j < n and ja[j] == 'ﾞ':
            voiced, j = True, j + 1
        elif j < n and ja[j] == 'ﾟ':
            semi, j = True, j + 1
        small = ''
        if j < n and ja[j] in SMALL:
            small, j = ja[j], j + 1
        m = _mora(c, small, voiced, semi)
        if m is None:
            return None
        if pending_sokuon and m[0] not in VOW and m[0] != 'n':
            m = ('t' if m.startswith('ch') else m[0]) + m
        pending_sokuon = False
        out.append(m)
        i = j
    s = ''.join(out)
    # long vowels are not written: ou -> o, oo -> o, uu -> u ; the syllabic n stays n
    for a, b in (('ou', 'o'), ('oo', 'o'), ('uu', 'u')):
        s = s.replace(a, b)
    return ' '.join(w[:1].upper() + w[1:] for w in s.split(' '))


if __name__ == '__main__':
    for w in sys.argv[1:]:
        print(w, hepburn(w))
