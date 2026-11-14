"""Build translation/clubwords_art.tsv: club-word logo art (GAME/ALLPNAME.BIN, texture ids 10824..10877) vs the current DB.
Pool index k (1..54) = ALLPNAME texture 10823+k = HOMETOWN pool tbl@422c8[k] = CLUBEDIT message table 0x1eb8c[k].
Reads only; writes the TSV (club-word rows, then the fixed-club / special-team rows from cw_fixed_rows()).
usage: python -I -X utf8 tools/re/cw_clubwords_art.py"""
import json, glob, re, struct, io, sys

# (art spelling as printed, ASCII form for strings, language of the word as printed, meaning, confidence, note)
ART = {
 1: ("Tempest", "Tempest", "English", "great storm", "high", ""),
 2: ("VULLCAN", "Vullcan", "English/Latin (Vulcan)", "volcano (Roman god of fire)", "spelling high / language medium", "Banner subtitle reads LEGEND OF VICTORY MOUNTAINS. Two L as the user reported. Not German (German is Vulkan); the original JP message claims German."),
 3: ("Avalanche", "Avalanche", "English", "avalanche (a rush of snow)", "high", "9 letters: does not fit an 8-byte pool slot (7 chars); DB pool has Valanch."),
 4: ("STING", "Sting", "English", "a sharp blow", "high", ""),
 5: ("MONOLITH", "Monolith", "English", "monolith / solid rock", "high", "Greek-looking caption under the logo is decorative noise. 8 letters: over a 7-char slot; DB pool has Monoris."),
 6: ("Bandits", "Bandits", "English", "outlaws", "high", ""),
 7: ("BLITZ", "Blitz", "English (from German lightning)", "to attack suddenly", "high", ""),
 8: ("SCHWARZ", "Schwarz", "German", "black", "high", ""),
 9: ("BLAZE", "Blaze", "English", "flames", "high", ""),
 10: ("Blues", "Blues", "English", "blue", "high", "Existing DB pool string Bruce (about 91 records / 46 files) is wrong."),
 11: ("SHADOWS", "Shadows", "English", "shadow", "high", ""),
 12: ("Mantis", "Mantis", "English", "mantis", "high", ""),
 13: ("GEIST", "Geist", "German", "spirit", "high", ""),
 14: ("Topolino", "Topolino", "Italian", "little mouse", "high", "8 letters: over a 7-char slot; DB pool has Topolin."),
 15: ("APE", "Ape", "Italian", "bee", "high", "Italian ape = bee (the JP message says French and the DB says Abeille; the logo is APE with a bee-striped P)."),
 16: ("BALLENA", "Ballena", "Spanish", "whale", "high", "DB pool Bajena is wrong."),
 17: ("Blau Wiese", "Blau Wiese", "German", "blue meadow", "high", "Two words in the art (Blau / Wiese). 10 chars incl. blank: fits the 12-byte slot only."),
 18: ("CIELO", "Cielo", "Spanish", "sky", "high", "Also Italian. 5 letters but the pool slot is 4 bytes (3 chars): DB pool has Sie."),
 19: ("COLMILLO", "Colmillo", "Spanish", "fang", "high", "Fang drawn between the letters. 8 letters: over a 7-char slot; DB pool Colmijo."),
 20: ("Corriente", "Corriente", "Spanish", "current (of water)", "high", "Caption: the super football club. 9 letters: over a 7-char slot; DB pool Corient."),
 21: ("ELF SCHRITT", "Elf Schritt", "German", "eleven steps / 11 footsteps", "high", "Two words in the art. 11 chars: fits the 12-byte slot exactly."),
 22: ("Espada", "Espada", "Spanish", "sword", "high", ""),
 23: ("GLÜCK", "Gluck", "German", "luck / good fortune", "high", "Umlaut in the art; ASCII fold Gluck (Glueck is the German transliteration, 6 chars)."),
 24: ("HERENCIA", "Herencia", "Spanish", "legacy / inheritance", "high", "The JP message says German (wrong). 8 letters: over a 7-char slot; DB pool Erencia."),
 25: ("infini", "Infini", "French", "infinity", "high", "Stylised INFINI with a ring around the F. DB pool Anfini is wrong."),
 26: ("LAMPO", "Lampo", "Italian", "lightning / flash", "high", ""),
 27: ("Leone", "Leone", "Italian", "lion", "high", ""),
 28: ("LYNX", "Lynx", "French/English (same spelling)", "lynx", "high", "DB pool Lanks is wrong."),
 29: ("MÉGÈRE", "Megere", "French", "shrew / termagant", "high", "Accents on both E; caption PRO SOCCER CLUB. DB pool Mejel is wrong."),
 30: ("MISTRAL", "Mistral", "French (Provencal)", "mistral (cold strong wind)", "high", ""),
 31: ("Panthera", "Panthera", "Latin (genus Panthera)", "panther", "medium", "Paw print replaces the dot over the E. The JP message claims Spanish (Pantera); the art says Panthera (8 letters: over a 7-char slot)."),
 32: ("RICCIO", "Riccio", "Italian", "hedgehog", "high", "DB pool Richo is wrong."),
 33: ("ROSA", "Rosa", "Spanish", "rose", "high", "Also Italian/Portuguese. 4 letters but the pool slot is 4 bytes (3 chars): DB pool has Ros."),
 34: ("UNICORN", "Unicorn", "English", "unicorn (one-horned mythical beast)", "high", ""),
 35: ("Aurora", "Aurora", "Italian", "dawn", "high", "Also Latin/Spanish."),
 36: ("AVANZARE", "Avanzare", "Italian", "to advance", "high", "The JP message says Spanish (Spanish is avanzar)."),
 37: ("EL TORO", "El Toro", "Spanish", "the bull", "high", "Two words in the art; 7 chars. DB pool Eltoro."),
 38: ("ESTELLA", "Estella", "Spanish (name from Latin stella)", "star", "medium", "Logo reads ESTELLA, not Estrella (Spanish for star is estrella). Estella = the star-name (Latin stella)."),
 39: ("FELIZ", "Feliz", "Spanish", "happy / fortunate", "high", "Also Portuguese. DB pool Felis is wrong."),
 40: ("FORTE", "Forte", "Italian", "strong", "high", "Caption: Powerful football club. Original JP message says Latin (fortis)."),
 41: ("GABE", "Gabe", "German", "gift / talent", "high", "DB pool Garbe is wrong."),
 42: ("Galeos", "Galeos", "Greek", "shark", "high", ""),
 43: ("GIURARE", "Giurare", "Italian", "to swear", "high", "DB pool Jurale is wrong."),
 44: ("IRIS", "Iris", "Greek", "rainbow", "high", "Rainbow-striped letters. DB pool Ilis is wrong."),
 45: ("LUMIERE", "Lumiere", "French", "light", "high", "No accent drawn in the art."),
 46: ("mythos", "Mythos", "German/Greek", "myth", "high", "Lower-case in the art."),
 47: ("PLAISIR", "Plaisir", "French", "pleasure", "high", ""),
 48: ("RAFALE", "Rafale", "French", "gust (of wind)", "high", "DB pool Rafal is wrong."),
 49: ("RENDIR", "Rendir", "Spanish", "to defeat / subdue", "high", "RAE: rendir = vencer, someter (also to yield)."),
 50: ("Salire", "Salire", "Italian", "to climb", "high", ""),
 51: ("SFIDA", "Sfida", "Italian", "challenge", "high", ""),
 52: ("STOLZ", "Stolz", "German", "pride", "high", "DB pool Sturz (= fall) is wrong. Seen on the kit chest in build/emu/live3.png."),
 53: ("TIGRE", "Tigre", "Italian", "tiger", "high", "Same spelling in Spanish/French/Portuguese."),
 54: ("VALENTÍA", "Valentia", "Spanish", "courage / bravery", "high", "Accent on the I in the art; ASCII fold Valentia."),
}
LANG_JA = {'英語': 'English', 'ドイツ語': 'German', 'イタリア語': 'Italian', 'フランス語': 'French', 'スペイン語': 'Spanish',
           'ラテン語': 'Latin', 'ギリシャ語': 'Greek', 'フランスの': 'French', '神話': 'myth (Unicorn)'}

