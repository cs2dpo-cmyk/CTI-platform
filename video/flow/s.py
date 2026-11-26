
import os
from PIL import Image, ImageDraw, ImageFont
src='C:/dev/cti-platform/video/flow/frames'
files=sorted(f for f in os.listdir(src) if f.endswith('.jpg'))
pick=[files[i] for i in [0,12,20,30,40,52,66,80,90,97] if i < len(files)]
cols,rows=2,5
tw,th=880,550
sheet=Image.new('RGB',(cols*tw+30, rows*th+30),(8,8,10))
d=ImageDraw.Draw(sheet); f=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
for i,n in enumerate(pick):
    im=Image.open(os.path.join(src,n)).convert('RGB').resize((tw-10,th-10),Image.LANCZOS)
    x=10+(i%cols)*tw; y=10+(i//cols)*th
    sheet.paste(im,(x,y)); d.text((x+4,y+4),n,font=f,fill=(230,190,110))
sheet.save('C:/dev/cti-platform/video/flow/sheet.png'); print(sheet.size, len(files))
