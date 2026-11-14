"""mn6_edit_tv.py: one-off, idempotent edit of the TV card routine text in tools/moneypatch.py (compact form, x = 456)."""
import os
import sys

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'moneypatch.py')
s = open(P, encoding='utf-8').read()
a = s.index('# jp style: the text is "[oku] oku [man] man", up to 15 characters')
b = s.index('TV_CARD_SRC = TV_CARD_SRC_JP')
new = '''# jp style (mn6): the capital is ONE text object in the compact form ("32 oku 5000m", flag 77) that starts at x = 456 of 640.  The plate of the card
# ends near x = 616 and its "Capital" capsule near 448, i.e. 168 px are available; the full form "32 oku 5000 man" is 183 px (too wide, it ran over the
# capsule at x = 440 and past the plate), the compact form is 147 px (456 .. 603); "945 oku" is 87 px.  The Japanese card drew the "億" piece at x - 72 and
# the "万円" piece at x (x = 512); the stack buffer is 32 bytes (an int32 needs up to 20 + NUL).
TV_CARD_X_JP = 456
TV_CARD_SRC_JP = (TV_CARD_SRC_WESTERN.replace('add   #-16,r15', 'add   #-32,r15').replace('add   #16,r15', 'add   #32,r15')
                  .replace('mov   r5,r13                  ; x', 'mov   r5,r13                  ; x\n        add   #%d,r13               ; x = %d' % (TV_CARD_X_JP - 512, TV_CARD_X_JP))
                  .replace('mov   #0,r6                   ; flag 0 = abbreviated money text', 'mov   #77,r6                  ; flag 77 = compact form'))
'''
if 'TV_CARD_X_JP' in s:
    sys.exit('already applied')
s = s[:a] + new + s[b:]
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
