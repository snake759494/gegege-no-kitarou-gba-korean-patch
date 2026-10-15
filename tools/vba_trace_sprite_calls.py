"""Install a RAM-only logger at the original sprite draw entry in an owned VBA."""
from pathlib import Path
import ctypes as c,struct,sys,json
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
k=c.WinDLL('kernel32');k.OpenProcess.restype=c.c_void_p
k.ReadProcessMemory.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.c_size_t,c.c_void_p];k.WriteProcessMemory.argtypes=k.ReadProcessMemory.argtypes;k.CloseHandle.argtypes=[c.c_void_p]
h=k.OpenProcess(0x1fffff,False,int(sys.argv[1]));nt=c.WinDLL('ntdll');nt.NtSuspendProcess.argtypes=[c.c_void_p];nt.NtResumeProcess.argtypes=[c.c_void_p]
def rd(a,n):
 b=c.create_string_buffer(n);z=c.c_size_t();k.ReadProcessMemory(h,a,b,n,c.byref(z));return b.raw[:z.value]
def wr(a,b):
 v=c.create_string_buffer(b);z=c.c_size_t();assert k.WriteProcessMemory(h,a,v,len(b),c.byref(z));assert z.value==len(b)
try:
 data=rd(0x400000,0x400000);hits=[i for i in range(0,len(data)-64,4) if struct.unpack_from('<I',data,i)[0]==0x3ffff and struct.unpack_from('<I',data,i+8)[0]==0x7fff and struct.unpack_from('<I',data,i+16)[0]==0x3ff];assert len(hits)==1
 hosts=[struct.unpack_from('<I',data,hits[0]-4+i*8)[0] for i in range(7)]
 at=0x09ffd000;log=0x0203f000
 asm=f'''push {{r0,r1,r2,r3,r4,r5,lr}}
ldr r1,[r0]
ldr r2,logs
movs r5,#128
loop: ldr r3,[r2]
cmp r3,r1
beq found
cmp r3,#0
beq insert
adds r2,#8
subs r5,#1
bne loop
b finish
insert: str r1,[r2]
found: ldr r3,[r2,#4]
adds r3,#1
str r3,[r2,#4]
finish: pop {{r0,r1,r2,r3,r4,r5}}
pop {{r3}}
mov lr,r3
push {{r4,r5,r6,r7,lr}}
mov r7,sl
mov r6,sb
mov r5,r8
ldr r3,resume
bx r3
.align 2
logs: .word {log}
resume: .word 0x080024d1
'''
 code=bytes(Ks(KS_ARCH_ARM,KS_MODE_THUMB).asm(asm,at)[0]);original=bytes.fromhex('f0b557464e464546')
 assert rd(hosts[6]+0x24c8,8)==original
 assert nt.NtSuspendProcess(h)==0
 try:
  wr(hosts[0]+0x3f000,bytes(1024));wr(hosts[6]+0x1ffd000,code)
  wr(hosts[6]+0x24c8,bytes.fromhex('004b1847')+struct.pack('<I',at|1))
 finally:nt.NtResumeProcess(h)
 print(json.dumps({'entry':'080024C8','log':'0203F000','capacity':128,'on_disk_modified':False,'pid':int(sys.argv[1])}))
finally:k.CloseHandle(h)
