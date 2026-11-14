p = 'tools/re/art6_gen_match.py'
s = open(p, encoding='utf8').read()
s = s.replace("regs.append(R('menu%d' % k, ja, en, [12, 41 + 32 * k, 112, 28], 'lbl', m_lbl, maxs=19))",
              "regs.append(R('menu%d' % k, ja, en, [12, 41 + 32 * k, 112, 28], 'lbl', {'mode': 'vgrad'}, maxs=19, erase_rect=[10, 42 + 32 * k, 116, 26]))")
s = s.replace("[72, 397, 80, 26], 'ext', {'mode': 'mask', 'ink': [{'luma_gt': 150}, {'luma_lt': 15}], 'dilate': 2, 'fill': 'diffuse'}, maxs=22))",
              "[74, 397, 76, 26], 'ext', {'mode': 'hgrad'}, maxs=22, erase_rect=[77, 396, 71, 34]))")
s = s.replace("erase_rect=[198, 437 + 40 * i, 148, 30]", "erase_rect=[198, 434 + 40 * i, 148, 34]")
s = s.replace("erase_rect=[360, 397 + 40 * i, 148, 30]", "erase_rect=[360, 394 + 40 * i, 148, 34]")
open(p, 'w', encoding='utf8').write(s)
