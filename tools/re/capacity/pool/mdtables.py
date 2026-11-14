import json
R='tools/re/capacity/pool/results/'
p=json.load(open(R+'pools.json'))
top=sorted(p,key=lambda s:-p[s]['all_jp'])[:12]
for sp,title in (('0','uniform ratio (every string scaled by exactly r)'),('0.5','mixed ratio (per string r*(1+0.5*U(-1,1)), mean r)')):
    g=json.load(open(R+'grid_s%s.json'%sp))
    print('\n%s: share of strings that overflow, in %%, "a / a2 / b0 / b2" (a per-string in place, a2 current textdb.insert_image, b0 pool-local repack, b2 repack+cross-pool+dup sharing)\n'%title)
    print('| image | strings | r=0.8 | r=1.0 | r=1.2 | r=1.5 | r=2.0 |'); print('|---|---|---|---|---|---|---|')
    for s in top+['ALL']:
        if s=='ALL':
            row=['**all 114**',str(sum(v['a_inplace']['1.0']['n'] for v in g.values()))]
        else:
            row=[s.split('/')[-1][:-4] if not s.startswith('ATFIRST') else 'ATFIRST/'+s.split('/')[-1][:-4], str(g[s]['a_inplace']['1.0']['n'])]
        for r in ('0.8','1.0','1.2','1.5','2.0'):
            cells=[]
            for m in ('a_inplace','a2_textdb','b0_pool_local','b2_pool_dup_cross'):
                if s=='ALL':
                    n=sum(v[m][r]['n'] for v in g.values()); o=sum(v[m][r]['n_over'] for v in g.values())
                else:
                    n=g[s][m][r]['n']; o=g[s][m][r]['n_over']
                cells.append('%.0f'%(100*o/n) if o/n>=0.005 or o==0 else '%.1f'%(100*o/n))
            row.append(' / '.join(cells))
        print('| '+' | '.join(row)+' |')
