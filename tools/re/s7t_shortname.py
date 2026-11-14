"""s7t: proposal + executable check for the shared SH-4 "short name" routine (practice name tags and ten other overlays).

Original routine (TRAINING.BIN file 0x15318, va 0x8c2e5318; the same 152-byte routine sits at the offsets listed in SITES):
    void shortname(char *dest /*r4*/, const char *src /*r5*/)
        copies at most 4 BYTES of src, stopping at the first blank or NUL, into an 8-byte local buffer,
        then sprintf(dest, n == 1 || n == 2 ? FMT1 /* " %s " */ : FMT2 /* "%s" */, buf)   (variadic args on the stack)
In the English build the BPINFO name is "Given Family", so the label shows the first 4 letters of the GIVEN name (`Taiy`) or an
initial (`H.`).

Replacement (this file): show the LAST blank-separated word (the family name) up to LIMIT bytes (<= 7, the buffer holds 8).
Same entry, same stack protocol, same literal pool slots, no callee-saved register touched.

    python -I -X utf8 tools/re/s7t_shortname.py             # assemble for TRAINING, check against the reference in the simulator
    python -I -X utf8 tools/re/s7t_shortname.py --hex       # print the patch bytes of every site
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sh4asm2   # noqa: E402
import sh4sim    # noqa: E402

LIMIT = 7

SRC = """
        .word 0x4f22             ; sts.l pr,@-r15
        add #-8,r15              ; buf = r15 .. r15+7
        mov r5,r6                ; q = start of the last word
        mov r5,r1                ; p
scan:   mov.b @r1+,r0
        tst r0,r0
        bt copy
        cmp/eq #32,r0
        bf scan
        mov.b @r1,r2             ; blank: the next byte starts a word unless it is the NUL (trailing blank)
        tst r2,r2
        bt scan
        bra scan
        mov r1,r6
copy:   mov r15,r3               ; d = buf
        mov r15,r7
        add #LIMIT,r7            ; end = buf + LIMIT
cl:     mov.b @r6+,r0
        tst r0,r0
        bt done
        cmp/eq #32,r0
        bt done
        .word 0x2300             ; mov.b r0,@r3
        add #1,r3
        cmp/hs r7,r3
        bf cl
done:   mov #0,r0
        .word 0x2300             ; mov.b r0,@r3
        sub r15,r3               ; n
        mov r3,r0
        cmp/eq #1,r0
        bt fmt1
        cmp/eq #2,r0
        bt fmt1
        mov.l @(FMT2P,pc),r2
        bra call
        nop
fmt1:   mov.l @(FMT1P,pc),r2
call:   mov r15,r3
        mov.l r3,@-r15           ; stack args: [sp] = fmt, [sp+4] = buf (as the original)
        mov.l r2,@-r15
        mov.l @(SPFP,pc),r1
        jsr @r1
        nop
        add #8,r15               ; the two pushed words
        add #8,r15               ; buf
        .word 0x4f26             ; lds.l @r15+,pr
        rts
        nop
        .align 4
