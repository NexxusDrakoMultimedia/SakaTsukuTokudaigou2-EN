"""s7bj: dump pristine PNGs of the package J textures over a checkerboard for viewing."""
import sys
from PIL import Image
srcs = {
 '00101':'build/tex/ATFIRST__TITLE.DAT/00101_TITLE.DAT_9.png',
 '00108':'build/tex/ATFIRST__TITLEM.DAT/00108_TITLEM.DAT_6.png',
 '00109':'build/tex/ATFIRST__TITLEM.DAT/00109_TITLEM.DAT_7.png',
 '00110':'build/tex/ATFIRST__TITLEM.DAT/00110_TITLEM.DAT_8.png',
}
for k,p in srcs.items():
    im=Image.open(p).convert('RGBA')
    bg=Image.new('RGBA',im.size,(90,160,90,255))
    bg.alpha_composite(im)
    bg.save('build/s7/titles/orig_%s.png'%k)
    print(k,im.size)
