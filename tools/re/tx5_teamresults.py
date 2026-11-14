"""tx5: English for the 'beat / lost to / drew with <national team>' clips (yh_end_ntr_*, yh_win_nt_* ...): a fixed sentence frame around a
country name, with the country taken from the DB lexicon (tx5_mech) and the override table.

    python -I -X utf8 tools/re/tx5_teamresults.py [--write]      -> build/tx5/results/r_teamres.tsv  (N<TAB>en)

Frame:  [残念ながら|惜しくも]? [強豪|強敵|古豪|ライバル、]? <country>代表 (を下しました | を破りました | に敗れました | に敗れております | と引き分けました |
        に引き分けております)   e.g.  強豪、ﾄﾞｲﾂ代表を破りました。 -> They beat Germany, a powerhouse.
"""
import os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))
import tx5_mech as M
import tx5_names as NM

PRE = {'残念ながら、': 'Sadly, ', '残念ながら': 'Sadly, ', '惜しくも': 'Unluckily, '}
ADJ = {'強豪、': ', a powerhouse', '強敵、': ', a tough opponent', '古豪、': ', a veteran power', 'ライバル、': ', their rival'}
KAN = {'韓国': 'South Korea', '中国': 'China', '香港': 'Hong Kong', '台湾': 'Taiwan', '北朝鮮': 'North Korea', '南ｱﾌﾘｶ': 'South Africa',
       '北ｱｲﾙﾗﾝﾄﾞ': 'Northern Ireland', 'ＵＡＥ': 'the UAE', '日本': 'Japan'}
FIX = {'ｵﾗﾝﾀﾞ': 'the Netherlands', 'ｱﾒﾘｶ': 'the USA', 'ﾁｪｺ': 'the Czech Republic', 'ｲﾝｸﾞﾗﾝﾄﾞ': 'England', 'ｽｺｯﾄﾗﾝﾄﾞ': 'Scotland', 'ｱｲﾙﾗﾝﾄﾞ': 'Ireland'}
VERB = [('を下しました', 'beat'), ('を破りました', 'beat'), ('に敗れました', 'lost'), ('に敗れております', 'lost'),
        ('と引き分けました', 'drew'), ('に引き分けております', 'drew')]


def country(c, lex):
    if c in KAN:
        return KAN[c]
    if c in FIX:
        return FIX[c]
    e = M.tr_token(c, lex)
    if e is None:
        try:
            e = NM.kata_to_roman(c)
        except Exception:
            return None
        NM.FALLBACK_USED.add(c)
    return e


def main():
    lex = M.lexicon()
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'tx5', 'distinct.tsv'), encoding='utf8')]
    out, left = [], []
    rx = re.compile(r'^(残念ながら、?|惜しくも)?(強豪、|強敵、|古豪、|ライバル、)?(.+?)代表(を下しました|を破りました|に敗れました|に敗れております|と引き分けました|に引き分けております)。?$')
    for n, tier, ja, cnt, ex in rows:
        m = rx.match(ja)
        if not m:
            continue
        pre, adj, c, verb = m.groups()
        cn = country(c, lex)
        if cn is None:
            left.append((n, ja))
            continue
        v = dict(VERB)[verb]
        p = PRE.get(pre or '', '')
        a = ADJ.get(adj or '', '')
        if v == 'beat':
            s = 'They beat %s%s.' % (cn, a)
        elif v == 'lost':
            s = 'They lost to %s%s.' % (cn, a)
        else:
            s = 'They drew with %s%s.' % (cn, a)
        if p:
            s = p + s[0].lower() + s[1:]
        out.append((n, s))
    print('team result lines', len(out), 'left', len(left), 'machine-romanised countries', sorted(NM.FALLBACK_USED))
    for n, s in out[:8] + out[-6:]:
        print('  ', n, s)
    if '--write' in sys.argv:
        with open(os.path.join(ROOT, 'build', 'tx5', 'results', 'r_teamres.tsv'), 'w', encoding='utf8', newline='\n') as f:
            for n, s in out:
                f.write('%s\t%s\n' % (n, s))


if __name__ == '__main__':
    main()