recs = {}
for l in open('translation/FLOW_PRG__CLUBEDIT.BIN.jsonl', encoding='utf8'):
    r = json.loads(l); recs[int(r['id'].split('#')[1], 16)] = r
d = open('extracted/FLOW_PRG/CLUBEDIT.BIN', 'rb').read()
msg = {}
for k in range(1, 55):
    v = struct.unpack_from('<I', d, 0x1eb8c + 4*k)[0] - 0x8c2d0000
    msg[k] = recs[v]
pool = {}
for l in open('translation/FLOW_PRG__HOMETOWN.BIN.jsonl', encoding='utf8'):
    r = json.loads(l)
    m = re.search(r'tbl@422c8\[(\d+)/55\]', r.get('ctx') or '')
    if m: pool[int(m.group(1))] = r

allrecs = []
for f in glob.glob('translation/*.jsonl'):
    for l in open(f, encoding='utf8'):
        r = json.loads(l); allrecs.append((f, r))

hdr = ['index', 'katakana_ja', 'art_spelling', 'ascii_for_strings', 'language_of_origin', 'meaning', 'confidence', 'texture_id',
       'flag_texture_id', 'db_pool_en', 'db_pool_slot_bytes', 'fits_slot', 'db_message_word', 'db_message_language', 'ja_message_language',
       'differs_from_db', 'n_records_ja', 'n_files_ja', 'note']
