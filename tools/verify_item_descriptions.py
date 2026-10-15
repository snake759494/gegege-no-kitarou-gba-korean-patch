from pathlib import Path
import struct,json,csv,hashlib
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
r=Path('.');rom=next(r.glob('*Korean).gba')).read_bytes();ctx=0x2006308;stop=0x3000100
snapshot=(r/'work/shop_ui_runtime/shop_00/ewram.bin').read_bytes()
rows=list(csv.DictReader((r/'translation/ko_item_descriptions.tsv').open(encoding='utf-8'),delimiter='\t'));results=[]
def hook(u,a,size,data):
 if a==0x8000924:u.mem_write(u.reg_read(UC_ARM_REG_R0),bytes(u.reg_read(UC_ARM_REG_R1)));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 elif a in (0x8000840,0x8038ae8):
  src=u.reg_read(UC_ARM_REG_R0);dst=u.reg_read(UC_ARM_REG_R1);n=u.reg_read(UC_ARM_REG_R2)*(4 if a==0x8038ae8 else 1)
  u.mem_write(dst,bytes(u.mem_read(src,n)));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
for row in rows:
 ref=int(row['pointer_ref'],16);ptr=struct.unpack_from('<I',rom,ref)[0];text=row['korean'];u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
 for a,n in [(0x8000000,0x2000000),(0x2000000,0x40000),(0x3000000,0x8000),(0x4000000,0x1000),(0x5000000,0x1000),(0x6000000,0x20000)]:u.mem_map(a,n)
 u.mem_write(0x8000000,rom);u.mem_write(0x2000000,snapshot);u.hook_add(UC_HOOK_CODE,hook)
 u.mem_write(ctx,struct.pack('<I',0x6000000));u.mem_write(ctx+8,struct.pack('<I',0x600f800))
 for reg,val in [(UC_ARM_REG_R0,4),(UC_ARM_REG_R1,16),(UC_ARM_REG_R2,ptr),(UC_ARM_REG_R3,0xa8),(UC_ARM_REG_SP,0x3007000),(UC_ARM_REG_LR,stop|1)]:u.reg_write(reg,val)
 u.emu_start(0x800421d,stop,count=2000000);assert u.reg_read(UC_ARM_REG_PC)==stop
 allocation=int.from_bytes(u.mem_read(ctx+0xf94,2),'little') if text else 0
 assert allocation<=48,(hex(ref),text,allocation)
 results.append({'ref':hex(ref),'text':text,'characters':len(text),'pixels':sum(6 if c==' ' else 12 for c in text),'tiles':allocation})
(r/'work/build/item_description_validation.json').write_text(json.dumps({'rom_sha256':hashlib.sha256(rom).hexdigest(),'rows':len(results),'max_tiles':max(x['tiles'] for x in results),'row_capacity_tiles':48,'passed':True,'cases':results},ensure_ascii=False,indent=2),encoding='utf-8');print('passed',len(results),'max tiles',max(x['tiles'] for x in results))
