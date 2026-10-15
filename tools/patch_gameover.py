from pathlib import Path
import struct,json
import numpy as np
from PIL import Image,ImageFilter
R=Path(__file__).resolve().parent.parent

def patch_gameover(source,out):
 f=0x858fc0;q=list(struct.unpack_from('<9I',source,f));p=[x-0x8000000 for x in q[:8]]
 im=Image.open(R/'assets/gameover_lettering_source.png').convert('L');a=np.array(im);on=(a<120).any(axis=0);runs=[];s=None
 for x,v in enumerate(list(on)+[False]):
  if v and s is None:s=x
  if not v and s is not None:
   if x-s>15:runs.append((s,x))
   s=None
 merged=[]
 for left,right in runs:
  if merged and left-merged[-1][1]<60:merged[-1]=(merged[-1][0],right)
  else:merged.append((left,right))
 runs=merged
 assert len(runs)==5,runs
 pp=struct.unpack_from('<16H',source,p[4]);pal=[((v&31)*8,((v>>5)&31)*8,((v>>10)&31)*8) for v in pp]
 tiles=bytearray();images=[]
 for left,right in runs:
  glyph=im.crop((left,0,right,im.height));box=Image.eval(glyph,lambda v:255-v).point(lambda v:255 if v>135 else 0).getbbox();glyph=glyph.crop(box)
  w=min(24,round(glyph.width*24/glyph.height));mask=np.array(glyph.resize((w,24),Image.Resampling.LANCZOS))<150
  canvas=Image.new('L',(32,32));x0=(32-w)//2;y0=4
  for yy,xx in zip(*np.where(mask)):canvas.putpixel((x0+int(xx),y0+int(yy)),255)
  rim=np.array(canvas.filter(ImageFilter.MaxFilter(3)))>0;ink=np.array(canvas)>0;idx=np.zeros((32,32),dtype='uint8');idx[rim]=1
  for y in range(32):
   color=(248,48+int(200*min(1,max(0,(y-4)/23))),0);n=min(range(1,16),key=lambda i:sum((color[j]-pal[i][j])**2 for j in range(3)));idx[y,ink[y]]=n
  images.append(idx)
 images.append(np.zeros((32,32),dtype='uint8'))
 for idx in images:
  for ty in range(4):
   for tx in range(4):
    b=idx[ty*8:ty*8+8,tx*8:tx*8+8].flatten();tiles.extend(bytes(int(b[i])|int(b[i+1])<<4 for i in range(0,64,2)))
 desc=struct.unpack_from('<10H',source,p[3]);descs=bytearray();layouts=bytearray();frames=bytearray();names=bytearray();nameptr=struct.unpack_from('<I',source,p[0])[0]
 for i in range(6):
  z=list(desc);z[0]=i*16;descs.extend(struct.pack('<10H',*z));layouts.extend(struct.pack('<HH',i,1));frames.extend(struct.pack('<HH',i,1));names.extend(struct.pack('<IHH',nameptr,i,1))
 out.extend(bytes((-len(out))%4));tile_at=len(out);out.extend(tiles);desc_at=len(out);out.extend(descs);layout_at=len(out);out.extend(layouts);frame_at=len(out);out.extend(frames);name_at=len(out);out.extend(names)
 q[0]=0x8000000+name_at;q[1]=0x8000000+frame_at;q[2]=0x8000000+layout_at;q[3]=0x8000000+desc_at;q[5]=q[7]=0x8000000+tile_at;q[8]=6<<16|len(tiles);struct.pack_into('<9I',out,f,*q)
 assert source[0xc439b:0xc43a2]==bytes([0,1,2,3,1,4,1]);out[0xc439b:0xc43a2]=bytes([5,0,1,2,3,4,5])
 D=R/'work/graphics/gameover';D.mkdir(exist_ok=True)
 for i,idx in enumerate(images):
  result=Image.new('RGBA',(32,32))
  for y in range(32):
   for x in range(32):
    v=int(idx[y,x])
    if v:result.putpixel((x,y),pal[v]+(255,))
  result.save(D/f'glyph_{i}.png')
 return {'native_actor_order':[5,0,1,2,3,4,5],'text':'게임종료!','font_used':False,'unique_glyphs':5,'blank_group':5,'tile_offset':hex(tile_at),'reused_long_vowel_glyph_replaced':True}