FMT1P:  .long FMT1
SPFP:   .long SPRINTF
FMT2P:  .long FMT2
"""

# (file, offset of the routine) - identical 152-byte routine (checked by the signature in tools/re/s7t_sigscan.py)
SITES = [('CAP_SLCT', 0x118dc), ('ENDOPT', 0x2e57c), ('EVENT', 0x4ba38), ('GAME', 0x6f44c), ('G_RESULT', 0xc440),
         ('NEWCON', 0x20a10), ('NEWS', 0x21d70), ('OFFICE', 0x283d8), ('TOWN', 0x26d54), ('TRAINING', 0x1533c),
         ('YOUTH', 0x14038)]     # offsets of the `mov #4,r3` word (routine starts 0x24 bytes earlier)
ENTRY = -0x24
ROUTINE_LEN = 0x98               # 152 bytes: code 0x..18-0x..a3 plus the 3 pool words


def build(base, fmt1, sprintf, fmt2):
    src = SRC.replace('LIMIT', str(LIMIT))
    code, listing, sym = sh4asm2.assemble(src, base, {'FMT1': fmt1, 'SPRINTF': sprintf, 'FMT2': fmt2})
    return code


def reference(src, limit=LIMIT):
    """python model of the replacement (src: bytes, no NUL)"""
    toks = src.split(b' ')
    # last word start after the last blank that is followed by a non-NUL byte
    q = 0
    for i, ch in enumerate(src):
        if ch == 0x20 and i + 1 < len(src):
            q = i + 1
    w = src[q:]
    w = w.split(b' ')[0][:limit]
    n = len(w)
    return (b' ' + w + b' ') if n in (1, 2) else w


def run_sim(code, base, src, fmt1, fmt2, sprintf):
    m = sh4sim.Machine()
    m.load(base, code)
    m.load(0x8c000000, src + b'\0')
    m.load(fmt1, b' %s \0')
    m.load(fmt2, b'%s\0')
    sp = 0x8c800000
    m.R[15] = sp
    m.R[4] = 0x8c900000
    m.R[5] = 0x8c000000
    for k in (8, 9, 10, 11, 12, 13, 14):
        m.R[k] = 0x1000 + k
    STOP = 0x8cff0000
    m.PR = STOP
    out = {}

    def spf(mm):
        fmt = mm.rn(mm.R[15], 4)
        arg = mm.rn(mm.R[15] + 4, 4)
        s = bytes(mm.rb(arg + i) for i in range(64)).split(b'\0')[0]
        f = bytes(mm.rb(fmt + i) for i in range(8)).split(b'\0')[0]
        out['text'] = f.replace(b'%s', s)
        out['dest'] = mm.R[4]
    m.ext_ret[sprintf] = spf
    m.run(base, STOP)
    for k in (8, 9, 10, 11, 12, 13, 14):
        assert m.R[k] == 0x1000 + k, 'callee-saved r%d clobbered' % k
    assert m.R[15] == sp, 'stack not restored'
    return out


def main():
    base, fmt1, sprintf, fmt2 = 0x8c2e5318, 0x8c34c4c4, 0x8c014d80, 0x8c34c4cc
    code = build(base, fmt1, sprintf, fmt2)
    if '--hex' in sys.argv:
        for f, o in SITES:
            print(f, hex(o + ENTRY), 'len', len(code))
        return
    assert len(code) <= ROUTINE_LEN, (len(code), ROUTINE_LEN)
    names = [b'Taiyo Yamada', b'H. Nakata', b'Kenji Nakagawa', b'Rudknapp', b'Ono', b'Al', b'X', b'Taro Yamada ',
             b'Pierre Van Der Sar', b'Seigo Kawamoto', b'T.Ishiwatari', b'Dai Sasaki']
    for nm in names:
        got = run_sim(code, base, nm, fmt1, fmt2, sprintf)['text']
        exp = reference(nm)
        print('%-22r -> %-12r %s' % (nm, got, 'ok' if got == exp else 'MISMATCH %r' % exp))
        assert got == exp
    print('bytes:', len(code), 'of', ROUTINE_LEN, '(pool words included)')


if __name__ == '__main__':
    main()


def emit(path=None):
    """patch bytes for every site: {file: {offset: hex}} (written to build/s7/shortname_patch.json); each site is checked for the
    exact original routine (all 11 are byte-identical apart from the three pool words) and the new code is run in the simulator."""
    import json
    import overlay
    ref = None
    res = {}
    for f, o in SITES:
        d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', f + '.BIN'), 'rb').read()
        base = overlay.unpack_overlay(d)['load_addr']
        ent = o + ENTRY
        orig = d[ent:ent + ROUTINE_LEN]
        code_part = orig[:0x8c]
        if ref is None:
            ref = code_part
        assert code_part == ref, f + ': routine differs'
        fmt1, spf, fmt2 = struct.unpack_from('<III', orig, 0x8c)
        new = build(base + ent, fmt1, spf, fmt2)
        assert len(new) <= ROUTINE_LEN
        new = new + b'\x09\x00' * ((ROUTINE_LEN - len(new)) // 2)
        for nm in (b'Taiyo Yamada', b'H. Nakata', b'Ono', b'Al'):
            got = run_sim(new, base + ent, nm, fmt1, fmt2, spf)['text']
            assert got == reference(nm), (f, nm, got)
        res[f] = {'offset': ent, 'va': base + ent, 'old': orig.hex(), 'new': new.hex()}
    out = path or os.path.join(ROOT, 'build', 's7', 'shortname_patch.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, 'w'), indent=1)
    print('wrote', out, len(res), 'sites')


if '--emit' in sys.argv:
    emit()
