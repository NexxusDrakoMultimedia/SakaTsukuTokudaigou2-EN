import json
wh = {'font': ['arial-bold-italic'], 'gradient': [[0, '#ffffff'], [0.55, '#e4e4f0'], [1, '#9c9cb8']],
      'outline': {'color': '#10102c', 'width': 0.8}, 'shadow': {'color': '#0c0c28', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
ink = {'mode': 'mask', 'ink': [{'luma_gt': 165}, {'luma_lt': 30}], 'dilate': 1, 'fill': 'diffuse'}
def R(id, ja, en, x, y, w=86, h=24, maxs=18):
    return {'id': id, 'ja': ja, 'text': en, 'x': x, 'y': y, 'w': w, 'h': h, 'style': 'wh', 'erase': ink, 'align': 'center', 'size': 'auto',
            'max_size': maxs, 'min_sx': 0.65}
regs = [R('c1', '応援歌1', 'Cheer Song 1', 4, 4), R('c2', '応援歌2', 'Cheer Song 2', 4, 36), R('c3', '応援歌3', 'Cheer Song 3', 4, 68),
        R('pinch', 'ピンチ', 'Pinch', 100, 4), R('rand', 'ランダム', 'Random', 100, 36), R('norm', 'ノーマル', 'Normal', 100, 68),
        R('good', '好調', 'Good', 100, 100)]
d = {'texture': '36805', 'supersample': 4, 'quantize': 'rgb565', 'regions': regs, 'styles': {'wh': wh}}
json.dump(d, open('tools/re/art6/36805.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
