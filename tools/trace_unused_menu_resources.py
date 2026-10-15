"""Trace the two legacy menu assets using ROM references and original Thumb code."""
from pathlib import Path
import json,struct,hashlib
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn.arm_const import *
R=Path(__file__).resolve().parent.parent;D=R/'work/resource_trace';D.mkdir(exist_ok=True)
rom=next(R.glob('*Japan).gba')).read_bytes();base=0x08000000
u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
for a,n in [(base,0x2000000),(0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000)]:u.mem_map(a,n)
u.mem_write(base,rom)
actor=0x02001000;obj=0x02010000;task=0x03006000;ret=0x03007000
state={};reads=[];draws=[];transitions=[];freed=[]
def rr(n):return u.reg_read([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3][n])
def result(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
def hook(emu,a,size,data):
 if a==0x080017c4:result(state.get('counter',31))
 elif a==0x0800184c:result(task)
 elif a==0x08038038:result(state.get('save',0))
 elif a==0x08001284:result(state.get('fade',0))
 elif a==0x080024c8:draws.append(rr(0));result()
 elif a==0x08001784:transitions.append(rr(0));result()
 elif a==0x080014d0:freed.append(rr(0));result()
 elif a==0x08038d88:result(rr(0)%rr(1))
 elif a==0x08038cf0:result(rr(0)//rr(1))
 elif a in [0x08002cf8,0x08005d7c,0x08037aa0,0x08001208]:result()
def readhook(emu,access,a,size,value,data):
 if 0x080bb838<=a<0x080bb9b0:reads.append(a)
u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_READ,readhook)
def call(a,arg=0):
 for reg in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7]:u.reg_write(reg,0)
 u.reg_write(UC_ARM_REG_R0,arg);u.reg_write(UC_ARM_REG_SP,0x03007f00);u.reg_write(UC_ARM_REG_LR,ret|1)
 u.emu_start(a|1,ret,count=10000);assert u.reg_read(UC_ARM_REG_PC)==ret,hex(a)
def ptrrefs(v):
 needle=struct.pack('<I',v);out=[];pos=0
 while (at:=rom.find(needle,pos))>=0:out.append(f'0x{at:06X}');pos=at+1
 return out
# The sole dynamic terrain-object lookup overwrites the incoming index flags.
u.mem_write(0x020072bc,struct.pack('<h',32));u.mem_write(0x020072c2,struct.pack('<h',32))
cases=[(ident,flag) for ident in range(256) for flag in [0,1,255]]+[(ident,flag) for ident in [0,21] for flag in range(256)]
terrain=set()
for ident,flag in cases:
 u.mem_write(actor,bytes(0x80));u.mem_write(actor,struct.pack('<I',ident<<1));u.mem_write(actor+3,bytes([flag]));reads.clear()
 call(0x08006364,actor)
 terrain.update((a-0x080bb838)//4 for a in reads)
assert terrain=={0,17},terrain
status=[rom[0x0c2104+i*8+3] for i in range(14)];assert 22 not in status and 32 not in status
# Title handler accepts only A/START, draws only the first (PRESS START) object.
titlecases=0;rendered=set();nexttasks=set()
def titlecase(handler,counter,save,keys,fade=0):
 global titlecases
 u.mem_write(obj,bytes(0x4c));u.mem_write(obj,struct.pack('<I',0x08832e28));u.mem_write(obj+0x18,struct.pack('<I',0x088364d4));u.mem_write(obj+0x30,struct.pack('<I',0x08832e28));u.mem_write(obj+0x4a,b'\xff\xff')
 u.mem_write(task+4,struct.pack('<I',obj));u.mem_write(0x0300094a,struct.pack('<H',keys));state.update(counter=counter,save=save,fade=fade);draws.clear();transitions.clear();freed.clear()
 call(handler);rendered.update(draws);nexttasks.update(transitions)
 assert all(a==obj for a in draws),draws
 assert obj+0x18 not in draws and obj+0x30 not in draws
 if handler==0x0802ed74 and fade==0:assert freed==[obj]
 titlecases+=1
for save in [-1,0,1,2]:
 for keys in range(1024):titlecase(0x0802ecfc,31,save,keys)
 for counter in [0,1,30,31,94,95,158,159]:
  for keys in [0,1,8,9,0x3ff]:titlecase(0x0802ecfc,counter,save,keys)
 for fade in [0,1]:
  for keys in [0,1,8,9,0x3ff]:titlecase(0x0802ed74,31,save,keys,fade)
assert nexttasks=={0x0802ed75,0x080324a1,0x0802f8b5},nexttasks
report={'original_sha256':hashlib.sha256(rom).hexdigest(),'classification':{'820EB4':'Unused fixed ability/companion plaques in the shipped game','8364D4':'Legacy title popup: initialized child object, never submitted to renderer by reachable title handlers'},'footer_references':{hex(v):ptrrefs(v) for v in [0x08820eb4,0x088364d4]},'terrain_dynamic_lookup':{'function':'08006364','executed_cases':len(cases),'resource_indices':sorted(terrain),'index_22_reached':False},'status_sprite_indices':status,'title_handlers':{'functions':['0802ECFC','0802ED74'],'executed_cases':titlecases,'button_masks_exhausted':1024,'save_query_results':[-1,0,1,2],'only_rendered_object_offset':0,'undrawn_child_offsets':[24,48],'next_callbacks':[hex(a) for a in sorted(nexttasks)],'frees_entire_ui_after_transition':True},'normal_menu_routes':'Actual ability/companion controls use status/radial sprites; actual normal/EX selection uses record menu resource 842888, not either legacy asset.','scope':'Original shipped BGKJ control paths, valid game state and original ROM code; arbitrary memory corruption, cheats that redirect code, and diagnostic renderer invocation are excluded.'}
(D/'cpu_route_proof.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
