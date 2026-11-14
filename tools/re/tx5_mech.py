"""tx5: mechanical English for the proper-noun clip groups of BCAST.BIN (yh_tm_*: club / national team names with particles,
yh_stadi*: stadium names), built from the half-width katakana words the DB already translated (club-name pool, nations, stadium parts).

    python -I -X utf8 tools/re/tx5_mech.py [--write]       -> build/tx5/results/r_mech.tsv  (N<TAB>en) + a coverage report

A line is translated only when EVERY hw katakana run of it is in the DB lexicon (longest variant) or is a stadium word known below;
otherwise it is left for the manual batches (listed in build/tx5/mech_left.tsv).  Particles: 対 -> 'vs', FC / FC東京 style ASCII kept.
"""
import collections, glob, json, os, re, sys, unicodedata
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))
import tx5_names as NM

HW = r'[｡-ﾟ]+'
KANJI = {'北朝鮮': ' North Korea ', '北欧': ' Nordic ', '世界選抜': ' World XI', '欧州選抜': ' European XI', 'サカつく': ' Sakatsuku ', '韓国': ' South Korea ', '中国': ' China ', '台湾': ' Taiwan ', '香港': ' Hong Kong ',
         '南米': ' South America ', '中東': ' Middle East ', '極東': ' Far East ', '謎の': ' Mysterious ', '代表': ' national team',
         '日本': ' Japan ', '世界': ' World ', '欧州': ' Europe ', '東京': ' Tokyo ', '横浜': ' Yokohama ', 'スタジアム': ' Stadium',
         '鹿島': ' Kashima', '市原': ' Ichihara', '柏': ' Kashiwa', '浦和': ' Urawa', '川崎': ' Kawasaki', '平塚': ' Hiratsuka',
         '清水': ' Shimizu', '磐田': ' Iwata', '名古屋': ' Nagoya', '京都': ' Kyoto', '大阪': ' Osaka', '神戸': ' Kobe',
         '広島': ' Hiroshima', '福岡': ' Fukuoka', '札幌': ' Sapporo', '仙台': ' Sendai', '山形': ' Yamagata', '大宮': ' Omiya',
         '甲府': ' Kofu', '新潟': ' Niigata', '鳥栖': ' Tosu', '大分': ' Oita', '水戸': ' Mito', '・': ' ', '北': ' North ', '南': ' South '}


def lexicon():
    lex = collections.defaultdict(collections.Counter)
    for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
        if 'BCAST' in os.path.basename(p):
            continue
        for ln in open(p, encoding='utf8'):
            if not ln.strip():
                continue
            r = json.loads(ln)
            if r.get('en') and re.fullmatch(HW, r['ja']):
                lex[r['ja']][r['en']] += 1
    out = {k: max(v, key=lambda e: (len(e), v[e])) for k, v in lex.items()}
    # full forms for the words the DB only holds as slot-forced abbreviations (Mars., Dortm., RUS ...): tools/re/tx5_mech_override.tsv
    for ln in open(os.path.join(ROOT, 'tools', 're', 'tx5_mech_override.tsv'), encoding='utf8'):
        if ln.strip():
            k, _, v = ln.rstrip('\n').partition('\t')
            out[k] = v
    return out


def tr_token(t, lex):
    if '･' in t:
        parts = [p for p in t.split('･') if p]
        es = [tr_token(p, lex) for p in parts]
        return None if any(e is None for e in es) else ' '.join(es)
    if t in lex:
        return lex[t]
    # stadium compound: <word>ｽﾀｼﾞｱﾑ
    for suf, en in (('ｽﾀｼﾞｱﾑ', 'Stadium'), ('ﾊﾟｰｸ', 'Park'), ('ｱﾘｰﾅ', 'Arena')):
        if t.endswith(suf) and len(t) > len(suf):
            base = t[:-len(suf)]
            if base in lex:
                return '%s %s' % (lex[base], en)
    return None


def tr_line(ja, lex):
    s = ja
    out = []
    pos = 0
    for m in re.finditer(HW, s):
        out.append(('t', s[pos:m.start()]))
        out.append(('h', m.group(0)))
        pos = m.end()
    out.append(('t', s[pos:]))
    res = ''
    for kind, v in out:
        if kind == 'h':
            e = tr_token(v, lex)
            if e is None:
                return None
            res += e
        else:
            t = v
            for k, e in sorted(KANJI.items(), key=lambda kv: -len(kv[0])):
                t = t.replace(k, e)
            t = t.replace('対', 'vs')
            t = unicodedata.normalize('NFKC', t) if re.fullmatch(r'[＀-￯\s]*', t) else t
            if re.search(r'[^\x20-\x7e]', t):
                return None
            res += t
    res = re.sub(r'\s+', ' ', res).replace('North Ireland', 'Northern Ireland')
    res = re.sub(r'(\w)(FC)', r'\1 \2', res)
    return res.strip() + (' ' if res.endswith(' ') else '')


def main():
    lex = lexicon()
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'tx5', 'distinct.tsv'), encoding='utf8')]
    done = set()
    for fp in glob.glob(os.path.join(ROOT, 'build', 'tx5', 'results', 'r0*.tsv')):
        for ln in open(fp, encoding='utf8'):
            done.add(ln.split('\t', 1)[0])
    ok, left = [], []
    for n, tier, ja, cnt, ex in rows:
        if n in done:
            continue
        stems = ex.split()
        if not any(re.match(r'yh_(tm_|stadi)', st) for st in stems):
            continue
        e = tr_line(ja, lex)
        if e is None or not e.strip():
            left.append((n, ja, ex))
        else:
            ok.append((n, e))
    print('mechanical', len(ok), 'left', len(left))
    for n, e in ok[:12]:
        print('  ', n, e)
    for n, ja, ex in left[:15]:
        print('  LEFT', n, ja, ex)
    if '--write' in sys.argv:
        with open(os.path.join(ROOT, 'build', 'tx5', 'results', 'r_mech.tsv'), 'w', encoding='utf8', newline='\n') as f:
            for n, e in ok:
                f.write('%s\t%s\n' % (n, e.rstrip() if len(e) > 73 else e.rstrip()))
        with open(os.path.join(ROOT, 'build', 'tx5', 'mech_left.tsv'), 'w', encoding='utf8', newline='\n') as f:
            for n, ja, ex in left:
                f.write('%s\t%s\t%s\n' % (n, ja, ex))


if __name__ == '__main__':
    main()
