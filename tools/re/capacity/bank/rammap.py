import sys
names=['ram_2400','ram_5400','live1_ram','live3_ram']
D={n:open('build/emu/%s.bin'%n,'rb').read() for n in names}
print('block(64K)  nonzero%% per dump: '+' '.join(names))
for b in range(0,256):
    row=[]
    for n in names:
        s=D[n][b*0x10000:(b+1)*0x10000]
        row.append(100*(0x10000-s.count(0))//0x10000)
    print('%08x '%(0x8c000000+b*0x10000)+' '.join('%3d'%r for r in row))
