"""Small two-pass SH-4 assembler (integer subset) for the font patch (docs/font-patch-design.md).

Written from the SH-4 software manual encodings, independent of capstone; the patch generator
(fontpatch.py) cross-checks every emitted word against capstone's decoder (canonical text must match).

Syntax (capstone style):  mov #imm,rN | mov rM,rN | mov.b/.w/.l @(r0,rM),rN | mov.l @(label),rN (pc-relative,
mov.w too) | add #imm,rN | add/addc/sub/and/or/xor/cmp/eq|gt|ge|hi|hs/tst/mul.l rM,rN | extu.b/.w rM,rN |
sts macl,rN | shll/shlr/shar/shll2/shll8/shll16 rN | bra/bsr/bt/bf/bt/s/bf/s label | jsr/jmp @rN | rts | nop |
.long expr | .word expr | .align 4 | label:
Branch/PC-relative displacements are computed from the address given to assemble(); reach and the
4-byte literal alignment rule are checked (ValueError on violation).
"""
import re
import struct

REG = {'r%d' % i: i for i in range(16)}


def _r(s):
    s = s.strip().lower()
    if s not in REG:
        raise ValueError('bad register %r' % s)
    return REG[s]


def _imm(s):
    s = s.strip()
    if s.startswith('#'):
        s = s[1:]
    return int(s, 0)


def _canon_imm(v):
    return str(v)


