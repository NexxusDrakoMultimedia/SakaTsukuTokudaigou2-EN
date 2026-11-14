d = open('extracted/DPETC/MESSAGE.INI','rb').read()
for o in (0x3cd3,0x7a09,0x890a,0x89a6,0xa4e6,0xab98):
    print(hex(o), d[o-40:o+30].decode('cp932','replace').replace('\r\n','|').replace('\n','|'))
