"""Reconstruct private build inputs from the user's verified original ROM."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
from PIL import Image

R=Path(__file__).resolve().parents[1]
def main():
 rom=(R/'Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Japan).gba').read_bytes()
 assert hashlib.sha256(rom).hexdigest()=='7c6c4806b637e6326cfc7e242a38fc3d3dcc53abaab9be96b8388f04bf1976cc'
 def restore(x):
  if isinstance(x,dict):
   if '$rom_cp932' in x:
    p,n=x['$rom_cp932'];return rom[p:p+n].decode('cp932')
   return {k:restore(v) for k,v in x.items()}
  if isinstance(x,list):return [restore(v) for v in x]
  return x
 for d in ['work/source','work/build','work/title','work/graphics/patched','work/fonts/galmuri']:(R/d).mkdir(parents=True,exist_ok=True)
 for n in ['script_lines','script_unique','script_blocks','extra_menu','paragraph_groups']:
  data=restore(json.loads((R/f'data/{n}.json').read_text(encoding='utf-8')))
  if n=='paragraph_groups':
   for g in data:g['source']=''.join(e['japanese'] for e in g['entries'])
  (R/f'work/source/{n}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 for tool in ['audit_backgrounds','audit_sprites']:
  subprocess.run([sys.executable,'-X','utf8',str(R/f'tools/{tool}.py')],cwd=R,check=True)
 rows=json.loads((R/'data/chapters.json').read_text(encoding='utf-8'))
 (R/'work/graphics/chapters.json').write_text(json.dumps(rows),encoding='utf-8')
 for i,o in enumerate(rows):
  im=Image.new('RGBA',(240,160))
  for y in range(160):
   for x in range(240):
    e=struct.unpack_from('<H',rom,o['tilemap']+(y//8*32+x//8)*2)[0]
    xx=7-x%8 if e&1024 else x%8;yy=7-y%8 if e&2048 else y%8
    c=(rom[o['tiles']+(e&1023)*32+yy*4+xx//2]>>(4*(xx%2)))&15
    if c:im.putpixel((x,y),(248,248,248,255))
  im.save(R/f'work/graphics/chapter_{i:02}.png')
 print('Private inputs reconstructed. Place the three matching BDF fonts in work/fonts/galmuri before building.')
if __name__=='__main__':main()
