"""sk6_hdrfix: LOADBAR 07332 and YOUTH.BIN 10469 header unit cells left ink fragments of the old kanji (top strokes at y 31..33, above the
erase rectangle y>=34) and the English sat 3 px below the kanji centre.  Widen the erase rectangle upward (y 28, h 42) and move the text up 2 px.
Idempotent.  sk6_hdrfix.py"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
for i in ('07332', '10469'):
    p = os.path.join(HERE, 'art1_spec', i + '.json')
    s = json.load(open(p, encoding='utf8'))
    for r in s['regions']:
        if r['id'] in ('yr', 'mo', 'wk'):
            er = r['erase_rect']
            r['erase_rect'] = [er[0], 28, er[2], 42]
            r['y'] = 34
    json.dump(s, open(p + '.tmp', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    os.replace(p + '.tmp', p)
    print(i, 'ok')
