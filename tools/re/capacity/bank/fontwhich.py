import sys
for n in ['ram_2400','live3_ram']:
    d=open('build/emu/%s.bin'%n,'rb').read()
    for f in ('/FONT.BIN','/ATFIRST/FONT.BIN','/ATFIRST/SHTEX0.ZAR','/ATFIRST/BAR.TBD','/ATFIRST/SECFTEX0.ZAR'):
        b=open('extracted'+f,'rb').read()
        base={'/FONT.BIN':0x8cd5c000,'/ATFIRST/FONT.BIN':0x8cd5c000,'/ATFIRST/SHTEX0.ZAR':0x8ce02000,'/ATFIRST/BAR.TBD':0x8ce2c000,'/ATFIRST/SECFTEX0.ZAR':0x8ce5c000}[f]
        o=base-0x8c000000
        seg=d[o:o+len(b)]
        eq=sum(1 for x,y in zip(seg,b) if x==y)
        print(n,f,len(b),'match %.4f'%(eq/len(b)),'first diff',next((i for i,(x,y) in enumerate(zip(seg,b)) if x!=y),None),'end addr %x'%(base+len(b)))
