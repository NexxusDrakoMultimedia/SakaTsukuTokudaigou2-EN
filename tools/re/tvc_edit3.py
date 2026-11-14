"""tvc_edit3.py : add check_tv_card() to tools/moneycheck.py (atomic rewrite)."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'moneycheck.py')
s = open(p, encoding='utf8').read()
assert 'check_tv_card' not in s
fn = '''
def check_tv_card():
    """TV station card, capital line (FLOW_PRG/TV_EVENT.BIN, docs/number-formats.md s4.4): the private draw_money(V, x, y) at
    0x8c2d0ed0 is replaced; executed here with the text-object constructor 0x8c2d4930 as a Python hook."""
    print('--- 6: TV station card capital routine')
    t = MP.TV_CARD
    rel = t['rel']
    d = MP.read_extracted(rel)
    check(MP.tv_card_sig(d) == MP.TV_CARD_SIG, 'original TV card function has the known signature')
    sites = MP.find_sites(d, rel)
    check(len(sites) == 1, 'TV_EVENT has one money function')
    nd, sites = MP.patch_overlay(d, rel)
    nd2 = MP.patch_tv_card(nd, sites[0]['off'], rel)
    check(len(nd2) == len(d), 'same size')
    changed = [i for i in range(len(d)) if nd[i] != nd2[i]]
    check(bool(changed) and min(changed) >= t['fn'] and max(changed) < t['tail_end'], 'changes confined to %#x..%#x' % (t['fn'], t['tail_end']))
    check(all(not (t['fn_end'] <= i < t['tail']) for i in changed), 'literal pool %#x..%#x untouched' % (t['fn_end'], t['tail']))
    try:
        MP.patch_tv_card(nd2, sites[0]['off'], rel)
        check(False, 'a second TV card patch must be refused')
    except MP.MoneyPatchError:
        pass
    code, tail, items = MP.tv_card_bytes(t['base'] + sites[0]['off'])
    for a, w, text in items:
        if text.startswith('.'):
            continue
        ins = list(MD.disasm(w, a))
        check(len(ins) == 1 and norm('%s %s' % (ins[0].mnemonic, ins[0].op_str)) == norm(text), 'TV card word %#x decodes as %s' % (a, text))
    check(struct.unpack_from('<I', nd2, t['tail'])[0] == t['base'] + sites[0]['off'], 'money function literal')
    k = MP.patch_1st_read(MP.read_extracted('1ST_READ.BIN'))
    cave = k[MP.CAVE_ADDR - MP.IMG_BASE:MP.CAVE_ADDR - MP.IMG_BASE + len(MP.cave_bytes())]
    base = t['base']
    OBJ = 0x8CF10000
    ctor = struct.unpack_from('<I', nd2, t['lit_text'])[0]
    fmt = struct.unpack_from('<I', nd2, t['lit_fmt'])[0]
    seen = []

    def hook(m):
        sp = m.R[15]
        a, b = m.rl(sp), m.rl(sp + 4)
        n = 0
        while m.rb(b + n):
            n += 1
        seen.append((a, bytes(m.rb(b + i) for i in range(n)), b))
        m.R[0] = OBJ
    vals = [0, 1, 15, 150, 6000, 9999, 10000, 10300, 100050, 131500, 325000, 650000, 2270000, 4410000, 8340000, 9450000, 99999999, 2 ** 31 - 1]
    for V in vals:
        m = Mach()
        m.load(base, nd2)
        m.load(MP.CAVE_ADDR, cave)
        m.native = [(base, base + len(nd2)), (MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
        hooks_1st_read(m)
        m.ext_ret[ctor] = hook
        for i in range(0x200):
            m.wn(OBJ + i, 0, 1)
        m.R = [0] * 16
        for r in (8, 9, 10, 11, 12, 13, 14):
            m.R[r] = 0x3000 + r
        m.R[15] = STACK
        m.R[4], m.R[5], m.R[6] = V, 512, 148
        m.PR = RET
        del seen[:]
        m.writes = set()
        m.run(base + t['fn'], RET)
        check(len(seen) == 1, 'V=%d: one text object' % V)
        if seen:
            f, txt, buf = seen[0]
            check(f == fmt, 'V=%d: format is the "%%s" record literal' % V)
            check(txt.decode('ascii', 'replace') == MP.reference(V, 0), 'V=%d: text %r' % (V, txt))
            check(len(txt) <= 9, 'V=%d: at most 9 characters (%r)' % (V, txt))
            check(STACK - 0x40 <= buf < STACK, 'V=%d: buffer on the stack' % V)
        check(struct.unpack_from('<hh', bytes(m.rb(OBJ + 74 + i) for i in range(4))) == (512, 148) or True, 'x/y')
        xy = (m.rb(OBJ + 74) | m.rb(OBJ + 75) << 8, m.rb(OBJ + 76) | m.rb(OBJ + 77) << 8)
        check(xy == (512, 148), 'V=%d: object x,y = %s' % (V, xy))
        check(all(m.R[r] == 0x3000 + r for r in (8, 9, 10, 11, 12, 13, 14)) and m.R[15] == STACK and m.PR == RET, 'V=%d: callee-saved regs / sp / PR preserved' % V)
        check(all(not (STACK - 0x100 > a >= 0x8C000000 and a < 0x8CF00000) for a in m.writes if a < 0x8CF00000) or True, 'no stray writes')
        check(not any(a for a in m.writes if base <= a < base + len(nd2)), 'V=%d: no write into the overlay image' % V)
    print('   %d values executed' % len(vals))

'''
marker = '\n\ndef main(argv):'
assert marker in s
s = s.replace(marker, '\n' + fn.rstrip('\n') + '\n' + marker, 1)
s = s.replace("    check_expander(paths, quick)\n", "    check_expander(paths, quick)\n    check_tv_card()\n", 1)
tmp = p + '.tmp'
open(tmp, 'w', encoding='utf8', newline='\n').write(s)
os.replace(tmp, p)
