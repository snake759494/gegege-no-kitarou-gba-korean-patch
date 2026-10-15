"""Deterministic native-pixel Korean title tiles, preserving original OBJ layout."""
from pathlib import Path
import json,struct
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
BASE=0x84A410

def make_title(rom):
 sprites=json.loads((ROOT/'tools/title_layout.json').read_text())
 layers=[{} for _ in range(3)]
 for s in sprites:
  for y in range(s['h']):
   for x in range(s['w']):
    ti=s['tile']+(y//8)*(s['w']//8)+x//8
    off=BASE+ti*32+(y%8)*4+(x%8)//2
    col=(rom[off]>>(4*(x%2)))&15
    layers[s['bank']][s['x']+x,s['y']+y]=col
 original=[a.copy() for a in layers]
 # Lettering orange/yellow palette entries are distinct from the scroll greens.
 # Restore just those pixels with adjacent original dark scroll texture.
 board=layers[0]
 bgcolors={1,2,4,5,11}
 for (x,y),col in list(board.items()):
  if 25<=x<=217 and 39<=y<=84 and col in {3,6,7,8,9,10,12,13,14,15}:
   neighbors=[]
   for dy in range(-8,9):
    for dx in range(-8,9):
     val=original[0].get((x+dx,y+dy),0)
     if val in bgcolors:neighbors.append((dx*dx+dy*dy,dy,dx,val))
   board[x,y]=min(neighbors)[3] if neighbors else 2
 # Replace the upper red text, preserving its original pair of 64x32 objects.
 layers[2]={p:0 for p in layers[2]}
 # Painted lettering is converted to native tiles; no font is used here.
 art=Image.open(ROOT/'assets/title_letters.png').convert('RGBA')
 for bank,paloff,yrange in [(2,0x84E230,range(0,42)),(0,0x84E210,range(42,90))]:
  palette=[((c&31)*255//31,((c>>5)&31)*255//31,((c>>10)&31)*255//31) for c in struct.unpack('<16H',rom[paloff:paloff+32])]
  for y in yrange:
   for x in range(240):
    rr,gg,bb,aa=art.getpixel((x,y))
    if aa:
     if (x,y) not in layers[bank]:raise ValueError(f'Painted pixel outside original OBJ: {x},{y}')
     col=min(range(1,16),key=lambda i:sum((a-b)**2 for a,b in zip(palette[i],(rr,gg,bb))))
     layers[bank][x,y]=col
     if bank==0:
      # The original foreground ornament crosses the subtitle in four places.
      # Clear only its overlap with new lettering so '열도' is not cut through.
      for dx,dy in [(0,0),(-1,0),(1,0),(0,-1),(0,1)]:
       if (x+dx,y+dy) in layers[1]:layers[1][x+dx,y+dy]=0
 out=bytearray(rom)
 for s in sprites:
  for y in range(s['h']):
   for x in range(s['w']):
    ti=s['tile']+(y//8)*(s['w']//8)+x//8;off=BASE+ti*32+(y%8)*4+(x%8)//2;shift=4*(x%2)
    col=layers[s['bank']][s['x']+x,s['y']+y]
    out[off]=(out[off]&~(15<<shift))|(col<<shift)
 # Diagnostic images use the actual original palette and OBJ coordinates.
 palblob=bytes(512)+rom[0x84E210:0x84E230]+rom[0x84E1F0:0x84E210]+rom[0x84E230:0x84E250]+bytes(416)
 palette=[((c&31)*255//31,((c>>5)&31)*255//31,((c>>10)&31)*255//31) for c in struct.unpack('<512H',palblob)]
 for label,ls in [('original',original),('korean',layers)]:
  im=Image.new('RGBA',(240,140))
  for bank in [0,1,2]:
   for (x,y),col in ls[bank].items():
    if col and x<240 and y<140:im.putpixel((x,y),palette[256+bank*16+col]+(255,))
  im.save(ROOT/f'work/title/title_{label}.png')
 return out,{'tile_rom_offset':hex(BASE),'changed_bytes':sum(a!=b for a,b in zip(out,rom)),'title':'게게게의 키타로','subtitle':'위기일발! 요괴열도','lettering':'custom painted Korean brush lettering; no typeset font; original OBJ and palettes preserved'}
if __name__=='__main__':
 r=next(ROOT.glob('*Japan*.gba')).read_bytes();out,report=make_title(r);print(json.dumps(report,ensure_ascii=False,indent=2))
