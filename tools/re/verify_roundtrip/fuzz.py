import sys, random, os
sys.path.insert(0,'tools')
import bzlib
fails=[]
def check(x, m, tag):
    try:
        p = bzlib.compress(x, m)
        # independent limit checks: decode w/ size
        y = bzlib.decompress(p, len(x), m)
        if y != x: fails.append((m,tag,len(x),'mismatch')); return
        # also decode with orig_size None
        if bzlib.decompress(p, None, m) != x and m!='-nc--': fails.append((m,tag,len(x),'mismatch-nosize'))
        # trailing garbage after end token should be ignored
        if m!='-nc--' and bzlib.decompress(p+b'\xff\x00\x13', len(x), m) != x: fails.append((m,tag,len(x),'trailing'))
    except Exception as e:
        fails.append((m,tag,len(x),repr(e)))
rnd = random.Random(1)
cases=[]
sizes=[0,1,2,3,4,5,7,8,9,15,16,17,31,32,33,63,64,65,127,128,129,130,255,256,257,258,259,260,261,510,511,512,513,514,515,516,517,518,519,520,1000,1024,4096,65535,65536,65537,100000]
for n in sizes:
    cases += [('zeros',bytes(n)),('ff',b'\xff'*n),('rand',bytes(rnd.getrandbits(8) for _ in range(n))),
              ('ab',(b'ab'*n)[:n]),('abc',(b'abc'*n)[:n]),('inc',bytes(i&255 for i in range(n)))]
    # repeat with period around windows
    for per in (1,2,3,4,16,17,127,128,129,255,256,257,258,511,512,513,514,516):
        blk=bytes(rnd.getrandbits(8) for _ in range(per))
        cases.append(('per%d'%per,(blk*(n//per+1))[:n]))
# low-entropy random
for t in range(300):
    n=rnd.choice([rnd.randint(0,40),rnd.randint(0,700),rnd.randint(0,3000)])
    k=rnd.choice([1,2,3,4,16])
    cases.append(('lowent%d'%k,bytes(rnd.randrange(k) for _ in range(n))))
    # structured: copies of earlier segments
    b=bytearray()
    while len(b)<n:
        if b and rnd.random()<.6:
            d=rnd.randint(1,min(len(b),600)); l=rnd.randint(1,300)
            for _ in range(l): b.append(b[-d])
        else: b.append(rnd.getrandbits(8))
    cases.append(('copies',bytes(b[:n])))
for tag,x in cases:
    check(x,'-bz--',tag)
    if len(x)%2==0: check(x,'-bzw-',tag)
    else:
        try: bzlib.compress(x,'-bzw-'); fails.append(('-bzw-',tag,len(x),'odd accepted'))
        except ValueError: pass
        check(x+b'\0','-bzw-',tag+'+pad')
    check(x,'-nc--',tag)
# format limit checks: parse tokens
def tokens_bz(p):
    i=0;ok=True
    while True:
        f=p[i];i+=1
        for _ in range(8):
            if f&1: i+=1
            else:
                b=p[i];i+=1
                if b&0x80: pass
                else:
                    b2=p[i];i+=1
                    if b2==0: return i==len(p)
        f>>=1
    return None
print('cases',len(cases),'fails',len(fails))
for f in fails[:40]: print(f)
