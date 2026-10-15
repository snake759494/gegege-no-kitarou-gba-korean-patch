"""Repack the three original 64x64 menu sprites with native bitmap glyphs."""
from pathlib import Path
from build_patch import parse_bdf
R=Path(__file__).resolve().parent.parent

def patch_menu_graphics(source,out):
 bdf=parse_bdf(R/'work/fonts/galmuri/Galmuri9.bdf')
 changes=[]
 for base,lines in [(0x840A98,['새 게임','일반 모드',None]),(0x841298,['새 게임','일반 모드','EX 모드']),(0x841A98,['이어 하기','기록 삭제','기록 복사'])]:
  a=[[0]*64 for _ in range(64)]
  for y in range(64):
   for x in range(64):
    off=base+(y//8*8+x//8)*32+y%8*4+x%8//2;a[y][x]=(source[off]>>(4*(x%2)))&15
  old=[r[:] for r in a]
  for row,text in enumerate(lines):
   if text is None:continue
   top=3+16*row
   for y in range(top,top+12):
    for x in range(4,61):
     if old[y][x] in (1,2,3,4,5,6,7):
      candidates=[(dx*dx+dy*dy,old[yy][xx]) for dy in range(-5,6) for dx in range(-5,6) if 3<=(xx:=x+dx)<61 and 2<=(yy:=y+dy)<49 and old[yy][xx]>=10]
      a[y][x]=min(candidates)[1] if candidates else 15
   widths=[4 if c==' ' else bdf[ord(c)]['bbx'][0]+1 for c in text];left=(64-sum(widths)+1)//2
   for c,advance in zip(text,widths):
    if c!=' ':
     g=bdf[ord(c)];w,h,_,_=g['bbx']
     for y,bits in enumerate(g['bitmap']):
      for x in range(w):
       if bits>>(((w+7)//8)*8-1-x)&1:a[top+2+y][left+x]=3
    left+=advance
  for y in range(64):
   for x in range(64):
    off=base+(y//8*8+x//8)*32+y%8*4+x%8//2;shift=4*(x%2);out[off]=(out[off]&~(15<<shift))|(a[y][x]<<shift)
  changes.append({'offset':hex(base),'labels':lines})
 return changes
