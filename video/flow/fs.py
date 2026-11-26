
import glob
from PIL import Image, ImageDraw, ImageFont
files=sorted(glob.glob('C:/dev/cti-platform/video/flow/f*.png'))
tw,th=860,484
sheet=Image.new('RGB',(tw*2+36, ((len(files)+1)//2)*(th+30)+8),(8,8,10))
d=ImageDraw.Draw(sheet); f=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
for i,p in enumerate(files):
    im=Image.open(p).convert('RGB').resize((tw,th),Image.LANCZOS)
    x=12+(i%2)*(tw+12); y=8+(i//2)*(th+30)
    sheet.paste(im,(x,y)); d.text((x+2,y+2),p.split('/')[-1],font=f,fill=(240,200,120))
sheet.save('C:/dev/cti-platform/video/flow/full_sheet.png'); print(sheet.size)
