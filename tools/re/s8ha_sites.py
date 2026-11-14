"""s8ha: print the code around every strlen literal load of the player-card panel of an overlay: from the load up to the first instructions after the jsr.
usage: s8ha_sites.py FILE BASE LOAD_ADDR..."""
import struct, sys
import capstone as cs
md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
d = open(sys.argv[1], 'rb').read()
base = int(sys.argv[2], 16)
for a in sys.argv[3:]:
    a = int(a, 16)
    print('-----', hex(a))
    o = a - base
    jsr_seen = 0
    for k in range(o, o + 60, 2):
        w = struct.unpack_from('<H', d, k)[0]
        i = list(md.disasm(d[k:k + 2], base + k))
        t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
        print('%08x  %04x  %s' % (base + k, w, t))
        if t.startswith('jsr'):
            jsr_seen = 1
        elif jsr_seen:
            jsr_seen += 1
            if jsr_seen > 9:
                break
