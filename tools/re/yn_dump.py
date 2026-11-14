d = open('extracted/2_DP.BIN','rb').read()
for o in (0x1877c0,):
    print(d[o:o+0x80].hex(' '))
    print(d[o:o+0x80])
