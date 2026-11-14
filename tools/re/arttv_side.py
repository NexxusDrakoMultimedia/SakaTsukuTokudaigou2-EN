from PIL import Image
import glob
fs=[glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/'+t+'_*.png')[0] for t in ('04081','04084')]
m=Image.new('RGB',(1024,330),(110,110,110))
for i,f in enumerate(fs):
    im=Image.open(f).convert('RGBA').crop((0,0,128,82)); b=Image.new('RGBA',im.size,(110,110,110,255)); b.alpha_composite(im)
    m.paste(b.convert('RGB').resize((512,328),Image.NEAREST),(i*512,0))
m.save('build/art_tv/side.png')
