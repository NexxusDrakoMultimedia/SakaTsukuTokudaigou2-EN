"""s8fg: every hwptr record with a plain 'ptr@' pointer (not a table) whose pointer word was RELOCATED in prop10c (vs the original),
and a code-use heuristic: the pointer is loaded by mov.l @(d,pc),rN; if within the next 40 instructions rN (or a copy) meets a multiply,
an index shift/add, or an offset access beyond the string, the pointer is probably an ARRAY BASE, not a string.
usage: s8fg_relscan.py [DISC=prop10c] [FILE_SUBSTR]
Output: build/s8fg/relscan_<disc>.txt and stdout summary.  Read-only on project and discs."""
import glob
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D  # noqa: E402
import capstone as cs  # noqa: E402

md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)


def loads_of(buf, lit):
    """pcs of mov.l @(d,pc),rN that load the literal at file offset lit"""
    out = []
    for pc in range(max(0, lit - 1024), lit, 2):
        w = struct.unpack_from('<H', buf, pc)[0]
        if w >> 12 == 0xD and ((pc + 4) & ~3) + (w & 0xFF) * 4 == lit:
            out.append((pc, (w >> 8) & 15))
    return out


def uses(buf, pc, reg):
    """heuristic text of how reg is used in the next 40 instructions"""
    tags = []
    regs = {reg}
    for k in range(1, 41):
        o = pc + 2 * k
        if o + 2 > len(buf):
            break
        w = struct.unpack_from('<H', buf, o)[0]
        top = w >> 12
        n = (w >> 8) & 15
        m = (w >> 4) & 15
        if w in (0x000B,):
            break
        if top == 0x2 and (w & 0xF) in (0xE, 0xF) and (m in regs or n in regs):    # mulu.w / muls.w
            tags.append('mul')
        if top == 0x0 and (w & 0xF) == 0x7 and (m in regs or n in regs):            # mul.l
            tags.append('mul.l')
        if top == 0x6 and (w & 0xF) == 0x3 and m in regs:                            # mov rm,rn copy
            regs.add(n)
        if top == 0x3 and (w & 0xF) == 0xC and (m in regs or n in regs):             # add rm,rn
            tags.append('add')
        if top == 0x1 and n in regs:                                                 # mov.l rm,@(d,rn)
            tags.append('st@(d,r)')
        if top == 0x5 and m in regs:                                                 # mov.l @(d,rm),rn
            tags.append('ld.l@(d,r)%d' % ((w & 0xF) * 4))
        if top == 0x8 and (w >> 8) in (4, 5) and m in regs:                          # mov.b/w @(d,rm),r0
            tags.append('ld.b/w@(d,r)')
        if top == 0x8 and (w >> 8) in (0, 1) and m in regs:                          # mov.b/w r0,@(d,rm)
            tags.append('st.b/w@(d,r)')
    return tags


def main(argv):
    disc = argv[1] if len(argv) > 1 else 'prop10c'
    sub = argv[2].upper() if len(argv) > 2 else ''
    s0 = D.Source(ROOT, None)
    s1 = D.Source(os.path.join(ROOT, 'build', 'trial'), disc)
    f0 = {r.path.upper(): r for r in D.read_filesystem(s0)[3] if not r.isdir}
    f1 = {r.path.upper(): r for r in D.read_filesystem(s1)[3] if not r.isdir}
    lines = []
    for jp in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        bn = os.path.basename(jp)
        if not (bn.startswith('FLOW_PRG__') or bn.startswith('ATFIRST__')):
            continue
        rel = bn[:-6].replace('__', '/')
        if sub and sub not in rel.upper():
            continue
        recs = [json.loads(l) for l in open(jp, encoding='utf-8') if l.strip()]
        cand = []
        for r in recs:
            if r.get('fmt') != 'hwptr' or not r.get('refs') or not (r.get('en') or ''):
                continue
            m = re.search(r'ptr@([0-9a-f]+)', r.get('ctx', ''))
            if m and 'tbl@' not in r['ctx']:
                cand.append((r, int(m.group(1), 16)))
        if not cand:
            continue
        a = f0.get('/' + rel.upper())
        b = f1.get('/' + rel.upper())
        if a is None or b is None:
            continue
        o = s0.read(a.lba, a.size)
        p = s1.read(b.lba, b.size)
        for r, po in cand:
            off = int(r['id'].split('#')[1], 16)
            wo = struct.unpack_from('<I', o, po)[0]
            wp = struct.unpack_from('<I', p, po)[0]
            if wo == wp:
                continue
            ld = loads_of(o, po)
            tags = []
            for pc, reg in ld:
                tags += uses(o, pc, reg)
            line = '%-24s %06x refs=%-2s en=%-14r %s->%s loads=%d uses=%s' % (rel, off, r['refs'], r['en'][:14], '%08x' % wo, '%08x' % wp, len(ld), ','.join(sorted(set(tags))))
            lines.append(line)
    out = os.path.join(ROOT, 'build', 's8fg', 'relscan_%s.txt' % disc)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    flagged = [l for l in lines if 'mul' in l.split('uses=')[1] or 'add' in l.split('uses=')[1]]
    print('relocated plain-pointer hwptr records:', len(lines), ' with mul/add use heuristic:', len(flagged), '->', out)
    for l in flagged[:60]:
        print(l)


main(sys.argv)
