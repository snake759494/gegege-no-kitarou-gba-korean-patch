from pathlib import Path
import json,struct,hashlib
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB
from unicorn.arm_const import *
R=Path('.');rom=next(R.glob('*Korean*.gba'));data=rom.read_bytes();report=json.loads((R/'work/build/build_report.json').read_text());codes={}
for line in (R/'work/build/custom_glyph_map.tsv').read_text(encoding='utf-8').splitlines()[1:]:
 c,code,_=line.split('\t');codes[c]=int(code,16)
cases=[]
for off in report['halfwidth_space']['helper_offsets']:
 second=off==report['halfwidth_space']['helper_offsets'][1]
 for text in ['가 나','가  나','가나다',' 가']:
  for n in range(len(text)+1):
   u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.mem_map(0x8000000,0x2000000);u.mem_write(0x8000000,data);u.mem_map(0x2000000,0x10000)
   ptr=0x2001000;sp=0x2008000;end=0x2000200
   u.mem_write(ptr,b''.join(codes[c].to_bytes(2,'big') for c in text));u.mem_write(sp+(4 if second else 0),struct.pack('<I',ptr))
   u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,end|1);u.reg_write(UC_ARM_REG_R5,n);u.reg_write(UC_ARM_REG_R6,n if second else 12);u.reg_write(UC_ARM_REG_R7,12)
   u.emu_start(0x8000000+int(off,16)|1,end,count=1000);actual=u.reg_read(UC_ARM_REG_R0);expected=sum(6 if c==' ' else 12 for c in text[:n]);assert actual==expected,(off,text,n,actual,expected)
   cases.append(dict(helper=off,text=text,index=n,pixels=actual))
(R/'work/build/halfspace_validation.json').write_text(json.dumps(dict(rom_sha256=hashlib.sha256(data).hexdigest(),passed=len(cases),cases=cases),ensure_ascii=False,indent=2),encoding='utf-8');print('passed',len(cases))
