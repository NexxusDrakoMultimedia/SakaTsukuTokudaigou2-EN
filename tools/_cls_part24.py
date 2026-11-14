"""One-off: write build/tex/classify/part_24.json for contact sheets 24-27 (manual classification)."""
import json, os

m = json.load(open('build/tex/sheets/sheet_map.json'))
JA = {
    '00803_ENDOPT.TBD_1': dict(
        japanese_text='セーブして終了 / データ作成 / オプション / バックアップ / EXIT (5 stacked labels; EXIT is Latin)',
        english_suggestion='Save & Quit / Data Making / Options / Backup / EXIT',
        kind='menu_button', priority=1,
        region=[0, 0, 232, 228],
        notes='Overlay label sheet for the end/option menu; rows approx y 2-36, 50-84, 98-132, 146-180 (JA), 195-225 (EXIT). '
              'Gold ARGB4444 twiddled 256x256, transparent background, drop shadow. Sibling #802 (END / OPTION) and #804 (DATA MAKING) '
              'are already English button plates. Keep row pitch 48px so UV rects still match. Check capacity: "Save & Quit" fits 232px at ~28px font.'),
    '00805_ENDOPT.TBD_3': dict(
        japanese_text='フリー選手 / 対戦クラブ / レジェンドクラブ / EXIT',
        english_suggestion='Free Agents / Rival Clubs / Legend Clubs / EXIT',
        kind='menu_button', priority=2,
        region=[0, 0, 250, 182],
        notes='Same ENDOPT.TBD style as #803, rows approx y 2-36, 50-84, 98-132 (JA), 148-180 (EXIT). 4th texture of the table. '
              'Widest label レジェンドクラブ spans ~248px, so "Legend Clubs" needs about the same width; use condensed font if needed. '
              'Meaning INFERRED (list-select categories for free players / opponent clubs / legend clubs); verify against string pools for wording.'),
}
out = []
for sname, d in m['sheets'].items():
    num = int(sname.split('_')[1])
    if num not in (24, 25, 26, 27):
        continue
    for it in d['items']:
        tid = it['id']
        e = dict(id=tid, sheet=sname, has_japanese=False, japanese_text='', english_suggestion='',
                 kind='other', priority=3, region=None, notes='')
        if tid in JA:
            e.update(JA[tid]); e['has_japanese'] = True
        elif tid.startswith('00781'):
            e['notes'] = 'Latin italic lyric text ("I was born to go to HELL mom, so let me go!"), already English. Easter egg, no action.'
        elif tid.startswith('00787'):
            e['notes'] = 'Tiny Latin/garbled mark on a logo-like shape; no Japanese.'
        elif tid in ('00802_ENDOPT.TBD_0', '00804_ENDOPT.TBD_2'):
            e['notes'] = 'Button plates with Latin "END / OPTION" and "DATA MAKING"; already English.'
        elif 'ClubHouse_Bch01.tbd_7' in tid or 'Bch05.tbd_2' in tid:
            e['notes'] = 'Latin plaques (ClubHouse01..04 / ClubHouse05a, Special, 05b, Ground); no Japanese.'
        elif 'dr_tt0' in tid:
            e['notes'] = 'Trophy/plaque 3D texture; no readable text.'
        out.append(e)
os.makedirs('build/tex/classify', exist_ok=True)
json.dump(out, open('build/tex/classify/part_24.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), sum(1 for e in out if e['has_japanese']))
