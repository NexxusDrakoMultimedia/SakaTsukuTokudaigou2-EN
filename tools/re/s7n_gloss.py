"""s7n: update translation/glossary.tsv for the names2 pass (idempotent): fixed J.League clubs, special teams, competitions per logo / banner art.

usage: python -I -X utf8 tools/re/s7n_gloss.py
Existing rows with a changed English are edited in place (the ja column is the key); new rows are appended.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'translation', 'glossary.tsv')
T = chr(9)

# ja, en, short, notes
ROWS = [
    ('欧州選抜 / 世界選抜', 'Euro / World', '', 'flag art EURO / WORLD (clubwords_art F32 / F33); the match title is World vs Europe (banner BINDMTCH 13912); prose: the Euro team / the World team'),
    ('ＦＣ東京', 'F.C.Tokyo', '', 'logo art F.C.TOKYO (F21); was FC Tokyo'),
    ('横浜Ｆ・マリノス', 'Yokohama F Marinos', 'Marinos', 'logo art, no period after F (F06); 8-byte pool slot keeps Marinos'),
    ('水戸ホーリーホック', 'Mito Hollyhock', '', 'logo art HOLLYHOCK (F27); was HollyHock'),
    ('湘南ベルマーレ', 'Shonan Bellmare', 'Bellmare', 'logo art Bellmare (F07); Belmare is a misspelling'),
    ('浦和レッドダイヤモンズ', 'Urawa Red Diamonds', 'Red Diamonds', 'logo art Red Diamonds (F02); Reds only where the slot is 8 bytes'),
    ('ジェフユナイテッド市原', 'JEF United Ichihara', 'JEF United', 'logo art JEF UNITED (F03); JEF only where the slot is 8 bytes'),
    ('ヴィッセル神戸', 'Vissel Kobe', '', 'logo art VISSEL KOBE (F14)'),
    ('サガン鳥栖', 'Sagan Tosu', '', 'logo art SAGANTOSU (F25)'),
    ('ｵｰﾙｲｰｽﾄ', 'East', '', 'flag art EAST (F29); was All East / AllEast'),
    ('ｵｰﾙｳｴｽﾄ', 'West', '', 'flag art WEST (F30); was All West / AllWest'),
    ('ﾄﾞﾘｰﾑｸﾗﾌﾞ (team menus)', 'Dream', '', 'flag art DREAM (F31) in the East / West / Dream menus; the mode name Dream Club keeps its English'),
    ('ｼﾞｬﾊﾟﾝｽﾀｰｽﾞ', 'Japanese Stars', '', 'BINDNAME art (S01)'),
    ('ｱｼﾞｱｽﾀｰｽﾞ', 'Asian Stars', '', 'BINDNAME art (S02)'),
    ('ｱﾌﾘｶｽﾀｰｽﾞ', 'African Stars', '', 'BINDNAME art (S03)'),
    ('北欧ｽﾀｰｽﾞ', 'N.Euro Stars', '', 'BINDNAME art N.EURO STARS (S04)'),
    ('ｽﾍﾟｲﾝﾚｼﾞｪﾝｽﾞ', 'Spanish Legends', '', 'BINDNAME art (S07)'),
    ('ﾌﾗﾝｽﾚｼﾞｪﾝｽﾞ', 'French Legends', '', 'BINDNAME art (S08)'),
    ('U.K. ﾚｼﾞｪﾝｽﾞ', 'English Legends', '', 'BINDNAME art ENGLISH LEGENDS (S09)'),
    ('ｵﾗﾝﾀﾞﾚｼﾞｪﾝｽﾞ', 'Hollander Legends', '', 'BINDNAME art HOLLANDER LEGENDS (S10)'),
    ('ｱﾙｾﾞﾝﾁﾝﾚｼﾞｪﾝｽﾞ', 'Argentine Legends', '', 'BINDNAME art (S11)'),
    ('ｲﾀﾘｱﾚｼﾞｪﾝｽﾞ', 'Italian Legends', '', 'BINDNAME art (S12)'),
    ('ﾄﾞｲﾂﾚｼﾞｪﾝｽﾞ', 'German Legends', '', 'BINDNAME art (S13)'),
    ('ﾌﾞﾗｼﾞﾙﾚｼﾞｪﾝｽﾞ', 'Brazilian Legends', '', 'BINDNAME art (S14)'),
    ('欧州ｽｰﾊﾟｰｽﾀｰｽﾞ / 南米ｽｰﾊﾟｰｽﾀｰｽﾞ', 'Euro Super Stars / S.Am. Super Stars', '', 'BINDNAME art (S15 / S16)'),
    ('欧州ｵｰﾙﾄﾞｽﾀｰｽﾞ / 南米ｵｰﾙﾄﾞｽﾀｰｽﾞ', 'Euro Old Stars / S.Am. Old Stars', '', 'BINDNAME art (S17 / S18)'),
    ('ﾜｰﾙﾄﾞｽﾀｰｽﾞ', 'The World Stars', '', 'BINDNAME art THE WORLD STARS (S19)'),
    ('ﾌｧﾝ感謝ﾏｯﾁ', 'Thanksgiving Match', '', 'banner THANKSGIVING MATCH (BINDMTCH 13924), plate THANKS GIVING; was Fan Appreciation / Fan Thanks / Thank-You Match'),
    ('ｱｼﾞｱｳｨﾅｰｽﾞｶｯﾌﾟ', 'Asia Winners Cup', '', 'banner ASIA WINNERS CUP (13913); was Asian Winners Cup / Asia Champ Cup'),
    ('ﾜｰﾙﾄﾞｳｨﾅｰｽﾞｶｯﾌﾟ', 'World Winners Cup', '', 'banner WORLD WINNERS CUP (13914); was World Champ Cup'),
    ('ｱｼﾞｱﾁｬﾚﾝｼﾞｶｯﾌﾟ', 'Asia Challenge Cup', '', 'banner ASIA CHALLENGE CUP (13927)'),
    ('ｱｼﾞｱﾄｰﾅﾒﾝﾄ', 'Asia Tournament', '', 'banner ASIA TOURNAMENT (13918); U22 Asia Tournament = banner UNDER22 ASIA TOURNAMENT (13935)'),
    ('ﾖｰﾛｯﾊﾟｶｯﾌﾟ', 'Europe Cup', '', 'banner EUROPE CUP (13920)'),
    ('欧州ﾁｬﾚﾝｼﾞﾘｰｸﾞ', 'Europe Challenge League', '', 'banner EUROPE CHALLENGE LEAGUE (13930)'),
    ('南米ﾁｬﾚﾝｼﾞﾘｰｸﾞ', 'South America Challenge League', '', 'banner SOUTH AMERICA CHALLENGE LEAGUE (13931)'),
    ('ﾌﾟﾚｼｰｽﾞﾝﾏｯﾁ', 'Preseason Match', '', 'banner PRESEASON MATCH (13938); was Pre-Season'),
    ('世界ｽﾎﾟｰﾂ大会', 'World Sports Festival', '', 'banner WORLD SPORTS FESTIVAL (13933 / 13934); was World Sports Games'),
    ('世界選抜対欧州選抜', 'World vs Europe', '', 'banner WORLD VS EUROPE (13912), plate WORLD VS EURO'),
]

lines = open(P, encoding='utf8', newline='').read().split(chr(10))
trail = lines[-1] == ''
if trail:
    lines = lines[:-1]
by_ja = {}
for i, ln in enumerate(lines):
    by_ja.setdefault(ln.split(T)[0], i)
edited = added = 0
for ja, en, short, note in ROWS:
    key = ja
    new = T.join([ja, en, short, note])
    # the legacy rows are keyed with the full-width / half-width spelling of the old corpus
    alias = {'ＦＣ東京': 'ＦＣ東京', '欧州選抜 / 世界選抜': '欧州選抜 / 世界選抜'}.get(key, key)
    if alias in by_ja:
        if lines[by_ja[alias]] != new:
            lines[by_ja[alias]] = new
            edited += 1
    else:
        lines.append(new)
        by_ja[alias] = len(lines) - 1
        added += 1
with open(P + '.s7n.tmp', 'w', encoding='utf8', newline='') as fh:
    fh.write(chr(10).join(lines) + (chr(10) if trail else ''))
os.replace(P + '.s7n.tmp', P)
print('edited', edited, 'added', added)
