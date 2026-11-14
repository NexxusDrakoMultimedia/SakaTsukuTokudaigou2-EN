"""ar6_banedit: ar6_banner.py edits (idempotent): fixed-size search with squash, standard caps per colour class."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ar6_banner.py')
s = open(p, encoding='utf8').read()
# 1. render_text takes a size
s = s.replace("def render_text(img, text, fmt, boxx0):", "def render_text(img, text, fmt, boxx0, size='auto'):")
s = s.replace("size='auto', max_size=21, min_sx=0.68, pad=0", "size=size, max_size=21, min_sx=0.68, pad=0")
# 2. pass 1 searches sizes
old = "    _, r1, w1 = render_text(blank, text, fmt, INK_R - MAXW)\n"
new = ("    for sz in [21 - 0.5 * k for k in range(0, 20)]:\n"
       "        _, r1, w1 = render_text(blank, text, fmt, INK_R - MAXW, sz)\n"
       "        if r1['block'][0] <= MAXW + 0.5 and (r1.get('squash') or 1.0) >= 0.68:\n"
       "            break\n")
if old in s:
    s = s.replace(old, new)
s = s.replace("out, r2, w2 = render_text(img, text, fmt, INK_R - MAXW)", "out, r2, w2 = render_text(img, text, fmt, INK_R - MAXW, sz)")
open(p, 'w', encoding='utf8').write(s)
print('ok')