rows = []
for k in range(1, 55):
    art, asc, lang, mean, conf, note = ART[k]
    p = pool[k]; ja = p['ja']; pen = p['en']; slot = p['slot']
    m = msg[k]
    mw = re.search(r'@Y/(.+?)@', m['en']); mw = mw.group(1) if mw else ''
    ml = re.search(r' is (?:a |the )?(\w+)(?: for|\s+@K)', m['en'])
    ml = ml.group(1) if ml else ''
    jl = ''
    for key, val in LANG_JA.items():
        if key in m['ja']: jl = val; break
    n = [(f, r) for f, r in allrecs if ja in r['ja']]
    diff = []
    if pen != asc: diff.append('pool')
    if mw != asc: diff.append('message')
    if ml and ml.lower() not in lang.lower(): diff.append('language')
    maxc = slot - 1
    fits = 'yes' if len(asc) <= maxc else 'NO(%d>%d)' % (len(asc), maxc)
    rows.append([k, ja, art, asc, lang, mean, conf, 10823 + k, 13521 + k, pen, slot, fits, mw, ml, jl,
                 '+'.join(diff) or 'same', len(n), len(set(f for f, _ in n)), note])

# fixed clubs / special teams: (id, ja key in DB, art spelling, ascii, art texture, flag texture, note)
FIXED_SRC = [
 ('F01', 'ｱﾝﾄﾗｰｽﾞ', 'Antlers', 'Antlers', 10730, 10481, 'caption KASHIMA'),
 ('F02', 'ﾚｯｽﾞ', 'Red Diamonds', 'Red Diamonds', 10731, 10482, 'DB uses the short form Reds'),
 ('F03', 'ｼﾞｪﾌ', 'JEF UNITED', 'JEF United', 10732, 10483, ''),
 ('F04', 'ﾚｲｿﾙ', 'Reysol', 'Reysol', 10733, 10484, 'caption KASHIWA'),
 ('F05', 'ｳﾞｪﾙﾃﾞｨ', 'Verdy', 'Verdy', 10734, 10485, 'caption FC NIPPON'),
 ('F06', 'F･ﾏﾘﾉｽ', 'Yokohama F Marinos', 'Yokohama F Marinos', 10735, 10486, 'DB Marinos'),
 ('F07', 'ﾍﾞﾙﾏｰﾚ', 'Bellmare', 'Bellmare', 10736, 10487, 'DB Belmare is a misspelling (Bellmare Hiratsuka)'),
 ('F08', 'ｴｽﾊﾟﾙｽ', 'S-PULSE', 'S-Pulse', 10737, 10488, 'caption SHIMIZU'),
 ('F09', 'ｼﾞｭﾋﾞﾛ', 'JÚBILO', 'Jubilo', 10738, 10489, 'accent in the art; caption IWATA'),
 ('F10', 'ｸﾞﾗﾝﾊﾟｽ', 'Grampus', 'Grampus', 10739, 10490, 'flag says Grampus Eight; caption NAGOYA'),
 ('F11', 'ﾊﾟｰﾌﾟﾙｻﾝｶﾞ', 'Purple Sanga', 'Purple Sanga', 10740, 10491, 'DB PurpleSanga has no space (slot width)'),
 ('F12', 'ｶﾞﾝﾊﾞ', 'GAMBA', 'Gamba', 10741, 10492, 'caption OSAKA'),
 ('F13', 'ｾﾚｯｿ', 'Cerezo', 'Cerezo', 10742, 10493, 'caption OSAKA'),
 ('F14', 'ｳﾞｨｯｾﾙ', 'VISSEL KOBE', 'Vissel Kobe', 10743, 10494, 'DB Vissel'),
 ('F15', 'ｻﾝﾌﾚｯﾁｪ', 'SANFRECCE', 'Sanfrecce', 10744, 10495, 'DB Sanfrec is a truncation; caption HIROSHIMA FC'),
 ('F16', 'ｱﾋﾞｽﾊﾟ', 'Avispa', 'Avispa', 10745, 10496, 'caption FUKUOKA'),
 ('F17', 'ｺﾝｻﾄﾞｰﾚ', 'Consadole', 'Consadole', 10746, 10497, 'DB Consado is a truncation (slot width); caption SAPPORO'),
 ('F18', 'ﾍﾞｶﾞﾙﾀ', 'VEGALTA', 'Vegalta', 10747, 10498, 'caption SENDAI'),
 ('F19', 'ﾓﾝﾃﾃﾞｨｵ', 'Montedio', 'Montedio', 10748, 10499, 'DB Montedo is a truncation; caption YAMAGATA'),
 ('F20', 'ｱﾙﾃﾞｨｰｼﾞｬ', 'Ardija', 'Ardija', 10749, 10500, 'caption OMIYA'),
 ('F21', 'FC東京', 'F.C.TOKYO', 'F.C.Tokyo', 10750, 10501, 'DB FCTokyo'),
 ('F22', 'ﾌﾛﾝﾀｰﾚ', 'Frontale', 'Frontale', 10751, 10502, 'DB Frontal is a truncation; caption KAWASAKI'),
 ('F23', 'ｳﾞｧﾝﾌｫｰﾚ', 'VENTFORET', 'Ventforet', 10752, 10503, 'caption KOFU'),
 ('F24', 'ｱﾙﾋﾞﾚｯｸｽ', 'Albirex', 'Albirex', 10753, 10504, 'caption NIIGATA'),
 ('F25', 'ｻｶﾞﾝ', 'SAGANTOSU', 'Sagan Tosu', 10754, 10505, 'art reads SAGANTOSU (G looks like S at this size); DB Sagan'),
 ('F26', 'ﾄﾘﾆｰﾀ', 'Trinita', 'Trinita', 10755, 10506, ''),
 ('F27', 'ﾎｰﾘｰﾎｯｸ', 'Hollyhock', 'Hollyhock', 10756, 10507, 'DB Holyhok is a misspelling; caption FC MITO / IBARAKI'),
 ('F28', '横浜FC', 'YOKOHAMA FC', 'Yokohama FC', 10757, 10508, 'DB Yoko.FC (short form)'),
 ('F29', 'ｵｰﾙｲｰｽﾄ', 'EAST', 'East', 0, 10509, 'flag art only (ALLFLAGS); DB AllEast; Japanese logo text in ALLLOGOS'),
 ('F30', 'ｵｰﾙｳｴｽﾄ', 'WEST', 'West', 0, 10510, 'flag art only; DB AllWest'),
 ('F31', 'ﾄﾞﾘｰﾑｸﾗﾌﾞ', 'DREAM', 'Dream', 0, 10511, 'flag art DREAM (10511) and Dream (10512); DB Dream Club'),
 ('F32', '欧州選抜', 'EURO', 'Euro', 0, 10513, 'flag art only; DB European XI'),
 ('F33', '世界選抜', 'WORLD', 'World', 0, 10514, 'flag art only; DB World XI'),
 ('S01', 'ｼﾞｬﾊﾟﾝｽﾀｰｽﾞ', 'JAPANESE STARS', 'Japanese Stars', 14024, 0, 'BINDNAME art; DB Japan Stars'),
 ('S02', 'ｱｼﾞｱｽﾀｰｽﾞ', 'ASIAN STARS', 'Asian Stars', 14025, 0, 'DB Asia Stars'),
 ('S03', 'ｱﾌﾘｶｽﾀｰｽﾞ', 'AFRICAN STARS', 'African Stars', 14026, 0, 'DB Africa Stars'),
 ('S04', '北欧ｽﾀｰｽﾞ', 'N.EURO STARS', 'N.Euro Stars', 14027, 0, 'DB Nordic Stars'),
 ('S05', 'ﾊﾞﾙｶﾝｽﾀｰｽﾞ', 'BALKAN STARS', 'Balkan Stars', 14028, 0, ''),
 ('S06', 'サカつくｽﾀｰｽﾞ', 'さかつく STARS', 'Sakatsuku Stars', 14029, 0, 'hiragana in the art; DB Sakatsuku Stars'),
 ('S07', 'ｽﾍﾟｲﾝﾚｼﾞｪﾝｽﾞ', 'SPANISH LEGENDS', 'Spanish Legends', 14030, 0, 'DB Spain Legends'),
 ('S08', 'ﾌﾗﾝｽﾚｼﾞｪﾝｽﾞ', 'FRENCH LEGENDS', 'French Legends', 14031, 0, 'DB France Legends'),
 ('S09', 'U.K. ﾚｼﾞｪﾝｽﾞ', 'ENGLISH LEGENDS', 'English Legends', 14032, 0, 'DB U.K. Legends'),
 ('S10', 'ｵﾗﾝﾀﾞﾚｼﾞｪﾝｽﾞ', 'HOLLANDER LEGENDS', 'Hollander Legends', 14033, 0, 'DB Netherlands Legends'),
 ('S11', 'ｱﾙｾﾞﾝﾁﾝﾚｼﾞｪﾝｽﾞ', 'ARGENTINE LEGENDS', 'Argentine Legends', 14034, 0, 'DB Argentina Legends'),
 ('S12', 'ｲﾀﾘｱﾚｼﾞｪﾝｽﾞ', 'ITALIAN LEGENDS', 'Italian Legends', 14035, 0, 'DB Italy Legends'),
 ('S13', 'ﾄﾞｲﾂﾚｼﾞｪﾝｽﾞ', 'GERMAN LEGENDS', 'German Legends', 14036, 0, 'DB Germany Legends'),
 ('S14', 'ﾌﾞﾗｼﾞﾙﾚｼﾞｪﾝｽﾞ', 'BRAZILIAN LEGENDS', 'Brazilian Legends', 14037, 0, 'DB Brazil Legends'),
 ('S15', '欧州ｽｰﾊﾟｰｽﾀｰｽﾞ', 'euro Super stars', 'Euro Super Stars', 14038, 0, 'DB Europe Super Stars'),
 ('S16', '南米ｽｰﾊﾟｰｽﾀｰｽﾞ', 'S.Am. Super stars', 'S.Am. Super Stars', 14039, 0, 'DB South America Super Stars'),
 ('S17', '欧州ｵｰﾙﾄﾞｽﾀｰｽﾞ', 'EURO Old stars', 'Euro Old Stars', 14040, 0, 'DB Europe Old Stars'),
 ('S18', '南米ｵｰﾙﾄﾞｽﾀｰｽﾞ', 'S.AM. Old stars', 'S.Am. Old Stars', 14041, 0, 'DB South America Old Stars'),
 ('S19', 'ﾜｰﾙﾄﾞｽﾀｰｽﾞ', 'THE WORLD STARS', 'The World Stars', 14042, 0, 'DB World Stars'),
 ('S20', 'ﾄﾞﾘｰﾑｽﾀｰｽﾞ', 'DREAM STARS', 'Dream Stars', 14043, 0, ''),
 ('S21', 'ｳｨﾝｸﾞﾌｧｰﾑｽﾞ', 'Wing Farms', 'Wing Farms', 14044, 0, ''),
]
for (fid, jakey, art, asc, tid, ftid, note) in FIXED_SRC:
    hits = [r for f, r in allrecs if r['ja'].strip() == jakey and (r.get('fmt') in ('hwptr', 'bcast', None) or True)]
    # prefer the CLUBEDIT hwptr record (has a slot), else the first record
    best = None
    for f, r in allrecs:
        if r['ja'].strip() == jakey and 'CLUBEDIT' in f: best = r; break
    if best is None and hits: best = hits[0]
    pen = best['en'] if best else ''
    slot = best.get('slot') if best else ''
    nrec = len([1 for f, r in allrecs if jakey in r['ja']])
    nfil = len(set(f for f, r in allrecs if jakey in r['ja']))
    same = 'same' if pen == asc else 'differs'
    rows.append([fid, jakey, art, asc, 'proper name', '', 'high' if fid[0] == 'F' and tid else 'medium', tid or '', ftid or '',
                 pen, slot if slot else '', '', '', '', '', same, nrec, nfil, note])

out = io.StringIO()
out.write('\t'.join(hdr) + '\n')
for r in rows:
    out.write('\t'.join(str(x) for x in r) + '\n')
open('translation/clubwords_art.tsv', 'w', encoding='utf8', newline='\n').write(out.getvalue())
print(len(rows), 'rows written')
for r in rows:
    if r[15] != 'same' or r[11] != 'yes':
        print(r[0], r[2], '| pool', r[9], r[10], '| msg', r[12], r[13], '| ja', r[14], '|', r[15], r[11], r[16])
