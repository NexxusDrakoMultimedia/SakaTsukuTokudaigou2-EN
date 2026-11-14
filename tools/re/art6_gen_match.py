import json, sys
lbl = {'font': ['arial-bold', 'segoe-ui-bold'], 'gradient': [[0, '#ffffff'], [0.5, '#e4e8e4'], [1, '#98a49c']],
       'outline': {'color': '#000000', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
yel = {'font': ['arial-black', 'arial-bold'], 'gradient': [[0, '#ffff70'], [0.55, '#ffee10'], [1, '#e8c800']],
       'outline': {'color': '#201000', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 1.0}}
blk = {'font': ['arial-bold'], 'fill': '#f2f2f2', 'outline': {'color': '#303030', 'width': 0.5}}
ext = {'font': ['arial-black', 'arial-bold'], 'gradient': [[0, '#fff060'], [0.5, '#ffb020'], [1, '#ff6000']],
       'outline': {'color': '#300000', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
m_lbl = {'mode': 'mask', 'ink': [{'sat_lt': 0.3, 'luma_gt': 70}, {'luma_lt': 26}], 'dilate': 1, 'fill': 'diffuse'}
m_yel = {'mode': 'mask', 'ink': [{'luma_gt': 170}, {'luma_lt': 20}], 'dilate': 2, 'fill': 'diffuse'}
m_blk = {'mode': 'mask', 'ink': [{'luma_gt': 60}], 'dilate': 1, 'fill': 'diffuse'}
clr = {'mode': 'clear'}
def R(id, ja, en, rect, style, erase, align='center', erase_rect=None, size='auto', maxs=21):
    r = {'id': id, 'ja': ja, 'text': en, 'x': rect[0], 'y': rect[1], 'w': rect[2], 'h': rect[3], 'style': style, 'erase': erase, 'align': align,
         'size': size, 'max_size': maxs, 'min_sx': 0.7}
    if erase_rect: r['erase_rect'] = erase_rect
    return r
def common():
    regs = []
    for k, (ja, en) in enumerate([('簡易選択', 'Quick Pick'), ('大会形式', 'Format'), ('試合形式', 'Match Type'), ('参加チーム', 'Teams'),
                                  ('スタジアム', 'Stadium'), ('選手規定', 'Player Rules')]):
        regs.append(R('menu%d' % k, ja, en, [12, 41 + 32 * k, 112, 28], 'lbl', clr, maxs=19, erase_rect=[10, 40 + 32 * k, 117, 30]))
    regs.append(R('blk1', '試合開始', 'Start Match', [434, 281, 76, 24], 'blk', m_blk, 'left', maxs=15))
    regs.append(R('blk2', '再ドロー', 'Redraw', [434, 321, 76, 24], 'blk', m_blk, 'left', maxs=15))
    regs.append(R('exit', '終了', 'Exit', [74, 397, 76, 26], 'ext', {'mode': 'hgrad'}, maxs=22, erase_rect=[77, 396, 71, 34]))
    for i, ab in enumerate('AB'):
        regs.append(R('nat' + ab, '代表' + ab, 'National ' + ab, [198, 438 + 40 * i, 148, 28], 'yel', m_yel, maxs=22, erase_rect=[198, 434 + 40 * i, 148, 34]))
    for i, ab in enumerate('ABC'):
        regs.append(R('ovs' + ab, '海外' + ab, 'Overseas ' + ab, [360, 398 + 40 * i, 148, 28], 'yel', m_yel, maxs=22, erase_rect=[360, 394 + 40 * i, 148, 34]))
    return regs
def out(tid, regs):
    d = {'texture': tid, 'supersample': 4, 'quantize': 'argb4444', 'regions': regs, 'styles': {'lbl': lbl, 'yel': yel, 'blk': blk, 'ext': ext}}
    json.dump(d, open('tools/re/art6/%s.json' % tid, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
r = common()
r.append(R('confirm', '決定', 'Confirm', [138, 239, 116, 27], 'yel', clr, maxs=22))
r.append(R('start', '試合開始', 'Start Match', [282, 239, 116, 27], 'yel', clr, maxs=22))
out('00165', r)
r = common()
r.append(R('start', '試合開始', 'Start Match', [187, 239, 291, 27], 'yel', clr, maxs=22))
out('00169', r)
