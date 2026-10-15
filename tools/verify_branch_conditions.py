from pathlib import Path
import struct,json,hashlib
from unicorn import *
from unicorn.arm_const import *
R=Path('.');rom=next(R.glob('*Korean*.gba')).read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
for a,n in [(0x8000000,0x2000000),(0x2000000,0x40000),(0x3000000,0x8000)]:u.mem_map(a,n)
u.mem_write(0x8000000,rom);vm=0x20178f4;game=0x3004a60;player=0x2020000;results=[]
def reset():
 u.mem_write(0x2000000,bytes(0x40000));u.mem_write(0x3000000,bytes(0x8000));u.mem_write(0x3005f28,struct.pack('<I',player))
def call(at,arg=0):
 u.reg_write(UC_ARM_REG_SP,0x3007000);u.reg_write(UC_ARM_REG_LR,0x3000101);u.reg_write(UC_ARM_REG_R0,arg);u.emu_start(at|1,0x3000100,count=100000);assert u.reg_read(UC_ARM_REG_PC)==0x3000100;return u.reg_read(UC_ARM_REG_R0)
def byte(a,v):u.mem_write(a,bytes([v]))
for p in range(0xbf86c,0xbf89c,8):
 ident,ch,stage,x0,x1=rom[p:p+5]
 if not ident:break
 for variant in ['inside','left_boundary','right_boundary','outside_left','outside_right','wrong_chapter','wrong_stage','seen','too_high']:
  reset();byte(game+0x6b,ch if variant!='wrong_chapter' else ch+1);byte(game+0x6c,stage if variant!='wrong_stage' else stage+1)
  x={'left_boundary':x0,'right_boundary':x1,'outside_left':x0-1,'outside_right':x1+1}.get(variant,(x0+x1)//2);u.mem_write(player+0x24,struct.pack('<i',x<<11));u.mem_write(player+0x28,struct.pack('<i',0xd001 if variant=='too_high' else 0xd000))
  if variant=='seen':byte(game+0x27+ident//8,1<<(ident%8))
  expected=ident if variant in ['inside','left_boundary','right_boundary'] else 0;actual=call(0x800f4cc);assert actual==expected,(ident,variant,actual,expected);results.append({'kind':'position','script':ident,'condition':variant,'result':actual})
p=0xbf89c;eventrows=[]
while rom[p]:eventrows.append(tuple(rom[p:p+4]));p+=4
for ident,ch,stage,event in eventrows:
 for variant in ['eligible','seen','wrong_chapter','wrong_stage','wrong_event','already_queued']:
  reset();byte(game+0x6b,ch if variant!='wrong_chapter' else ch+1);byte(game+0x6c,stage if variant!='wrong_stage' else stage+1)
  if variant=='seen':byte(game+0x27+ident//8,1<<(ident%8))
  if variant=='already_queued':byte(vm+0x1a,99)
  call(0x800f57c,event if variant!='wrong_event' else 255);actual=u.mem_read(vm+0x1a,1)[0];expected=ident if variant=='eligible' else 99 if variant=='already_queued' else 0;assert actual==expected,(ident,variant,actual,expected);results.append({'kind':'event','script':ident,'condition':variant,'queued':actual})
  if variant=='eligible':
   u.mem_write(vm+0x18,b'\x01\0');actual=call(0x800f4cc);assert actual==ident;assert u.mem_read(vm+0x1a,1)==b'\0'
report={'rom_sha256':hashlib.sha256(rom).hexdigest(),'position_events':5,'trigger_events':len(eventrows),'passed':len(results),'cases':results};(R/'work/build/branch_condition_validation.json').write_text(json.dumps(report,indent=2));print('passed',len(results),'event rows',len(eventrows))
