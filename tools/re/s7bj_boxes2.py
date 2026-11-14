import numpy as np
from PIL import Image
a=np.asarray(Image.open('build/tex/ATFIRST__TITLE.DAT/00101_TITLE.DAT_9.png').convert('RGBA')).astype(int)
l=a[...,:3].sum(2)//3
sub=l[26:66,190:320]
cols=(sub<110).sum(0)
print(' '.join('%d'%c for c in cols))
rows=(sub<110).sum(1); print(' '.join('%d'%c for c in rows))
# strip text
sub=l[203:229,80:430]; cols=(sub<100).sum(0); print(' '.join('%d'%c for c in cols))
print(' '.join('%d'%c for c in (sub<100).sum(1)))
