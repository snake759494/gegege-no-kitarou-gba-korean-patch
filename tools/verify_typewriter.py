from pathlib import Path
import struct,json
from unicorn import *
from unicorn.arm_const import *
R=Path('.');r=next(R.glob('*Korean*.gba')).read_bytes();codes={}
for row in (R/'work/build/custom_glyph_map.tsv').read_text(encoding='utf-8').splitlines()[1:]:
 ch,code,_=row.split('\t');codes[ch]=int(code,16)
ctx=0x2006308;source=0x2020000;stop=0x3000100;captures=[]
def hook(u,address,size,data):
 if address==0x8000924:
  u.mem_write(u.reg_read(UC_ARM_REG_R0),bytes(u.reg_read(UC_ARM_REG_R1)));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 if address==0x8001468:u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 if address==0x80038d4:
  n=int.from_bytes(u.mem_read(ctx+0xfa4,2),'little');size=((n*12+7)//8)*2
  for off in [0xf94,0xf96]:
   v=int.from_bytes(u.mem_read(ctx+off,2),'little');u.mem_write(ctx+off,struct.pack('<H',v+size))
  captures.append(bytes(u.mem_read(ctx+12,0x780)));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
results=[]
for text in ['가 나다라마','가나 다라마','가나다 라마','가  나 다','어머니에게도 요괴와 인간은']:
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
 for a,n in [(0x8000000,0x2000000),(0x2000000,0x40000),(0x3000000,0x8000)]:u.mem_map(a,n)
 u.mem_write(0x8000000,r);u.hook_add(UC_HOOK_CODE,hook)
 u.hook_add(UC_HOOK_MEM_INVALID,lambda u,a,addr,size,value,data: print(hex(u.reg_read(UC_ARM_REG_PC)),hex(addr),size,value) or False)
 u.mem_write(source,b''.join(codes[ch].to_bytes(2,'big') for ch in text)+b'\0\0');u.mem_write(ctx+0xf98,struct.pack('<I',source));u.mem_write(ctx+0xfa2,b'\x01\0');u.mem_write(ctx+0xfa6,b'\x01')
 def run(addr):
  u.reg_write(UC_ARM_REG_SP,0x3007000);u.reg_write(UC_ARM_REG_LR,stop|1);u.emu_start(addr|1,stop,count=1000000);assert u.reg_read(UC_ARM_REG_PC)==stop
 for i in range(len(text)):
  u.mem_write(ctx+0xfa8,b'\0');run(0x800431c);assert u.mem_read(ctx+0xfa7,1)[0]==(i+1)*2
  alloc=((i+1)*12+7)//8*2;assert int.from_bytes(u.mem_read(ctx+0xf94,2),'little')==alloc
  assert int.from_bytes(u.mem_read(ctx+0xfa2,2),'little')==1
  actual=captures[-1];endpos=source+(i+1)*2;saved=bytes(u.mem_read(endpos,2));u.mem_write(endpos,b'\0\0');u.reg_write(UC_ARM_REG_R0,source);run(0x8003d44);assert bytes(u.mem_read(ctx+12,0x780))==actual;u.mem_write(endpos,saved)
 final=captures[-1];u.reg_write(UC_ARM_REG_R0,source);run(0x8003d44);assert bytes(u.mem_read(ctx+12,0x780))==final
 results.append({'text':text,'characters':len(text),'matches_full_line_render':True,'allocation_correct':True})
import hashlib
report={'rom_sha256':hashlib.sha256(r).hexdigest(),'passed':sum(x['characters'] for x in results),'cases':results}
(R/'work/build/typewriter_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report)
