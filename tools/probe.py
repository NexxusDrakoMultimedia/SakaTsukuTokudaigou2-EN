import sys,glob,struct
P="Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan) (Track %d).bin"
for t in (1,3,5):
    f=open(P%t,'rb'); n=0
    d=f.read(2352*20)
    print("track",t,"sectors",__import__('os').path.getsize(P%t)//2352)
    print(" sync",d[:12].hex(),"hdr",d[12:16].hex())
    print(" s0 user[:48]",d[16:64])
    for s in range(14,20):
        u=d[s*2352+16:s*2352+16+2048]
        print(" sec",s,u[:8])
