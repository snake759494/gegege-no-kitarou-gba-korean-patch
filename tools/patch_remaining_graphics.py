from pathlib import Path
from PIL import Image
import json,numpy as np,struct
from patch_ui_graphics import patch_bg
R=Path(__file__).resolve().parent.parent

def patch_remaining(r,out):
 bg={o['id']:o for o in json.loads((R/'work/graphics/backgrounds/index.json').read_text())};im=Image.open(R/'assets/scenery_lettering_regions.png').convert('RGB')
 ids=['9e1194','a12994','a20194','a2d994','a3f994','a63994','a87994','a8c194'];rects=[[(40,3,174,53),(56,53,88,116)],[(35,0,90,126)],[(91,0,205,120)],[(54,4,103,112)],[(16,2,85,125)],[(91,75,139,104)],[(169,0,209,75)],[(78,15,194,55)]]
 for j,id in enumerate(ids):
  scene=im.crop((j%4*256,j//4*128,j%4*256+256,j//4*128+128)).convert('RGBA');ops=[('paste',scene.crop(box),(box[0],box[1])) for box in rects[j]];patch_bg(r,out,bg[id],ops)
 # A third title copy is stored in the generic BG bank. Rebuild it as a
 # self-contained 16-color picture, preserving placement and copyright.
 o=bg['c05b14'];art=Image.open(R/'work/title/title_static_korean.png').convert('RGB');full=Image.new('RGB',(256,160));full.paste(art,(0,0));q=full.quantize(colors=16,dither=Image.Dither.NONE);pp=q.getpalette()[:48];gpal=[(pp[i]//8)|((pp[i+1]//8)<<5)|((pp[i+2]//8)<<10) for i in range(0,48,3)];blob=bytearray()
 for ty in range(20):
  for tx in range(32):
   data=q.crop((tx*8,ty*8,tx*8+8,ty*8+8)).tobytes();blob.extend(bytes(data[i]|data[i+1]<<4 for i in range(0,64,2)))
 out[o['tiles']:o['tiles']+len(blob)]=blob;out[o['palette']:o['palette']+512]=struct.pack('<256H',*(gpal*16));out[o['tilemap']:o['tilemap']+1280]=struct.pack('<640H',*range(640));out[o['tilemap']+1280:o['tilemap']+1920]=bytes(640);full.save(R/'work/graphics/patched/c05b14.png')
 return {'scenery_sound_effects':ids,'additional_title_copy':'c05b14','source_art':'assets/scenery_lettering_regions.png','outside_letter_regions_preserved':True}
