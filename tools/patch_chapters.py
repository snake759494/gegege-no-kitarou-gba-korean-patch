"""Hand-painted Korean chapter cards in original tile layers and brush silhouettes."""
from pathlib import Path
from PIL import Image,ImageFilter
import numpy as np,struct,json
from scipy.ndimage import label
from patch_ui_graphics import patch_bg
R=Path(__file__).resolve().parent.parent
TITLES=['키타로의 탄생','요괴 우시오니의 저주!','일본 정복! 팔백 리','거대 요괴 다이다라봇치','대한파! 냉동 요괴 유킨코의 덫!','요괴 아카시타! 오소레산의 결전!','키타로 사형 선고! 요괴 대재판!','요괴 반란! 중국 요괴의 역습!','위기일발! 요괴열도!!','어머니를 찾아 지옥으로']
def inkcrop(im):
 a=np.array(im.convert('RGB'));mask=(a.min(2)<120);yy,xx=np.where(mask);return im.crop((int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)))
def patch_chapters(r,out):
 src=Image.open(R/'assets/chapter_lettering_source.png').convert('RGB');a=np.array(src);ys=np.any(a.min(2)<120,axis=1);runs=[];start=None
 for y,on in enumerate(list(ys)+[False]):
  if on and start is None:start=y
  if not on and start is not None:
   if y-start>12:runs.append((start,y))
   start=None
 assert len(runs)==10,runs
 rows=json.loads((R/'work/graphics/chapters.json').read_text());reports=[]
 for i,o in enumerate(rows):
  original=Image.open(R/f'work/graphics/chapter_{i:02}.png').convert('RGBA');im=Image.new('RGBA',original.size);mask=original.getchannel('A');im.paste((248,248,248,255),(0,0,240,160),mask)
  art=inkcrop(Image.open(R/'assets/chapter_04_lettering_source.png').convert('RGB') if i==4 else src.crop((0,runs[i][0],src.width,runs[i][1])))
  box=mask.getbbox();x0,y0,x1,y1=box;target_w=min(224,max(180,x1-x0-8));target_h=min(34,max(24,y1-y0-10));art=art.resize((target_w,target_h),Image.Resampling.LANCZOS);aa=np.array(art);ink=(aa.min(2)<150);red=(aa[:,:,0]>aa[:,:,1]*1.6)&(aa[:,:,0]>60)&ink
  canvas=Image.new('RGBA',(240,160));ix=(240-target_w)//2;iy=max(0,(y0+y1-target_h)//2)
  for y,x in zip(*np.where(ink)):canvas.putpixel((ix+int(x),iy+int(y)),(208,0,24,255) if red[y,x] else (0,0,0,255))
  # White rim keeps black brush lettering readable at the original ragged edge.
  rim=canvas.getchannel('A').filter(ImageFilter.MaxFilter(3));im.paste((248,248,248,255),(0,0,240,160),rim);im.alpha_composite(canvas)
  idx=Image.new('L',(256,160));ar=np.array(im)
  for y in range(160):
   for x in range(240):
    rr,g,b,al=map(int,ar[y,x]);idx.putpixel((x,y),0 if not al else 1 if rr>g+40 else 2 if rr<100 else 15)
  tiles=[bytes(32)];lookup={bytes(32):0};maps=[]
  for ty in range(20):
   for tx in range(32):
    px=idx.crop((tx*8,ty*8,tx*8+8,ty*8+8)).tobytes();b=bytes(px[j]|px[j+1]<<4 for j in range(0,64,2))
    if b not in lookup:lookup[b]=len(tiles);tiles.append(b)
    maps.append(0xf000|lookup[b])
  assert len(tiles)<=256,(i,len(tiles))
  out.extend(b'\xff'*((-len(out))%4));at=len(out);out.extend(b''.join(tiles).ljust(0x2000,b'\0'));struct.pack_into('<I',out,0xc3150+i*20+8,0x8000000+at)
  out[o['tilemap']:o['tilemap']+1280]=struct.pack('<640H',*maps);struct.pack_into('<H',out,o['palette']+2,0x0c1a);struct.pack_into('<H',out,o['palette']+4,0);struct.pack_into('<H',out,o['palette']+30,0x7fff)
  # Remove the separate Japanese animated emphasis glyph; the Korean emphasis
  # is part of the rebuilt card to keep word order readable in every frame.
  if o['obj_tiles']:out[o['obj_tiles']:o['obj_tiles']+0x800]=bytes(0x800)
  im.save(R/f'work/graphics/patched/chapter_{i:02}.png');reports.append({'chapter':i,'title':TITLES[i],'tile_count':len(tiles),'tile_offset':hex(at),'separate_japanese_emphasis_removed':bool(o['obj_tiles'])})
 bg=[o for o in json.loads((R/'work/graphics/backgrounds/index.json').read_text()) if 0xaf3994<=o['tiles']<=0xb25f14]
 boxes=[(5,3,26,42),(17,0,76,21),(160,6,220,26),(89,0,161,21),(11,0,35,55),(163,80,216,99),(117,81,139,133),(11,0,72,24),(34,75,92,97),(145,15,201,36)]
 for i,(o,box) in enumerate(zip(bg,boxes)):
  x,y,xx,yy=box;ops=[('fill',box,(0,0,0,254))]
  if i in (0,4,6):
   chars='서장' if i==0 else f'{i}화'
   for j,c in enumerate(chars):ops.append(('draw',c,x+1,y+j*13,11,(0,0,15,254)))
  else:ops.append(('draw','최종화' if i==9 else f'제{i}화',x+1,y+2,11,(0,0,15,254)))
  # Chapter 5 uses an opaque illustrated background rather than transparent green.
  patch_bg(r,out,o,ops)
 return reports
