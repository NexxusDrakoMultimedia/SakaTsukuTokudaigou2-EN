"""s7n rules: (ja NFKC substrings, en regex -> replacement) per club / special team / competition.
Source of the spellings: translation/clubwords_art.tsv F / S rows (re-read against the PNGs, 2026-11-12) and the banner art
GAME/BINDMTCH.BIN 13905-13941 / ETC_DATA/CPNAMES.TBD 296-300 for the competitions.
Rules are applied only to records whose Japanese contains one of the ja substrings (NFKC), so a person / word with the same
English letters is never touched.  Order inside a rule matters (first the long forms)."""
import re

# (name, [ja substrings], [(regex, replacement), ...])
RULES = [
    # ---- fixed J.League clubs: the spelling (and, where the logo shows it, the full form) of the logo art
    ('F02 Red Diamonds', ['レッズ', 'レッドダイヤモンズ'], [(r'\bReds\b', 'Red Diamonds')]),
    ('F03 JEF United', ['ジェフ'], [(r'\bJEF\b(?! United)', 'JEF United')]),
    ('F06 Yokohama F Marinos', ['マリノス'], [(r'Yokohama F\.? ?Marinos', 'Yokohama F Marinos'), (r'(?<!Yokohama )\bF\. ?Marinos\b', 'F Marinos'),
                                          (r'\bFMarinos\b', 'F Marinos')]),
    ('F07 Bellmare', ['ベルマーレ'], [(r'\bBelmare\b', 'Bellmare')]),
    ('F11 Purple Sanga', ['サンガ'], [(r'\bPurpleSanga\b', 'Purple Sanga')]),
    ('F14 Vissel Kobe', ['ヴィッセル', 'ビッセル'], [(r'\bVissel\b(?! Kobe)', 'Vissel Kobe')]),
    ('F15 Sanfrecce', ['サンフレッチェ'], [(r'\bSanfrec\b', 'Sanfrecce')]),
    ('F17 Consadole', ['コンサドーレ'], [(r'\bConsado\b', 'Consadole')]),
    ('F19 Montedio', ['モンテディオ'], [(r'\bMontedo\b', 'Montedio')]),
    ('F21 F.C.Tokyo', ['FC東京'], [(r'\bF\.? ?C\.? ?Tokyo\b', 'F.C.Tokyo')]),
    ('F22 Frontale', ['フロンターレ'], [(r'\bFrontal\b', 'Frontale')]),
    ('F25 Sagan Tosu', ['サガン'], [(r'\bSagan\b(?! Tosu)', 'Sagan Tosu')]),
    ('F27 Hollyhock', ['ホーリーホック'], [(r'\bHolyhok\b', 'Hollyhock'), (r'\bHollyHock\b', 'Hollyhock')]),
    ('F28 Yokohama FC', ['横浜FC'], [(r'\bYoko\.FC\b', 'Yokohama FC')]),
    # ---- all-star / select teams (flag art EAST / WEST / DREAM / EURO / WORLD, banner WORLD VS EUROPE)
    ('F29 East', ['オールイースト'], [(r'\bAll ?East\b', 'East')]),
    ('F30 West', ['オールウエスト', 'オールウェスト'], [(r'\bAll ?West\b', 'West')]),
    ('F33 World vs Europe (title)', ['世界選抜対欧州選抜', '世界選抜vs欧州選抜'], [(r'World XI vs\.? (?:European|Euro) XI', 'World vs Europe'),
                                                    (r'World XI v (?:European|Euro) XI', 'World vs Europe')]),
    ('F32/F33 the team', ['欧州選抜', '世界選抜'], [(r"\b([Tt]he) World XI\b", r'\1 World team'), (r"\b([Tt]he) (?:European|Euro) XI\b", r'\1 Euro team')]),
    ('F32 Euro', ['欧州選抜'], [(r'\bEuropean XI\b', 'Euro'), (r'\bEuro XI\b', 'Euro')]),
    ('F33 World', ['世界選抜'], [(r'\bWorld XI\b', 'World')]),
    # ---- special teams (BINDNAME art)
    ('S01 Japanese Stars', ['ジャパンスターズ'], [(r'\bJapan Stars\b', 'Japanese Stars')]),
    ('S02 Asian Stars', ['アジアスターズ'], [(r'\bAsia Stars\b', 'Asian Stars')]),
    ('S03 African Stars', ['アフリカスターズ'], [(r'\bAfrica Stars\b', 'African Stars')]),
    ('S04 N.Euro Stars', ['北欧スターズ'], [(r'\bNordic Stars\b', 'N.Euro Stars')]),
    ('S07 Spanish Legends', ['スペインレジェンズ'], [(r'\bSpain Legends\b', 'Spanish Legends')]),
    ('S08 French Legends', ['フランスレジェンズ'], [(r'\bFrance Legends\b', 'French Legends')]),
    ('S09 English Legends', ['U.K.レジェンズ', 'UKレジェンズ'], [(r'\bU\.K\. Legends\b', 'English Legends')]),
    ('S10 Hollander Legends', ['オランダレジェンズ'], [(r'\bNetherlands Legends\b', 'Hollander Legends')]),
    ('S11 Argentine Legends', ['アルゼンチンレジェンズ'], [(r'\bArgentina Legends\b', 'Argentine Legends')]),
    ('S12 Italian Legends', ['イタリアレジェンズ'], [(r'\bItaly Legends\b', 'Italian Legends')]),
    ('S13 German Legends', ['ドイツレジェンズ'], [(r'\bGermany Legends\b', 'German Legends')]),
    ('S14 Brazilian Legends', ['ブラジルレジェンズ'], [(r'\bBrazil Legends\b', 'Brazilian Legends')]),
    ('S15 Euro Super Stars', ['欧州スーパースターズ'], [(r'\bEurope Super ?[Ss]tars\b', 'Euro Super Stars')]),
    ('S16 S.Am. Super Stars', ['南米スーパースターズ'], [(r'\bSouth America Super ?[Ss]tars\b', 'S.Am. Super Stars')]),
    ('S17 Euro Old Stars', ['欧州オールドスターズ'], [(r'\bEurope Old [Ss]tars\b', 'Euro Old Stars')]),
    ('S18 S.Am. Old Stars', ['南米オールドスターズ'], [(r'\bSouth America Old [Ss]tars\b', 'S.Am. Old Stars')]),
    ('S19 The World Stars', ['ワールドスターズ'], [(r'(?<!The )(?<!the )\bWorld Stars\b', 'The World Stars')]),
    # ---- competitions with art (BINDMTCH banners, CPNAMES plates)
    ('C Thanksgiving Match', ['ファン感謝', 'サンクスギビング'], [(r'Fan Appreciation Match', 'Thanksgiving Match'), (r'Fan Thanks Match', 'Thanksgiving Match'),
                                                          (r'Thank-You Match', 'Thanksgiving Match')]),
    ('C Asia Winners Cup', ['アジアウィナーズ', 'アジアウイナーズ'], [(r"Asian Winners'? Cup", 'Asia Winners Cup'), (r'Asia Champ Cup', 'Asia Winners Cup')]),
    ('C World Winners Cup', ['ワールドウィナーズ', 'ワールドウイナーズ'], [(r"World Winners' Cup", 'World Winners Cup'), (r'World Champ Cup', 'World Winners Cup')]),
    ('C Asia Challenge Cup', ['アジアチャレンジ'], [(r'Asian Challenge Cup', 'Asia Challenge Cup')]),
    ('C Asia Tournament', ['アジアトーナメント'], [(r'U2[12] Asian Tournament', 'U22 Asia Tournament'), (r'Asian Tournament', 'Asia Tournament')]),
    ('C U23 Inter League', ['インターリーグ'], [(r'U2[12] Inter-League', 'U23 Inter League')]),
    ('C Europe Cup', ['ヨーロッパカップ'], [(r'\bThe European Cup\b', 'The Europe Cup'), (r'\bEuropean Cup\b', 'Europe Cup')]),
    ('C Europe Challenge League', ['欧州チャレンジ'], [(r'\bEuropean Challenge League\b', 'Europe Challenge League')]),
    ('C South America Challenge League', ['南米チャレンジ'], [(r'\bSouth American Challenge League\b', 'South America Challenge League')]),
    ('C South America Cup', ['南アメリカカップ', 'サウスアメリカカップ', '南米カップ'], [(r'\bSouth American Cup\b', 'South America Cup')]),
    ('C Preseason Match', ['プレシーズン'], [(r'Pre-[Ss]eason Match', 'Preseason Match')]),
    ('C World Sports Festival', ['世界スポーツ大会'], [(r'World Sports Games', 'World Sports Festival'), (r'World Sports Finals', 'World Sports Festival Finals'),
                                                  (r'World Games', 'World Sports Festival'), (r'World Sports Qualif', 'World Sports Festival Qualif')]),
    ('C Thanksgiving (label)', ['ファン感謝'], [(r'\bFan Thanks\b(?! Match)', 'Thanksgiving')]),
    ('F06 Yokohama F Marinos (clip)', ['Fマリノス'], [(r'^F Marinos', 'Yokohama F Marinos')]),
    ('C South America Challenge League (cut)', ['南米チャレンジ'], [(r'South American Challenge\b(?! League)', 'South America Challenge League')]),
    ('C Preseason (label)', ['プレシーズンマッチ'], [(r'^Pre-season$', 'Preseason')]),
    ('C World Team Match', ['世界選抜戦'], [(r'World XI Match', 'World Team Match')]),
]

import unicodedata


def norm_ja(t):
    t = unicodedata.normalize('NFKC', t)
    for ch in ('・', '.', ' ', '　'):
        t = t.replace(ch, '')
    return t


def ws(rx):
    """literal blanks of a pattern also match a line break of the record"""
    return re.compile(rx.replace(' ', '[ \n]'))


RULES_C = [(n, [norm_ja(j) for j in ja], [(ws(p), r) for p, r in pats]) for n, ja, pats in RULES]


# records chosen by the exact Japanese label AND the size of the pointer table they live in (the team menus East / West / Dream);
# the prose "Dream Club" (the mode) keeps its English
CTX_RULES = [('F31 Dream', 'ﾄﾞﾘｰﾑｸﾗﾌﾞ', re.compile(r'tbl@[0-9a-f]+\[\d+/(?:3|8)\]'), 'Dream')]
