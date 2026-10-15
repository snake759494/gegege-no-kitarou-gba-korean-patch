"""Native bitmap labels, original tile geometry and palettes, no font scaling."""
from pathlib import Path
from PIL import Image
import numpy as np,struct,json
from scipy.ndimage import distance_transform_edt
from build_patch import parse_bdf
from ui_brush_lettering import paint, paint_box, encyclopedia
R=Path(__file__).resolve().parent.parent
F={n:parse_bdf(R/f'work/fonts/galmuri/Galmuri{n}.bdf') for n in (9,11,14)}
def draw(im,text,x,y,size=9,color=(24,24,24,255),center=False):
 widths=[4 if c==' ' else F[size][ord(c)]['bbx'][0]+1 for c in text]
 if center:x-=sum(widths)//2
 for c,advance in zip(text,widths):
  if c!=' ':
   g=F[size][ord(c)];w,h,_,_=g['bbx']
   for yy,bits in enumerate(g['bitmap']):
    for xx in range(w):
     if bits>>(((w+7)//8)*8-1-xx)&1:
      assert 0<=x+xx<im.width and 0<=y+yy<im.height,(text,x,y,im.size)
      im.putpixel((x+xx,y+yy),color)
  x+=advance

def erase(im,box,style='dark'):
 a=np.array(im);x0,y0,x1,y1=box;roi=a[y0:y1,x0:x1];rgb=roi[:,:,:3].astype(int);gray=rgb.mean(2)
 if style=='dark':
  ink=(gray<205)&(roi[:,:,3]>0);valid=(gray>210)&(rgb.max(2)-rgb.min(2)<100)&(roi[:,:,3]>0)
 else:
  ink=(gray>110)&(rgb.min(2)>70)&(roi[:,:,3]>0);valid=(rgb[:,:,0]>rgb[:,:,1]*1.1)&(rgb[:,:,0]<170)&(rgb[:,:,1]>25)&(roi[:,:,3]>0)
 if valid.any():
  _,indices=distance_transform_edt(~valid,return_indices=True);roi[ink]=roi[indices[0][ink],indices[1][ink]]
 else:roi[ink]=[230,220,200,255] if style=='dark' else [100,56,32,255]
 return Image.fromarray(a)

def erase_text(im, box, threshold=165):
 # Repair only dark lettering inside its inset box; preserve colored frames.
 a=np.array(im);x0,y0,x1,y1=box;roi=a[y0:y1,x0:x1];gray=roi[:,:,:3].mean(2)
 ink=(gray<threshold)&(roi[:,:,3]>0)
 valid=(gray>threshold+15)&(roi[:,:,3]>0)
 assert valid.any(),box
 _,indices=distance_transform_edt(~valid,return_indices=True)
 roi[ink]=roi[indices[0][ink],indices[1][ink]]
 return Image.fromarray(a)


def palette(r,p,n=16):return [((v&31)*8,((v>>5)&31)*8,((v>>10)&31)*8,255) for v in struct.unpack_from('<'+str(n)+'H',r,p)]
def nearest(col,pal):return min(range(1,16),key=lambda i:sum((col[j]-pal[i][j])**2 for j in range(3)))
def patch_sprite(r,out,item,ops):
 path=R/'work/graphics/sprites'/f"{item['id']}.png";orig=Image.open(path).convert('RGBA');im=orig.copy()
 for op in ops:
  if op[0]=='erase':im=erase(im,*op[1:])
  elif op[0]=='erase_text':im=erase_text(im,*op[1:])
  elif op[0]=='brush':paint(im,*op[1:])
  elif op[0]=='brush_box':paint_box(im,*op[1:])
  elif op[0]=='clear':im.paste((0,0,0,0),op[1])
  else:draw(im,*op[1:])
 for o in item['objects']:
  pal=palette(r,o['palette']);ox=o['x']-item['origin'][0];oy=o['y']-item['origin'][1]
  for y in range(o['h']):
   for x in range(o['w']):
    col=im.getpixel((ox+x,oy+y))
    if col==orig.getpixel((ox+x,oy+y)):continue
    idx=0 if col[3]==0 else nearest(col,pal);off=o['tile']+(y//8*(o['w']//8)+x//8)*32+y%8*4+x%8//2;shift=x%2*4;out[off]=(out[off]&~(15<<shift))|(idx<<shift)
 im.save(R/'work/graphics/patched'/f"{item['id']}.png")

def patch_bg(r,out,item,ops):
 p=item['palette'];m=item['tilemap'];t=item['tiles'];banks=item.get('banks',m+item.get('height',160)*8);pal=palette(r,p,256);height=item.get('height',160);im=Image.new('RGBA',(256,height));indices=np.zeros((height,256),dtype='uint8');entries=[]
 for ty in range(height//8):
  for tx in range(32):
   en=struct.unpack_from('<H',r,m+(ty*32+tx)*2)[0];entries.append(en)
   for y in range(8):
    for x in range(8):
     xx=7-x if en&1024 else x;yy=7-y if en&2048 else y;b=r[t+(en&1023)*32+yy*4+xx//2];idx=b>>(4*(xx%2))&15;indices[ty*8+y,tx*8+x]=idx;im.putpixel((tx*8+x,ty*8+y),pal[r[banks+ty*32+tx]*16+idx])
 orig=im.copy()
 for op in ops:
  if op[0]=='erase':im=erase(im,*op[1:])
  elif op[0]=='erase_text':im=erase_text(im,*op[1:])
  elif op[0]=='brush':paint(im,*op[1:])
  elif op[0]=='brush_box':paint_box(im,*op[1:])
  elif op[0]=='encyclopedia':encyclopedia(im)
  elif op[0]=='fill':im.paste(op[2],op[1])
  elif op[0]=='paste':im.paste(op[1],op[2])
  else:draw(im,*op[1:])
 for ty in range(height//8):
  for tx in range(32):
   en=entries[ty*32+tx];bank=r[banks+ty*32+tx];tile=ty*32+tx;struct.pack_into('<H',out,m+tile*2,tile)
   for y in range(8):
    for x in range(0,8,2):
     vals=[]
     for xx in (x,x+1):
      pt=(tx*8+xx,ty*8+y);col=im.getpixel(pt);idx=col[2] if col[3]==254 else int(indices[pt[1],pt[0]]) if col==orig.getpixel(pt) else min(range(16),key=lambda i:sum((col[j]-pal[bank*16+i][j])**2 for j in range(3)));vals.append(idx)
     out[t+tile*32+y*4+x//2]=vals[0]|vals[1]<<4
 im.save(R/'work/graphics/patched'/f"{item['id']}.png")

def patch_ui(r,out):
 D=R/'work/graphics/patched';D.mkdir(exist_ok=True);idx={i['id']:i for i in json.loads((R/'work/graphics/sprites/index.json').read_text(encoding='utf-8'))};changes=[]
 def sprite(id,ops):patch_sprite(r,out,idx[id],ops);changes.append(id)
 dark=(32,24,24,255);white=(248,240,232,255)
 for j,s in enumerate(['특수 능력','동료 요괴']):sprite(f'820eb4_{j:03}',[('erase_text',(4,9,65,21),135),('draw',s,35,10,9,dark,True)])
 sprite('82a73c_009',[('erase_text',(20,11,171,27),185),('draw','요괴열도 지도',94,13,14,(112,88,64,255),True)])
 for j,s in enumerate(['독','마비','졸음','정상']):
  id=f'82e448_{j+48:03}';w=Image.open(R/'work/graphics/sprites'/f'{id}.png').width;box=(0,0,w-16 if j<3 else w,16)
  sprite(id,[('clear',box)]+[('draw',s,1+dx,3+dy,9,white) for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]]+[('draw',s,1,3,9,dark)])
 for j,s in enumerate(['집 나가기','저장','아이템 구입','아이템 판매','상태','요괴 도감','키타로의 집']):
  sprite(f'831510_{j:03}',[('erase_text',(6,7,95,17) if j<6 else (10,9,101,22),170),('draw',s,50 if j<6 else 56,7 if j<6 else 10,11 if j==6 else 9,dark,True)])
 for j,s in enumerate(['아이템 구입','아이템 판매']):sprite(f'831bf4_{j:03}',[('erase',(8,2,91,13),'light'),('draw',s,48,3,9,white,True)])
 for j,lines in [(3,['이야기 모드','???????']),(4,['이야기 모드','도전 모드'])]:
  sprite(f'8364d4_{j:03}',[('erase',(17,14,120,48))]+[('draw',s,64,20+i*16,9,dark,True) for i,s in enumerate(lines)])
 for j in (2,4):sprite(f'839224_{j:03}',[('erase',(17,14,118,48))]+[('draw',s,64,17+i*11,9,dark,True) for i,s in enumerate(['저장한 곳부터','집으로 돌아가기','게임 종료'])])
 sprite('8965d8_001',[('clear',(0,0,32,32))]+[('draw',s,16+dx,y+dy,9,dark,True) for s,y in [('레벨',5),('상승',17)] for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]]+[('draw','레벨',16,5,9,white,True),('draw','상승',16,17,9,white,True)])
 for j,s in enumerate('게임종료!'):sprite(f'858fc0_{j:03}',[('clear',(0,0,32,32)),('draw',s,16,8,14,(248,160,0,255),True)])
 bg={i['id']:i for i in json.loads((R/'work/graphics/backgrounds/index.json').read_text())}
 for id in ['be4214','be9b94','bef514']:
  ops=[('erase',(7,20,42,34)),('brush','상태',8,23,12,dark),('erase',(7,36,39,117))]
  for y,text in [(38,'체'),(54,'기'),(70,'공'),(86,'운'),(102,'돈')]:ops.append(('brush',text,9,y,12,dark))
  ops.extend([('erase',(61,68,80,83)),('brush','방',62,70,12,dark)])
  if id=='be4214':ops.extend([('erase',(7,118,63,150)),('brush','경험치',8,120,11,dark),('brush','다음',8,136,11,dark)])
  if id=='be4214':
   ops.extend([('erase',(16,2,117,16),'light'),
    ('brush_box','상태',(36,6,72,13),9,white),
    ('brush_box','키타로',(78,1,114,14),12,(248,216,88,255)),
    ('erase',(188,2,229,15),'light'),('brush_box','사용',(195,4,216,11),9,white),
    ('erase',(110,17,161,32),'light'),('brush_box','동료',(126,18,154,29),11,white),
    ('erase',(178,17,229,32),'light'),('brush_box','장비',(196,18,215,29),11,white)])
  else:
   ops.extend([('erase',(17,2,153,16),'light'),
    ('brush_box','상태' if id=='be9b94' else '사용',(19,4,49,11) if id=='be9b94' else (23,4,44,11),9,white),
    ('brush_box','아이템 사용' if id=='be9b94' else '아이템 장비',(65,2,123,14) if id=='be9b94' else (65,2,126,14),12,white)])
   if id=='be9b94':ops.extend([('erase',(193,2,230,16),'light'),('brush_box','장비',(195,4,217,11),9,white)])
  patch_bg(r,out,bg[id],ops);changes.append(id)
 patch_bg(r,out,bg['bf4e94'],[('fill',(105,2,232,15),(16,8,32,255)),('draw','수량',108,3,9,white),('draw','소지금',156,3,9,white)]);changes.append('bf4e94')
 patch_bg(r,out,bg['bfa814'],[('encyclopedia',)]);changes.append('bfa814')
 return {'hand_painted_backgrounds':['be4214','be9b94','bef514','bfa814'],'native_font_labels':changes,'count':len(changes),'fonts':['Galmuri9','Galmuri11','Galmuri14'],'font_scaling':False}