class Asm:
    def __init__(self, origin, symbols=None):
        self.origin = origin
        self.sym = dict(symbols or {})
        self.items = []          # (kind, data, text)

    # -- parsing ------------------------------------------------------------------------------
    def parse(self, src):
        for raw in src.splitlines():
            line = raw.split(';')[0].strip()
            if not line:
                continue
            while True:
                m = re.match(r'^([A-Za-z_][\w]*):\s*(.*)$', line)
                if not m:
                    break
                self.items.append(('label', m.group(1), ''))
                line = m.group(2).strip()
            if not line:
                continue
            if line.startswith('.align'):
                self.items.append(('align', int(line.split()[1], 0), line))
            elif line.startswith('.long'):
                self.items.append(('long', line.split(None, 1)[1].strip(), line))
            elif line.startswith('.word'):
                self.items.append(('word', line.split(None, 1)[1].strip(), line))
            else:
                self.items.append(('ins', line, line))
        return self

    def _val(self, expr):
        expr = expr.strip()
        if expr in self.sym:
            return self.sym[expr]
        return int(expr, 0)

    # -- two passes -----------------------------------------------------------------------------
    def assemble(self):
        # pass 1: addresses
        a = self.origin
        for kind, data, text in self.items:
            if kind == 'label':
                self.sym[data] = a
            elif kind == 'align':
                while a % data:
                    a += 2
            elif kind == 'long':
                a += 4
            elif kind in ('word', 'ins'):
                a += 2
        # pass 2: encode
        out = []        # (addr, bytes, canonical text)
        a = self.origin
        for kind, data, text in self.items:
            if kind == 'label':
                continue
            if kind == 'align':
                while a % data:
                    out.append((a, struct.pack('<H', 0x0009), 'nop'))
                    a += 2
                continue
            if kind == 'long':
                v = self._val(data) & 0xFFFFFFFF
                out.append((a, struct.pack('<I', v), '.long 0x%08x' % v))
                a += 4
                continue
            if kind == 'word':
                v = self._val(data) & 0xFFFF
                out.append((a, struct.pack('<H', v), '.word 0x%04x' % v))
                a += 2
                continue
            w, canon = self._enc(data, a)
            out.append((a, struct.pack('<H', w), canon))
            a += 2
        return out

    # -- encoder --------------------------------------------------------------------------------
    def _enc(self, line, a):
        m = re.match(r'^(\S+)\s*(.*)$', line)
        op, args = m.group(1).lower(), m.group(2).strip()
        ops = [x.strip() for x in re.split(r',(?![^()]*\))', args)] if args else []

        def f4(hi, n, mm, lo):
            return (hi << 12) | (n << 8) | (mm << 4) | lo

        if op == 'nop':
            return 0x0009, 'nop'
        if op == 'rts':
            return 0x000B, 'rts'
        if op == 'mov':
            s, d = ops
            if s.startswith('#'):
                v = _imm(s)
                if not -128 <= v <= 127:
                    raise ValueError('imm8 range: ' + line)
                n = _r(d)
                return 0xE000 | (n << 8) | (v & 0xFF), 'mov #%d,r%d' % (v, n)
            mm, n = _r(s), _r(d)
            return f4(6, n, mm, 3), 'mov r%d,r%d' % (mm, n)
        if op in ('mov.b', 'mov.w', 'mov.l'):
            s, d = ops
            sz = {'mov.b': 0, 'mov.w': 1, 'mov.l': 2}[op]
            mm = re.match(r'^@\(r0,(r\d+)\)$', s.lower())
            if mm:                                  # load, indexed
                rm, n = _r(mm.group(1)), _r(d)
                return f4(0, n, rm, 0xC + sz), '%s @(r0,r%d),r%d' % (op, rm, n)
            mm = re.match(r'^@\(r0,(r\d+)\)$', d.lower())
            if mm:                                  # store, indexed
                rn, m2 = _r(mm.group(1)), _r(s)
                return f4(0, rn, m2, 4 + sz), '%s r%d,@(r0,r%d)' % (op, m2, rn)
            mm = re.match(r'^@\(([A-Za-z_]\w*|0x[0-9a-fA-F]+),pc\)$', s, re.I)
            if mm and op in ('mov.w', 'mov.l'):     # pc-relative literal
                tgt = self._val(mm.group(1))
                n = _r(d)
                if op == 'mov.l':
                    if tgt % 4:
                        raise ValueError('literal %#x not 4-aligned: %s' % (tgt, line))
                    base = (a & ~3) + 4
                    disp = (tgt - base) // 4
                    if tgt < base or disp > 255:
                        raise ValueError('mov.l literal %#x out of reach from %#x' % (tgt, a))
                    return 0xD000 | (n << 8) | disp, 'mov.l 0x%08x,r%d' % (tgt, n)
                if tgt % 2:
                    raise ValueError('word literal not 2-aligned')
                base = a + 4
                disp = (tgt - base) // 2
                if tgt < base or disp > 255:
                    raise ValueError('mov.w literal out of reach')
                return 0x9000 | (n << 8) | disp, 'mov.w 0x%08x,r%d' % (tgt, n)
            mm = re.match(r'^@r(\d+)$', s.lower())
            if mm:                                  # mov.x @rm,rn
                rm, n = int(mm.group(1)), _r(d)
                return f4(6, n, rm, sz), '%s @r%d,r%d' % (op, rm, n)
            raise ValueError('unsupported addressing: ' + line)
        if op == 'add':
            s, d = ops
            n = _r(d)
            if s.startswith('#'):
                v = _imm(s)
                if not -128 <= v <= 127:
                    raise ValueError('imm8 range: ' + line)
                return 0x7000 | (n << 8) | (v & 0xFF), 'add #%d,r%d' % (v, n)
            mm = _r(s)
            return f4(3, n, mm, 0xC), 'add r%d,r%d' % (mm, n)
        two = {'addc': (3, 0xE), 'sub': (3, 0x8), 'cmp/eq': (3, 0x0), 'cmp/ge': (3, 0x3), 'cmp/gt': (3, 0x7),
               'cmp/hi': (3, 0x6), 'cmp/hs': (3, 0x2), 'tst': (2, 0x8), 'and': (2, 0x9), 'or': (2, 0xB),
               'xor': (2, 0xA), 'extu.b': (6, 0xC), 'extu.w': (6, 0xD), 'exts.b': (6, 0xE), 'exts.w': (6, 0xF),
               'neg': (6, 0xB), 'mul.l': (0, 0x7)}
        if op in two:
            hi, lo = two[op]
            s, d = ops
            mm, n = _r(s), _r(d)
            return f4(hi, n, mm, lo), '%s r%d,r%d' % (op, mm, n)
        if op == 'movt':
            n = _r(ops[0])
            return f4(0, n, 2, 9), 'movt r%d' % n
        if op == 'sts' and ops[0].lower() == 'macl':
            n = _r(ops[1])
            return f4(0, n, 1, 0xA), 'sts macl,r%d' % n
        one = {'shll': 0x00, 'shlr': 0x01, 'shar': 0x21, 'shll2': 0x08, 'shlr2': 0x09, 'shll8': 0x18,
               'shlr8': 0x19, 'shll16': 0x28, 'shlr16': 0x29, 'cmp/pl': 0x15, 'cmp/pz': 0x11, 'dt': 0x10}
        if op in one:
            n = _r(ops[0])
            return 0x4000 | (n << 8) | one[op], '%s r%d' % (op, n)
        if op in ('jsr', 'jmp'):
            n = _r(ops[0].lstrip('@'))
            return 0x4000 | (n << 8) | (0x0B if op == 'jsr' else 0x2B), '%s @r%d' % (op, n)
        if op in ('bra', 'bsr', 'bt', 'bf', 'bt/s', 'bf/s'):
            tgt = self._val(ops[0])
            disp = (tgt - (a + 4)) // 2
            if (tgt - (a + 4)) % 2:
                raise ValueError('odd branch target')
            if op in ('bra', 'bsr'):
                if not -2048 <= disp <= 2047:
                    raise ValueError('bra out of reach')
                return (0xA000 if op == 'bra' else 0xB000) | (disp & 0xFFF), '%s 0x%08x' % (op, tgt)
            if not -128 <= disp <= 127:
                raise ValueError('%s out of reach (%d) at %#x -> %#x' % (op, disp, a, tgt))
            code = {'bt': 0x8900, 'bf': 0x8B00, 'bt/s': 0x8D00, 'bf/s': 0x8F00}[op]
            return code | (disp & 0xFF), '%s 0x%08x' % (op, tgt)
        raise ValueError('unsupported instruction: ' + line)


def assemble(src, origin, symbols=None):
    """returns (bytes, listing[(addr, word_bytes, canonical_text)], symbols)"""
    a = Asm(origin, symbols).parse(src)
    out = a.assemble()
    return b''.join(x[1] for x in out), out, a.sym
