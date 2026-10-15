from pathlib import Path
import struct,json
from PIL import Image
from patch_ui_graphics import draw,erase,palette,nearest
R=Path(__file__).resolve().parent.parent

def patch_menu_animation(source,out):
 reports=[];D=R/'work/graphics/animation_patched';D.mkdir(exist_ok=True)
 for footer in [0x8364d4,0x839224]:
  q=list(struct.unpack_from('<9I',source,footer));p0,p1,p2,desc,pal,tile,_,_= [v-0x8000000 for v in q[:8]];count=(p1-p2)//4;tiles=bytearray();descs=bytearray();layouts=bytearray()
  for frame in range(count):
   first,num=struct.unpack_from('<HH',source,p2+frame*4);objects=[]
   for k in range(num):
    z=list(struct.unpack_from('<10H',source,desc+(first+k)*20));w=z[3]&255;h=z[3]>>8
    x=z[5] if z[5]<32768 else z[5]-65536;y=z[6] if z[6]<32768 else z[6]-65536
    objects.append((z,x,y,w,h))
   layouts.extend(struct.pack('<HH',len(descs)//20,num))
   if not objects:continue
   x0=min(o[1] for o in objects);y0=min(o[2] for o in objects);w=max(o[1]+o[3] for o in objects)-x0;h=max(o[2]+o[4] for o in objects)-y0
   im=Image.new('RGBA',(w,h))
   for z,x,y,ow,oh in objects:
    pp=palette(source,pal+(z[2]&255)*32)
    for yy in range(oh):
     for xx in range(ow):
      at=tile+z[0]*32+(yy//8*(ow//8)+xx//8)*32+yy%8*4+xx%8//2;b=out[at];idx=b>>(4*(xx%2))&15
      if idx:im.putpixel((x-x0+xx,y-y0+yy),pp[idx])
   if frame not in [0,4,8]:
    im=erase(im,(16,14,w,49))
    lettering=Image.new('RGBA',(104,40));lines=['이야기 모드','???????' if frame<5 else '도전 모드'] if footer==0x8364d4 else ['저장한 곳부터','집으로 돌아가기','게임 종료']
    for n,text in enumerate(lines):draw(lettering,text,52,n*(16 if footer==0x8364d4 else 11),9,(32,24,24,255),True)
    overlay=Image.new('RGBA',im.size);overlay.alpha_composite(lettering,(w-12-104,20 if footer==0x8364d4 else 17));overlay.paste((0,0,0,0),(0,0,16,h));im.alpha_composite(overlay)
   im.save(D/f'{footer:06x}_{frame:03}.png')
   for z,x,y,ow,oh in objects:
    pp=palette(source,pal+(z[2]&255)*32);z[0]=len(tiles)//32
    for ty in range(oh//8):
     for tx in range(ow//8):
      for yy in range(8):
       for xx in range(0,8,2):
        vals=[]
        for dx in [0,1]:
         col=im.getpixel((x-x0+tx*8+xx+dx,y-y0+ty*8+yy));vals.append(0 if col[3]==0 else nearest(col,pp))
        tiles.append(vals[0]|vals[1]<<4)
    descs.extend(struct.pack('<10H',*z))
  assert len(tiles)<=65535
  out.extend(b'\0'*((-len(out))%4));t=len(out);out.extend(tiles);d=len(out);out.extend(descs);f=len(out);out.extend(layouts);a=len(out);out.extend(source[p1:p0])
  q[1]=0x8000000+a;q[2]=0x8000000+f;q[3]=0x8000000+d;q[5]=q[7]=0x8000000+t;q[8]=(q[8]&0xffff0000)|len(tiles);struct.pack_into('<9I',out,footer,*q)
  reports.append({'resource':hex(footer),'frames':count,'tile_bytes':len(tiles),'all_partial_open_frames_localized':True})
 return reports
