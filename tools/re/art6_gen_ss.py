import json
wh = {'font': ['arial-bold-italic'], 'shear': 0.0, 'gradient': [[0, '#ffffff'], [0.55, '#e8e8f4'], [1, '#a8a8c8']],
      'outline': {'color': '#0c0820', 'width': 0.9}, 'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
bl = {'font': ['arial-black'], 'shear': 0.22, 'gradient': [[0, '#4a52ff'], [1, '#1c1cc8']],
      'outline': {'color': '#10106a', 'width': 0.8}, 'shadow': {'color': '#5a2a00', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 0.9}}
lav = {'font': ['arial-bold-italic'], 'gradient': [[0, '#f4f4ff'], [1, '#aeb0e8']], 'outline': {'color': '#1a1a70', 'width': 0.9},
       'shadow': {'color': '#101050', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
cream = {'font': ['arial-bold-italic'], 'gradient': [[0, '#fff8ec'], [1, '#c8b8a8']], 'outline': {'color': '#5a1408', 'width': 0.8},
         'shadow': {'color': '#4a0c04', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
plain = {'font': ['arial-bold'], 'fill': '#f4f0ff', 'shadow': {'color': '#301050', 'dx': 1, 'dy': 1, 'alpha': 0.8}}
ink_w = {'mode': 'mask', 'ink': [{'luma_gt': 175}, {'luma_lt': 28}], 'dilate': 1, 'fill': 'diffuse'}
ink_b = {'mode': 'mask', 'ink': [{'bg_dist_gt': 75, 'bg': [215, 140, 40]}], 'dilate': 1, 'fill': 'diffuse'}
ink_l = {'mode': 'mask', 'ink': [{'luma_gt': 135}, {'luma_lt': 35}], 'dilate': 2, 'fill': 'diffuse'}
ink_c = {'mode': 'mask', 'ink': [{'luma_gt': 165}, {'luma_lt': 60}], 'dilate': 1, 'fill': 'diffuse'}
def R(id, ja, en, rect, style, erase, maxs=20, align='center'):
    return {'id': id, 'ja': ja, 'text': en, 'x': rect[0], 'y': rect[1], 'w': rect[2], 'h': rect[3], 'style': style, 'erase': erase,
            'align': align, 'size': 'auto', 'max_size': maxs, 'min_sx': 0.7}
regs = [
 R('title', 'タイトル付け', 'Set Title', [10, 26, 78, 24], 'wh', ink_w, 14),
 R('compose', '作曲', 'Compose', [8, 63, 82, 26], 'wh', ink_w, 18),
 R('time', '拍子', 'Time', [8, 101, 82, 26], 'wh', ink_w, 20),
 R('tempo', 'テンポ', 'Tempo', [8, 143, 82, 26], 'wh', ink_w, 20),
 R('load', 'ロード', 'Load', [8, 183, 82, 26], 'wh', ink_w, 20),
 R('save', 'セーブ', 'Save', [8, 222, 82, 26], 'wh', ink_w, 20),
 R('exit', '終了', 'Exit', [8, 260, 82, 26], 'wh', ink_w, 20),
 R('head', '応援歌エディット', 'Cheer Song Edit', [100, 25, 168, 37], 'bl', ink_b, 30),
 R('timelab', '拍子', 'Time', [204, 120, 42, 24], 'wh', ink_w, 14),
 R('tempolab', 'テンポ', 'Tempo', [250, 122, 40, 22], 'wh', ink_w, 14),
 R('slow', '遅', 'Slow', [332, 108, 38, 28], 'wh', ink_w, 16),
 R('fast', '速', 'Fast', [458, 108, 38, 28], 'wh', ink_w, 16),
 R('sample', 'サンプルデータ', 'Sample Data', [116, 152, 178, 26], 'lav', ink_l, 20, 'left'),
 R('savefile', 'セーブファイル', 'Save File', [116, 188, 178, 24], 'lav', ink_l, 20, 'left'),
 R('melody', 'メロディ', 'Melody', [304, 144, 80, 24], 'wh', ink_w, 17, 'left'),
 R('rhythm', 'リズム', 'Rhythm', [312, 170, 66, 20], 'wh', ink_w, 16, 'left'),
 R('triplet', '三連符', 'Triplet', [450, 146, 58, 20], 'plain', {'mode': 'mask', 'ink': [{'luma_gt': 190}], 'dilate': 1, 'fill': 'diffuse'}, 14),
 R('b3', '三拍子', '3 Beats', [338, 321, 70, 26], 'cream', ink_c, 18),
 R('b4', '四拍子', '4 Beats', [338, 353, 70, 26], 'cream', ink_c, 18),
]
d = {'texture': '36802', 'supersample': 4, 'quantize': 'argb1555', 'regions': regs, 'styles': {'wh': wh, 'bl': bl, 'lav': lav, 'cream': cream, 'plain': plain}}
json.dump(d, open('tools/re/art6/36802.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
