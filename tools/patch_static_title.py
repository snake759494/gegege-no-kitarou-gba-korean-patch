"""Patch separate 8bpp title background; retain original palette and copyright."""
from PIL import Image
from pathlib import Path
import struct
R=Path(__file__).resolve().parent.parent

def patch_static_title(source,out):
 palette=[((c&31)*8,((c>>5)&31)*8,((c>>10)&31)*8) for c in struct.unpack('<256H',source[0xB2920:0xB2B20])]
 entries=struct.unpack('<1024H',source[0xB82A0:0xB8AA0])
 im=Image.new('RGB',(256,256))
 for ty in range(32):
  for tx in range(32):
   t=entries[ty*32+tx]
   for y in range(8):
    for x in range(8):
     xx=7-x if t&1024 else x;yy=7-y if t&2048 else y
     idx=source[0xB2B20+(t&1023)*64+yy*8+xx];im.putpixel((tx*8+x,ty*8+y),palette[idx])
 # Match the original stationary logo's smaller placement, using the repaired
 # original ornament and painted Korean lettering, not a typeset font.
 art=Image.open(R/'work/title/title_korean.png').convert('RGBA').resize((216,126),Image.Resampling.NEAREST)
 im.paste((0,0,0),(0,0,240,120));im.paste(art,(12,-7),art)
 pal_im=Image.new('P',(1,1));pal_im.putpalette([c for color in palette for c in color])
 indexed=im.quantize(palette=pal_im,dither=Image.Dither.NONE)
 tiles=[bytes(64)];lookup={bytes(64):0};tilemap=[]
 for ty in range(32):
  for tx in range(32):
   b=indexed.crop((tx*8,ty*8,tx*8+8,ty*8+8)).tobytes()
   if b not in lookup:lookup[b]=len(tiles);tiles.append(b)
   tilemap.append(lookup[b])
 if len(tiles)%2:tiles.append(bytes(64))
 assert len(tiles)<=510
 out.extend(b'\xff'*((-len(out))%4));at=len(out);out.extend(b''.join(tiles))
 assert source[0x2EC3C:0x2EC40]==bytes.fromhex('af 22 d2 01')
 struct.pack_into('<H',out,0x2EC3C,0x2200+len(tiles)//2)
 struct.pack_into('<I',out,0x2ECDC,0x8000000+at)
 out[0xB82A0:0xB8AA0]=struct.pack('<1024H',*tilemap)
 indexed.convert('RGB').crop((0,0,240,160)).save(R/'work/title/title_static_korean.png')
 return {'original_tile_offset':'0xB2B20','tilemap_offset':'0xB82A0','new_tile_offset':hex(at),'tiles':len(tiles),'palette_preserved':True}
