"""Write build/tex/classify/part_16.json for contact sheets 16-19 (visual classification by eye)."""
import json, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = json.load(open(os.path.join(root, 'build/tex/sheets/sheet_map.json'), encoding='utf-8'))
out = []
for s in (16, 17, 18, 19):
    for it in m['sheets']['sheet_%04d' % s]['items']:
        out.append({
            'id': it['id'], 'sheet': s, 'has_japanese': False,
            'japanese_text': '', 'english_suggestion': '', 'kind': 'other',
            'priority': 3, 'region': None,
            'notes': 'Staff/coach portrait photo-style face in gold/cyan frame; no kana/kanji. Viewed at sheet scale (PROVEN no text visible; faces only).'})
os.makedirs(os.path.join(root, 'build/tex/classify'), exist_ok=True)
json.dump(out, open(os.path.join(root, 'build/tex/classify/part_16.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out))
