"""s7n: edit translation/refit/forms.tsv for the names2 pass (idempotent).  Source data of tools/re/rfit_gen.py.

usage: python -I -X utf8 tools/re/s7n_forms.py
* J.League clubs: the logo-art forms (Red Diamonds, JEF United, Vissel Kobe, Sagan Tosu, F.C.Tokyo, Hollyhock, Yokohama F Marinos)
  with the previous short form as the fallback that the generator tries when the long one does not fit the column (pixel check)
* East / West rows removed (the DB itself now holds East / West; an overlay would put 'All East' back)
* competitions: Asia / World Winners Cup, World Sports Festival, Thanksgiving, special teams of the CHALDANI / CHALMODE lists
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'translation', 'refit', 'forms.tsv')
T = chr(9)


def row(cls, ja, en, sel, why):
    return T.join([cls, ja, en, sel, why])


text = open(P, encoding='utf8', newline='').read()
lines = text.split(chr(10))
out = []
removed = []
for ln in lines:
    p = ln.split(T)
    if len(p) >= 4 and p[0] == 'jclub' and p[1] in ('ｵｰﾙｳｴｽﾄ', 'ｵｰﾙｲｰｽﾄ'):
        removed.append(ln)
        continue
    if len(p) >= 4 and p[0] == 'jclub' and p[1] == 'ﾎｰﾘｰﾎｯｸ':
        ln = row('jclub', 'ﾎｰﾘｰﾎｯｸ', 'Hollyhock', 'n<=20', 'logo art HOLLYHOCK (clubwords_art F27); Mito Hollyhock')
    if len(p) >= 4 and p[0] == 'jclub' and p[3] == 'n<=14':
        p[3] = 'n<=20'
        ln = T.join(p)
    out.append(ln)

new_j = [
    row('jclub', 'ﾚｯｽﾞ', 'Red Diamonds | Reds', 'n<=20', 'logo art Red Diamonds (F02); Reds is the slot cut'),
    row('jclub', 'ｼﾞｪﾌ', 'JEF United | JEF', 'n<=20', 'logo art JEF UNITED (F03); JEF is the slot cut'),
    row('jclub', 'ｳﾞｨｯｾﾙ', 'Vissel Kobe | Vissel', 'n<=20', 'logo art VISSEL KOBE (F14)'),
    row('jclub', 'ｻｶﾞﾝ', 'Sagan Tosu | Sagan', 'n<=20', 'logo art SAGAN TOSU (F25)'),
    row('jclub', 'ﾏﾘﾉｽ', 'Yokohama F Marinos | F Marinos', 'n<=20', 'logo art Yokohama F Marinos (F06, no period); Marinos is the slot cut'),
    row('jclub', 'FC東京', 'F.C.Tokyo | FC Tokyo | FCTokyo', 'fmt=ptr', 'logo art F.C.TOKYO (F21); FCTokyo is the 8-byte slot cut'),
]
new_o = [
    row('other', 'ｱｼﾞｱｳｨﾅｰｽﾞｶｯﾌﾟ', 'Asia Winners Cup | Asia Champ Cup', '*', 'banner ASIA WINNERS CUP (BINDMTCH 13913), plate ASIA WIN CUP'),
    row('other', 'ｱｼﾞｱｳｲﾅｰｽﾞｶｯﾌﾟ', 'Asia Winners Cup | Asia Champ Cup', '*', 'banner ASIA WINNERS CUP (BINDMTCH 13913)'),
    row('other', 'ﾜｰﾙﾄﾞｳｨﾅｰｽﾞｶｯﾌﾟ', 'World Winners Cup | World Champ Cup', '*', 'banner WORLD WINNERS CUP (BINDMTCH 13914)'),
    row('other', 'ﾜｰﾙﾄﾞｳｲﾅｰｽﾞｶｯﾌﾟ', 'World Winners Cup | World Champ Cup', '*', 'banner WORLD WINNERS CUP (BINDMTCH 13914)'),
    row('other', '世界ｽﾎﾟｰﾂ大会', 'World Sports Festival | Sports Festival | World Games', '*', 'banner WORLD SPORTS FESTIVAL (BINDMTCH 13933 / 13934)'),
    row('other', '世界ｽﾎﾟｰﾂ大会予選', 'World Sports Festival Qual. | Sports Festival Qual. | Sports Fest. Qual. | World Games Qual.', '*', 'banner WORLD SPORTS FESTIVAL QUALIFY (13933)'),
    row('other', '世界ｽﾎﾟｰﾂ大会予選ﾘｰｸﾞ', 'World Sports Festival Qualif. | Sports Festival Qualif. | World Sports Qualif.', '*', 'banner WORLD SPORTS FESTIVAL QUALIFY (13933)'),
    row('other', '世界ｽﾎﾟｰﾂ大会決勝ﾄｰﾅﾒﾝﾄ', 'World Sports Festival Finals | Sports Festival Finals | World Sports Finals', '*', 'banner WORLD SPORTS FESTIVAL (13934)'),
    row('other', 'ﾌｧﾝ感謝ﾏｯﾁ', 'Thanksgiving Match | Thanksgiving | Fan Thanks', '*', 'banner THANKSGIVING MATCH (BINDMTCH 13924), plate THANKS GIVING'),
    row('other', 'Ｕ.Ｋ.レジェンズ', 'English Legends | U.K. Legends', '*', 'BINDNAME art ENGLISH LEGENDS (S09)'),
    row('other', 'ワールドスターズ', 'The World Stars | World Stars', '*', 'BINDNAME art THE WORLD STARS (S19)'),
    row('other', 'ジャパン・スターズ', 'Japanese Stars | Japan Stars', '*', 'BINDNAME art JAPANESE STARS (S01)'),
    row('other', 'アジア・スターズ', 'Asian Stars | Asia Stars', '*', 'BINDNAME art ASIAN STARS (S02)'),
    row('other', 'アフリカ・スターズ', 'African Stars | Africa Stars', '*', 'BINDNAME art AFRICAN STARS (S03)'),
    row('other', 'スペイン・レジェンズ', 'Spanish Legends | Spain Legends', '*', 'BINDNAME art SPANISH LEGENDS (S07)'),
    row('other', 'イタリア・レジェンズ', 'Italian Legends | Italy Legends', '*', 'BINDNAME art ITALIAN LEGENDS (S12)'),
    row('other', 'ブラジル・レジェンズ', 'Brazilian Legends | Brazil Legends', '*', 'BINDNAME art BRAZILIAN LEGENDS (S14)'),
]
# idempotent: drop previous rows of the same (cls, ja) before appending
keys = {(r.split(T)[0], r.split(T)[1]) for r in new_j + new_o}
out = [ln for ln in out if not (len(ln.split(T)) >= 4 and (ln.split(T)[0], ln.split(T)[1]) in keys)]
# insert the jclub rows right after the last jclub row, the cups rows after the last `other` cup row
last_j = max(i for i, ln in enumerate(out) if ln.startswith('jclub' + T))
out[last_j + 1:last_j + 1] = new_j
last_o = max(i for i, ln in enumerate(out) if ln.startswith('other' + T))
out[last_o + 1:last_o + 1] = new_o
with open(P + '.s7n.tmp', 'w', encoding='utf8', newline='') as fh:
    fh.write(chr(10).join(out))
os.replace(P + '.s7n.tmp', P)
print('removed', len(removed), 'jclub added', len(new_j), 'other added', len(new_o))
