import re
p = 'tools/test_pipeline.py'
s = open(p, encoding='utf-8').read()
old = "        if not diff <= want or not diff:\n            check(False, 'G: %s differs outside the hook bytes / %%D literal' % iso)\n"
new = ("        if iso == '/' + MPT.TV_CARD['rel']:          # TV station card capital routine (moneypatch.patch_tv_card)\n"
       "            t = MPT.TV_CARD\n"
       "            want |= set(range(t['fn'], t['fn_end'])) | set(range(t['tail'], t['tail_end']))\n"
       "            code, tail, _ = MPT.tv_card_bytes(t['base'] + sites[0]['off'])\n"
       "            check(new[t['fn']:t['fn_end']] == code and new[t['tail']:t['tail_end']] == tail, 'G: TV_EVENT card routine bytes')\n"
       + old)
assert s.count(old) == 1
open(p + '.tmp', 'w', encoding='utf-8', newline='').write(s.replace(old, new))
import os
os.replace(p + '.tmp', p)
