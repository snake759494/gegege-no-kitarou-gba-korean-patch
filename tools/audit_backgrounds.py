from pathlib import Path
from PIL import Image,ImageDraw
import struct,json
R=Path('.');r=next(R.glob('*Japan*.gba')).read_bytes();D=R/'work/graphics/backgrounds';D.mkdir(parents=True,exist_ok=True);rows=[];seen=set()
for a in range(0,0x100000-32,4):
 q=struct.unpack_from('<8I',r,a)
 if not(q[0]==q[1] and q[2]==q[3] and q[4]==q[5] and q[6]==q[7]):continue
 t,p,m,c=[q[i]-0x8000000 for i in [0,2,4,6]]
 if not(0x800000<=t<p<m<c<len(r) and (p-t,c-m) in [(0x4000,0x400),(0x5000,0x500)] and m-p==512) or t in seen:continue
 seen.add(t);height=(c-m)//8;pal=struct.unpack_from('<256H',r,p);im=Image.new('RGB',(256,height))
 for y in range(height):
  for x in range(256):
   en=struct.unpack_from('<H',r,m+(y//8*32+x//8)*2)[0];xx=7-x%8 if en&1024 else x%8;yy=7-y%8 if en&2048 else y%8;b=r[t+(en&1023)*32+yy*4+xx//2];idx=(b>>(4*(xx%2))&15)+r[c+y//8*32+x//8]*16;v=pal[idx];im.putpixel((x,y),((v&31)*8,((v>>5)&31)*8,((v>>10)&31)*8))
 id=f'{t:06x}';im.save(D/(id+'.png'));rows.append(dict(id=id,tiles=t,palette=p,tilemap=m,banks=c,table=a,height=height))
(D/'index.json').write_text(json.dumps(rows,indent=2));print('BGs',len(rows))
for page in range((len(rows)+23)//24):
 sh=Image.new('RGB',(1024,1068),(60,60,60));d=ImageDraw.Draw(sh)
 for j,o in enumerate(rows[page*24:page*24+24]):
  im=Image.open(D/(o['id']+'.png'));x=j%4*256;y=j//4*178;sh.paste(im,(x,y));d.text((x,y+161),o['id'],fill='yellow')
 sh.save(D/f'contact_{page:02}.png')
