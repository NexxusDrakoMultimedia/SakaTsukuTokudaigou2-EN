import sys, random, time
sys.path.insert(0,'tools')
import bzlib
rnd=random.Random(7)
def audit(p, m, outlen):
    """independent token walk; returns (maxlen,maxdist,errors)"""
    errs=[];i=0;out=0;maxl=0;maxd=0
    wide = m=='-bzw-'
    while True:
        if wide: f=(p[i]<<8)|p[i+1]; i+=2; nb=16
        else: f=p[i]; i+=1; nb=8
        for _ in range(nb):
            if f&1: i+= 2 if wide else 1; out+= 2 if wide else 1
            else:
                if wide:
                    lo,hi=p[i],p[i+1]; i+=2
                    if hi==0:
                        if i!=len(p): errs.append('trailing bytes after end')
                        if out!=outlen: errs.append('len')
                        return maxl,maxd,errs
                    l=(hi+1)*2; d=512-lo*2
                else:
                    b=p[i]; i+=1
                    if b&0x80: l=(b&7)+2; d=16-((b>>3)&15)
                    else:
                        b2=p[i]; i+=1
                        if b2==0:
                            if i!=len(p): errs.append('trailing bytes after end')
                            if out!=outlen: errs.append('len')
                            return maxl,maxd,errs
                        l=b2+1; d=128-b
                if d>out or d<1: errs.append('dist %d > out %d'%(d,out))
                if l<2: errs.append('short len')
                maxl=max(maxl,l); maxd=max(maxd,d); out+=l
            f>>=1
bad=[]
t=time.time()
for it in range(1500):
    n=rnd.choice([rnd.randint(0,300),rnd.randint(0,5000),rnd.randint(5000,40000)])*1
    n&=~1
    mode=rnd.random()
    b=bytearray()
    while len(b)<n:
        r=rnd.random()
        if b and r<.7:
            d=rnd.choice([1,2,3,15,16,17,127,128,129,255,256,257,512,513,rnd.randint(1,len(b))]); d=min(d,len(b))
            l=rnd.choice([2,3,9,10,255,256,257,258,512,513,rnd.randint(1,600)])
            for _ in range(l): b.append(b[-d])
        else:
            for _ in range(rnd.randint(1,6)): b.append(rnd.getrandbits(8) if mode<.5 else rnd.randrange(4))
    x=bytes(b[:n])
    for m in ('-bz--','-bzw-'):
        try:
            p=bzlib.compress(x,m)
            if bzlib.decompress(p,len(x),m)!=x: bad.append((m,it,len(x),'mismatch'));continue
            ml,md,e=audit(p,m,len(x))
            if e: bad.append((m,it,len(x),e[:2]))
            lim=(256,128) if m=='-bz--' else (512,512)
            if ml>lim[0] or md>lim[1]: bad.append((m,it,len(x),'limit',ml,md))
        except Exception as ex: bad.append((m,it,len(x),repr(ex)))
print('bad',len(bad),bad[:10],'t',time.time()-t)
# big
for name,x in (('zeros1M',bytes(1<<20)),('rand256k',bytes(rnd.getrandbits(8) for _ in range(1<<18)))):
    for m in ('-bz--','-bzw-'):
        t=time.time();p=bzlib.compress(x,m);ok=bzlib.decompress(p,len(x),m)==x
        print(name,m,len(p),ok,round(time.time()-t,1))
# expansion bound on random
x=bytes(rnd.getrandbits(8) for _ in range(10000))
for m in ('-bz--','-bzw-'): print('rand expand',m,len(bzlib.compress(x,m)))
# decoder robustness: garbage must raise DecodeError only
import os
exc={}
for k in range(3000):
    g=bytes(rnd.getrandbits(8) for _ in range(rnd.randint(0,60)))
    for m in ('-bz--','-bzw-'):
        try: bzlib.decompress(g,None,m)
        except bzlib.DecodeError: pass
        except Exception as e: exc[(m,type(e).__name__)]=g
print('non-DecodeError exceptions',exc)
