import json
st = json.load(open('translation/art/03584.json', encoding='utf8'))['styles']
spec = {
    'texture': 'ETC_DATA/PL_EDIT.ZAR PL_PT4.TBD#0 (03585) Player Edit labels (skin tones, face part names)',
    'size': [512, 512], 'supersample': 4, 'quantize': 'argb4444',
    'styles': {
        'pl_white': st['pl_white'],
        'pl_blue': {'font': ['arial-narrow-bold', 'arial-bold'], 'gradient': [[0, '#e4f0ff'], [1, '#a8c4e8']],
                    'outline': {'color': '#000000', 'width': 1.0},
                    'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'steps': 2, 'alpha': 1.0}},
    },
    'defaults': {'erase': {'mode': 'clear'}, 'align': 'left', 'valign': 'middle', 'min_sx': 0.6, 'style': 'pl_white', 'size': 19},
    'regions': [],
}
R = spec['regions']
for k in range(8):
    R.append({'id': 'skin%d' % (k + 1), 'ja': '肌の色%d' % (k + 1), 'text': 'Skin Tone %d' % (k + 1), 'size': 21,
              'x': 81, 'y': 9 + 32 * k, 'w': 98, 'h': 25, 'dx': 1,
              'erase': {'mode': 'mask', 'ink': {'luma_gt': 100}, 'dilate': 3, 'fill': 'hfill',
                        'exclude': [[0, 256, 200, 8], [0, 0, 200, 4]]}})
def add(i, ja, t, x, y, w, h, style=None):
    d = {'id': i, 'ja': ja, 'text': t, 'x': x, 'y': y, 'w': w, 'h': h}
    if style:
        d['style'] = style
    R.append(d)
add('skin_tone', '肌の色', 'Skin Tone', 140, 271, 72, 27)
add('hair', '髪型', 'Hair', 140, 302, 52, 28)
add('eyes', '目', 'Eyes', 141, 335, 36, 27)
add('mouth', '口', 'Mouth', 141, 367, 40, 27)
add('glasses', 'メガネ', 'Glasses', 140, 398, 72, 28)
add('exit', '終了', 'Exit', 139, 431, 50, 28)
add('face_shape', '輪郭', 'Face Shape', 220, 286, 72, 28)
add('brows', '眉毛', 'Brows', 220, 319, 60, 27)
add('nose', '鼻', 'Nose', 220, 350, 44, 28)
add('facial_hair', 'ヒゲ', 'Facial Hair', 220, 382, 72, 27)
add('other', 'その他', 'Other', 220, 416, 72, 28)
add('part_no', 'パーツ番号', 'Part No.', 294, 270, 110, 28, 'pl_blue')
add('position', '位置', 'Position', 294, 303, 66, 27, 'pl_blue')
add('size', '大きさ', 'Size', 294, 334, 66, 28, 'pl_blue')
add('height', '高さ', 'Height', 294, 366, 66, 28, 'pl_blue')
add('width', '幅', 'Width', 294, 398, 52, 28, 'pl_blue')
add('frame', '骨格', 'Frame', 294, 430, 62, 28, 'pl_blue')
add('shape', '形状', 'Shape', 294, 461, 62, 28, 'pl_blue')
json.dump(spec, open('translation/art/03585.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
