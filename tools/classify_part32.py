"""Build build/tex/classify/part_32.json for contact sheets 32-35 (manual visual classification)."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
smap = json.load(open(os.path.join(ROOT, 'build/tex/sheets/sheet_map.json'), encoding='utf-8'))['sheets']

JP = {
    2003: dict(japanese_text='クラブハウス', english_suggestion='Clubhouse', kind='menu_button', priority=2,
               region=[0, 0, 128, 32],
               notes='128x32 cyan label plate, black bold katakana, ESTAICON.ZAR zo_club.tbd_1. Establishment-menu caption under the Clubhouse icon (paired with LEVEL UP #2002/#2004). 9 chars JP -> "Clubhouse" 9 chars fits.'),
    2006: dict(japanese_text='グラウンド', english_suggestion='Grounds', kind='menu_button', priority=2,
               region=[0, 0, 128, 32],
               notes='128x32 cyan label plate, ESTAICON.ZAR zo_grou.tbd_1. Help text uses グラウンド for the training ground; "Grounds" fits width (alt "Training Ground" too long for 128px at this font size).'),
    2009: dict(japanese_text='スタジアム', english_suggestion='Stadium', kind='menu_button', priority=2,
               region=[0, 0, 128, 32],
               notes='128x32 cyan label plate, ESTAICON.ZAR zo_stad.tbd_1.'),
}
NOTES = {
    2002: 'LEVEL UP is Latin text already (clubhouse icon); no change needed.',
    2005: 'LEVEL UP Latin (grounds icon); no change needed.',
    2008: 'LEVEL UP Latin (stadium icon); no change needed.',
    2004: 'Blank blue silhouette frame, no text.',
    2007: 'Blank blue silhouette frame, no text.',
    2010: 'Blank blue silhouette frame, no text.',
    2016: 'Latin word BOOKS (bookshop sign in office scene); English already.',
    2045: 'Tiny Latin brand "tatsuo" on PC; not translatable/needed.',
    2046: 'Tiny Latin brand "tatsuo" on monitor; not needed.',
    2054: 'Illegible tiny Latin brand on PC tower; not needed.',
    2053: 'Tiny Latin brand on PC tower; not needed.',
    1998: 'Office interior scene art, no text.', 1999: 'Office interior scene art, no text.',
    2000: 'Office interior scene art, no text.', 2001: 'Office interior scene art, no text.',
}

out = []
for n in (32, 33, 34, 35):
    s = 'sheet_%04d' % n
    for it in smap[s]['items']:
        tid = it['n']
        e = dict(id=it['id'], sheet=n, has_japanese=tid in JP, japanese_text='', english_suggestion='',
                 kind='other', priority=3, region=None,
                 notes=NOTES.get(tid, 'Pure surface/scene texture (stadium or office material), no text.'))
        if tid in JP:
            e.update(JP[tid])
        out.append(e)

os.makedirs(os.path.join(ROOT, 'build/tex/classify'), exist_ok=True)
p = os.path.join(ROOT, 'build/tex/classify/part_32.json')
json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), sum(1 for e in out if e['has_japanese']))
