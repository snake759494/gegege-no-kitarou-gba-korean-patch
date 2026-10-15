"""Half-width Korean space in both original Thumb text renderers."""
import struct
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
K=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
def asm(s,at):return bytes(K.asm(s,at)[0])
def patch_halfspace(source,out,codes):
 # The old font table is no longer referenced after all six literals move.
 at=0x355DE8;space=codes[' '];little=((space&255)<<8)|(space>>8)
 def helper(at,second):
  save='{r1,r3,r4,r5,r6,r7,lr}' if second else '{r1,r2,r3,r4,r5,r6,r7,lr}'
  restore='{r1,r3,r4,r5,r6,r7,pc}' if second else '{r1,r2,r3,r4,r5,r6,r7,pc}'
  setup='ldr r1,[sp,#32]; mov r3,r6; movs r6,#12' if second else 'ldr r1,[sp,#32]; mov r3,r5; movs r6,#12'
  end='lsrs r2,r0,#1' if second else ''
  return asm(f'''push {save}
{setup}
movs r0,#0
ldr r4,space
loop: cmp r3,#0
beq done
ldrh r2,[r1]
cmp r2,r4
bne full
lsrs r2,r6,#1
adds r0,r0,r2
b next
full: adds r0,r0,r6
next: adds r1,#2
subs r3,#1
b loop
done: {end}
pop {restore}
.align 2
space: .word {little}
''',0x8000000+at)
 first=helper(at,False);out[at:at+len(first)]=first
 assert source[0x3dbc:0x3dc0]==bytes.fromhex('281c7843')
 out[0x3dbc:0x3dc0]=asm(f'bl {0x8000000+at}',0x8003dbc)
 at2=(at+len(first)+3)&~3;second=helper(at2,True);out[at2:at2+len(second)]=second
 assert source[0x400e:0x4012]==bytes.fromhex('92199000')
 out[0x400e:0x4012]=asm(f'bl {0x8000000+at2}',0x800400e)
 assert source[0x40a0:0x40a2]==bytes.fromhex('9100')
 out[0x40a0:0x40a2]=asm('lsls r1,r2,#1',0x80040a0)
 at3=(at2+len(second)+3)&~3
 typer=asm("""push {r4,r5,r6,r7,lr}
sub sp,#44
ldr r4,context
ldr r5,source_field
ldrb r6,[r5,#15]
ldr r7,[r5]
ldrb r0,[r7,r6]
cmp r0,#0
beq finished
ldrb r0,[r5,#16]
cmp r0,#0
beq render
subs r0,#1
strb r0,[r5,#16]
b pending
render: movs r0,#4
strb r0,[r5,#16]
bl 0x08001468
movs r1,#3
ands r0,r1
beq copy_start
movs r0,#0
strb r0,[r5,#16]
copy_start: mov r0,r7
mov r1,sp
adds r2,r6,#2
copy: ldrb r3,[r0]
strb r3,[r1]
adds r0,#1
adds r1,#1
subs r2,#1
bne copy
movs r0,#0
strb r0,[r1]
cmp r6,#0
beq draw
lsls r0,r6,#1
adds r0,r0,r6
lsls r0,r0,#1
adds r0,#7
lsrs r0,r0,#3
lsls r0,r0,#1
ldr r1,allocation
ldrh r2,[r1]
subs r2,r2,r0
strh r2,[r1]
ldrh r2,[r1,#2]
subs r2,r2,r0
strh r2,[r1,#2]
draw: mov r0,sp
bl 0x08003d44
movs r0,#1
bl 0x080038d4
adds r6,#2
strb r6,[r5,#15]
pending: movs r0,#0
b done
finished: movs r0,#1
done: add sp,#44
pop {r4,r5,r6,r7,pc}
.align 2
context: .word 0x02006308
source_field: .word 0x020072a0
allocation: .word 0x0200729c
""",0x8000000+at3)
 out[at3:at3+len(typer)]=typer
 assert source[0x431c:0x4320]==bytes.fromhex('f0b582b0')
 out[0x431c:0x4324]=asm('ldr r3,[pc,#0]; bx r3; .word '+str(0x8000000+at3+1),0x800431c)
 return {'typewriter_prefix_render':True,'typewriter_helper':hex(at3),'typewriter_helper_size':len(typer),'space_pixels' :6,'normal_advance':12,'wide_mode_space_pixels':6,'hooks':[hex(0x3dbc),hex(0x400e)],'helper_offsets':[hex(at),hex(at2)],'helper_sizes':[len(first),len(second)]}
