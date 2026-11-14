import pickle,collections,sys
sys.path.insert(0,'tools')
A=pickle.load(open('tools/re/verify_gt/anom.pkl','rb'))
unc=[a for a in A if a[2].startswith('uncovered')]
print('rejected',sum('REJECTED' in a[2] for a in unc))
print(collections.Counter(a[0] for a in unc).most_common(40))
for a in unc:
    if 'REJECTED' in a[2]: print(a)
pv=[a for a in A if a[2].startswith('pvr')]
print(collections.Counter(a[2][10:18] for a in pv).most_common(10))
for a in pv[:8]: print(a)
for a in A:
    if a[2].startswith('tail'): print(a)
