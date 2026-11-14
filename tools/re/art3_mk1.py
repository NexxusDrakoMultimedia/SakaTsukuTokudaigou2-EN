import json
spec = {
    'texture': 'ETC_DATA/N_ENTRY.DAT pvr.tbd#0 (03541) Name Entry tabs, confirm, delete, space',
    'size': [512, 512], 'supersample': 4, 'quantize': 'argb4444',
    'defaults': {'erase': {'mode': 'clear'}, 'style': 'menu_label', 'align': 'left', 'valign': 'middle', 'min_sx': 0.6, 'size': 22, 'min_sx': 0.7},
    'regions': [],
}
R = spec['regions']
def add(i, ja, t, x, y, w, h, **kw):
    d = {'id': i, 'ja': ja, 'text': t, 'x': x, 'y': y, 'w': w, 'h': h}
    d.update(kw)
    R.append(d)
add('confirm', '決定', 'Confirm', 3, 389, 64, 33, size=19)
add('symbols', '記号', 'Symbols', 69, 390, 66, 32, size=19)
add('abc', '英数字', 'ABC/123', 6, 430, 79, 32)
add('katakana', 'カタカナ', 'Katakana', 86, 430, 98, 32)
add('hiragana', 'ひらがな', 'Hiragana', 5, 470, 104, 32)
add('kanji', '漢字', 'Kanji', 110, 470, 56, 32)
add('delete', '一文字削除', 'Delete', 196, 382, 104, 25, align='center')
add('space', 'スペース', 'Space', 196, 431, 106, 28, align='center')
json.dump(spec, open('translation/art/03541.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
