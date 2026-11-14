import json
yel = {'bold': 0.6, 'font': ['arial-bold'], 'gradient': [[0, '#ffff70'], [0.55, '#ffee10'], [1, '#e8c800']],
       'outline': {'color': '#201000', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 1.0}}
wht = {'bold': 0.6, 'font': ['arial-bold'], 'gradient': [[0, '#ffffff'], [0.5, '#e8e8ec'], [1, '#9c9ca8']],
       'outline': {'color': '#101018', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 1.0}}
btn = {'font': ['arial-bold'], 'fill': '#f4f4ff', 'outline': {'color': '#10104a', 'width': 0.8}, 'shadow': {'color': '#10104a', 'dx': 1, 'dy': 1, 'alpha': 1.0}}
m_yel = {'mode': 'mask', 'ink': [{'luma_gt': 170}, {'luma_lt': 20}], 'dilate': 2, 'fill': 'diffuse'}
m_wht = {'mode': 'mask', 'ink': [{'luma_gt': 160}, {'luma_lt': 20}], 'dilate': 2, 'fill': 'diffuse'}
m_btn = {'mode': 'mask', 'ink': [{'luma_gt': 185}, {'luma_lt': 40}], 'dilate': 1, 'fill': 'diffuse'}
def R(id, ja, en, rect, style, erase, maxs=26, er=None):
    r = {'id': id, 'ja': ja, 'text': en, 'x': rect[0], 'y': rect[1], 'w': rect[2], 'h': rect[3], 'style': style, 'erase': erase,
         'align': 'center', 'size': 'auto', 'max_size': maxs, 'min_sx': 0.7}
    if er: r['erase_rect'] = er
    return r
def out(tid, regs):
    d = {'texture': tid, 'supersample': 4, 'quantize': 'argb4444', 'regions': regs, 'styles': {'yel': yel, 'wht': wht, 'btn': btn}}
    json.dump(d, open('tools/re/art6/%s.json' % tid, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
out('00167', [
 R('ovs', '海外クラブ', 'Overseas Clubs', [2, 20, 133, 34], 'yel', m_yel, 24, [1, 18, 135, 38]),
 R('jl', 'Jリーグ', 'J.League', [2, 98, 133, 36], 'yel', m_yel, 26, [1, 96, 135, 40]),
 R('nat', '国代表', 'National Teams', [2, 178, 133, 36], 'yel', m_yel, 24, [1, 176, 135, 40]),
 R('auto', '自動選択', 'Auto', [146, 23, 132, 36], 'wht', m_wht, 28, [145, 21, 134, 40]),
 R('man', '手動選択', 'Manual', [146, 110, 132, 38], 'wht', m_wht, 28, [145, 108, 134, 42]),
])
out('00170', [
 R('ovs', '海外クラブ', 'Overseas Clubs', [2, 26, 133, 34], 'yel', m_yel, 24, [1, 24, 135, 38]),
 R('nat', '国代表', 'National Teams', [146, 26, 133, 34], 'yel', m_yel, 24, [145, 24, 135, 38]),
 R('auto', '自動選択', 'Auto', [290, 24, 132, 36], 'wht', m_wht, 28, [289, 22, 134, 40]),
 R('jl', 'Jリーグ', 'J.League', [2, 110, 133, 34], 'yel', m_yel, 26, [1, 108, 135, 38]),
 R('man', '手動選択', 'Manual', [290, 110, 132, 36], 'wht', m_wht, 28, [289, 108, 134, 40]),
 R('start', '試合開始', 'Start Match', [150, 102, 84, 30], 'btn', m_btn, 15, [150, 100, 84, 34]),
 R('redraw', '再ドロー', 'Redraw', [150, 142, 84, 30], 'btn', m_btn, 15, [150, 140, 84, 34]),
])
