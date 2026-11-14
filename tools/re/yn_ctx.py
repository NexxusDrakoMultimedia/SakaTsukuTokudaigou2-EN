d = open('build/emu/t1_ram.bin','rb').read()
for o in (0x3948dc,0x3954ec,0x39afaf,0x39b114,0x39b246,0x39bcaf,0x39bcda,0x39f434):
    s = d[o-12:o+24]
    print(hex(o), s.decode('cp932','replace').replace('\n','|'))
