"""tvc_edit1.py : one-shot edit of tools/moneypatch.py (adds the TV_EVENT station-card capital hook).  Atomic rewrite."""
import os, sys
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'moneypatch.py')
s = open(p, encoding='utf8').read()
assert 'TV_CARD' not in s

block = '''

# ------------------------------------------------------------------------------------------------ TV station card (TV_EVENT)
# PROVEN by reading FLOW_PRG/TV_EVENT.BIN (load 0x8c2d0000): the "capital" line of the TV station card is NOT drawn through the
# tsString `%m` expander but by a private function at 0x8c2d0ed0  draw_money(V, x, y)  (single caller 0x8c2d109a, V = table
# 0x8c2d9a54[level] in 10,000-yen units: 325000 650000 2270000 4410000 8340000 9450000).  It splits V = hi * 10000 + lo and
# draws two separate text objects, "%s億" (hi) at x-72 and "%s万円" (lo, 4 zero padded digits) at x, so the English pieces
# "%s00M" + "Y%s0000" printed 3200M50000000.  Pieces cannot be reordered or divided, so the function is replaced by a
# 64-byte routine that formats V with the (hooked) money function of the same overlay (-> cave -> "Y3.25bn") and draws ONE text
# object (format = the "%s人" record, English "%s") at (x, y).  The old big-value path (0xf2c..0xf9b) becomes dead; its first word
# holds the literal of the money function.  The literal pool 0xf14..0xf2b is shared with two other functions and is not touched.
TV_CARD = dict(rel='FLOW_PRG/TV_EVENT.BIN', base=0x8C2D0000, fn=0x0ED0, fn_end=0x0F14, tail=0x0F2C, tail_end=0x0F9C,
               lit_text=0x0F1C, lit_fmt=0x0F24)
TV_CARD_SIG = '3a55a1b0d9'            # sha1[:10] of the original bytes 0xed0..0xf13 + 0xf2c..0xf9b (no pool, no pc-relative targets)
TV_CARD_SRC = """
        mov.l r14,@-r15
        mov.l r13,@-r15
        sts.l pr,@-r15
        add   #-16,r15
        mov   r5,r13                  ; x
        mov   r4,r5                   ; V (10,000 yen)
        mov   r15,r4                  ; dst = 16-byte buffer on the stack
        mov   r6,r14                  ; y
        mov.l @(L_money,pc),r3
        jsr   @r3
        mov   #0,r6                   ; flag 0 = abbreviated money text
        mov   r15,r1
        add   r0,r1
        mov   #0,r2
        mov.b r2,@r1                  ; NUL
        mov.l @(L_fmt,pc),r3          ; the "%s" record
        mov.l @(L_text,pc),r2         ; text-object constructor (fmt, args...)
        mov   r15,r1
        mov.l r1,@-r15
        jsr   @r2
        mov.l r3,@-r15
        add   #8,r15
        mov   r0,r4
        mov   #74,r0
        mov.w r13,@(r0,r4)
        mov   #76,r0
        mov.w r14,@(r0,r4)
        add   #16,r15
        lds.l @r15+,pr
        mov.l @r15+,r13
        rts
        mov.l @r15+,r14
"""


def tv_card_sig(d):
    t = TV_CARD
    return hashlib.sha1(d[t['fn']:t['fn_end']] + d[t['tail']:t['tail_end']]).hexdigest()[:10]


def tv_card_bytes(money_addr):
    """(code at fn, filler for tail) for a money function at load address `money_addr`."""
    t = TV_CARD
    sym = dict(L_money=t['base'] + t['tail'], L_fmt=t['base'] + t['lit_fmt'], L_text=t['base'] + t['lit_text'])
    code, items, _ = assemble(TV_CARD_SRC, t['base'] + t['fn'], sym)
    if len(code) > t['fn_end'] - t['fn']:
        raise MoneyPatchError('TV card routine too long (%d bytes)' % len(code))
    code += b'\x09\x00' * ((t['fn_end'] - t['fn'] - len(code)) // 2)
    tail = struct.pack('<I', money_addr) + b'\x09\x00' * ((t['tail_end'] - t['tail'] - 4) // 2)
    return code, tail, items


def patch_tv_card(d, money_off, name='FLOW_PRG/TV_EVENT.BIN'):
    """d = TV_EVENT.BIN bytes (money function already hooked or not); money_off = file offset of its money function."""
    t = TV_CARD
    if tv_card_sig(d) != TV_CARD_SIG:
        raise MoneyPatchError('%s: TV card capital function at %#x does not match the known bytes (%s)' % (name, t['fn'], tv_card_sig(d)))
    if struct.unpack_from('<II', d, t['lit_text'])[0] != 0x8C2D4930 or struct.unpack_from('<I', d, t['lit_fmt'] - 4)[0] != struct.unpack_from('<I', d, t['lit_text'] - 0)[0] and False:
        pass
    code, tail, _ = tv_card_bytes(t['base'] + money_off)
    b = bytearray(d)
    b[t['fn']:t['fn_end']] = code
    b[t['tail']:t['tail_end']] = tail
    assert len(b) == len(d)
    return bytes(b)

'''
marker = '\n\ndef overlay_paths(root=EXTRACTED):'
assert marker in s
s = s.replace(marker, block + marker, 1)

old = '''        nd, sites = patch_overlay(d, rel, addr, variants, decimal_d)
        if sites:'''
new = '''        nd, sites = patch_overlay(d, rel, addr, variants, decimal_d)
        if sites and rel == TV_CARD['rel'] and tv_card:
            nd = patch_tv_card(nd, sites[0]['off'], rel)
            rep.setdefault('tv_card', rel)
        if sites:'''
assert old in s
s = s.replace(old, new, 1)
s = s.replace("def make_patches(read, current=None, addr=CAVE_ADDR, paths=None, expect=None, variants='A', decimal_d=True):",
              "def make_patches(read, current=None, addr=CAVE_ADDR, paths=None, expect=None, variants='A', decimal_d=True, tv_card=True):", 1)
tmp = p + '.tmp'
open(tmp, 'w', encoding='utf8', newline='\n').write(s)
os.replace(tmp, p)
print('ok')
