from pathlib import Path
from PIL import Image,ImageDraw
import struct,json
R=Path('.');r=next(R.glob('*Japan*.gba')).read_bytes();D=R/'work/graphics/sprites';D.mkdir(exist_ok=True,parents=True);resources=[]
for a in range(0x800000,0xc80000-36,4):
 q=struct.unpack_from('<9I',r,a)
 if q[5]!=q[7] or not all(0x08800000<=q[i]<0x08c80000 for i in range(8)):continue
 n=q[8]>>16;length=q[8]&65535
 if not 1<=n<=500 or not 32<=length<=0x8000 or length%32:continue
 ptr=[x-0x8000000 for x in q[:8]]
 if ptr[4]-ptr[5]!=length:continue
 p0,p1,p2,desc,pal,tile,_,_=ptr
 if not(desc<=p2<=p1<=p0<=a):continue
 for j in range(n):
  np,start,count=struct.unpack_from('<IHH',r,p0+j*8);np-=0x8000000
  if not 0<=np<len(r):continue
  try:name=r[np:r.index(0,np)].decode('cp932')
  except:continue
  if len(name)>80:continue
  frame,dur=struct.unpack_from('<HH',r,p1+start*4);first,num=struct.unpack_from('<HH',r,p2+frame*4)
  if num>100 or first*20+desc>=p2:continue
  objs=[]
  for k in range(num):
   z=struct.unpack_from('<10H',r,desc+(first+k)*20);w=z[3]&255;h=z[3]>>8
   if w not in [8,16,32,64] or h not in [8,16,32,64]:break
   x=z[5] if z[5]<32768 else z[5]-65536;y=z[6] if z[6]<32768 else z[6]-65536
   objs.append(dict(tile=tile+z[0]*32,palette=pal+(z[2]&255)*32,x=x,y=y,w=w,h=h,descriptor=desc+(first+k)*20))
  if len(objs)!=num or not objs:continue
  x0=min(o['x'] for o in objs);y0=min(o['y'] for o in objs);x1=max(o['x']+o['w'] for o in objs);y1=max(o['y']+o['h'] for o in objs)
  if x1-x0>512 or y1-y0>512:continue
  im=Image.new('RGBA',(x1-x0,y1-y0))
  for o in objs:
   pp=struct.unpack_from('<16H',r,o['palette'])
   for y in range(o['h']):
    for x in range(o['w']):
     b=r[o['tile']+(y//8*(o['w']//8)+x//8)*32+y%8*4+x%8//2];c=b>>(4*(x%2))&15;v=pp[c]
     if c:im.putpixel((o['x']-x0+x,o['y']-y0+y),((v&31)*8,((v>>5)&31)*8,((v>>10)&31)*8,255))
  id=f'{a:06x}_{j:03}';im.save(D/(id+'.png'));resources.append(dict(id=id,name=name,footer=a,group=j,origin=[x0,y0],objects=objs))
(D/'index.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2),encoding='utf-8');print('resources',len(resources),'groups',len(set(o['footer'] for o in resources)))
# First UI resource groups through 0x86xxxx; numbered contact sheets.
ui=[o for o in resources if o['footer']<0x860000]
for page in range((len(ui)+47)//48):
 sh=Image.new('RGB',(960,720),(70,70,70));draw=ImageDraw.Draw(sh)
 for j,o in enumerate(ui[page*48:page*48+48]):
  im=Image.open(D/(o['id']+'.png'));im.thumbnail((154,100));x=j%6*160;y=j//6*90;sh.paste(im,(x,y),im);draw.text((x,y+75),o['id'],fill='yellow')
 sh.save(D/f'contact_{page:02}.png')
print('ui',len(ui))

