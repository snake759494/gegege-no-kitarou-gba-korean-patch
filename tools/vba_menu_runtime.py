"""Background VBA debugging: emulated KEYINPUT writes, no OS input or focus calls."""
import ctypes as c,struct,subprocess,time,json,hashlib,sys
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
from pathlib import Path
from capture_vba_framebuffer import framebuffer
R=Path(__file__).resolve().parent.parent;D=R/(sys.argv[1] if len(sys.argv)>1 else 'work/menu_direct_runtime');D.mkdir(exist_ok=True)
k=c.WinDLL('kernel32',use_last_error=True);k.OpenProcess.restype=c.c_void_p;k.ReadProcessMemory.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.c_size_t,c.c_void_p];k.WriteProcessMemory.argtypes=k.ReadProcessMemory.argtypes;k.CloseHandle.argtypes=[c.c_void_p]
def read(h,a,n):
 b=c.create_string_buffer(n);got=c.c_size_t();k.ReadProcessMemory(h,a,b,n,c.byref(got));return b.raw[:got.value]
def write(h,a,data):
 b=c.create_string_buffer(data);got=c.c_size_t();assert k.WriteProcessMemory(h,a,b,len(data),c.byref(got));assert got.value==len(data)
ini=R/'vba.ini';backup=ini.read_bytes();p=None;h=None
try:
 slow='slow' in sys.argv[3:]
 settings=backup.replace(b'pauseWhenInactive=1',b'pauseWhenInactive=0').replace(b'soundOff=0',b'soundOff=1').replace(b'filter=8',b'filter=0')
 settings=settings.replace(b'throttle=0',b'throttle=100') if slow else settings.replace(b'frameSkip=0',b'frameSkip=2')
 ini.write_bytes(settings)
 si=subprocess.STARTUPINFO();si.dwFlags=1;si.wShowWindow=0
 rom=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else next(R.glob('*Korean*.gba'));p=subprocess.Popen([str(R/'vba.exe'),str(rom)],cwd=R,startupinfo=si)
 time.sleep(4);h=k.OpenProcess(0x438,False,p.pid);data=read(h,0x400000,0x400000)
 hits=[off for off in range(0,len(data)-64,4) if struct.unpack_from('<I',data,off)[0]==0x3ffff and struct.unpack_from('<I',data,off+8)[0]==0x7fff and struct.unpack_from('<I',data,off+16)[0]==0x3ff];assert len(hits)==1
 k.SetPriorityClass.argtypes=[c.c_void_p,c.c_ulong];k.SetPriorityClass(h,0x20)
 u=c.WinDLL('user32');u.GetMenu.restype=c.c_void_p;cbtype=c.WINFUNCTYPE(c.c_bool,c.c_void_p,c.c_void_p);owned=[]
 @cbtype
 def enum_window(w,a):
  ident=c.c_ulong();u.GetWindowThreadProcessId(c.c_void_p(w),c.byref(ident))
  if ident.value==p.pid and u.GetMenu(c.c_void_p(w)):owned.append(w)
  return True
 u.EnumWindows(enum_window,0);assert len(owned)==1;window=owned[0]
 off=hits[0];rom_host=struct.unpack_from('<I',data,off-4+6*8)[0]
 write(h,rom_host+0x1fffff0,b'\xff\x03');write(h,rom_host+0x1408,struct.pack('<I',0x09fffff0))
 regions={name:(struct.unpack_from('<I',data,off-4+i*8)[0],size) for i,name,size in [(0,'ewram',0x40000),(1,'iwram',0x8000),(2,'io',0x400),(3,'pal',0x400),(4,'vram',0x18000),(5,'oam',0x400)]}
 def capture(name):
  d=D/name;d.mkdir(exist_ok=True)
  for n,(a,size) in regions.items():(d/(n+'.bin')).write_bytes(read(h,a,size))
  native,meta=framebuffer(lambda a,n:read(h,a,n));native.save(d/'native.png');(d/'native.json').write_text(json.dumps(meta,indent=2))
  (d/'capture.json').write_text(json.dumps({'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'emulator':str(R/'vba.exe'),'pid':p.pid,'emulated_input_only':True,'input_bridge':'runtime-only ROM literal 0x1408 redirected to reserved input halfword 0x09FFFFF0; on-disk ROM unchanged'},indent=2));print(name,flush=True)
 def key(bit):
  a=rom_host+0x1fffff0
  write(h,a,struct.pack('<H',0x3ff&~(1<<bit)));time.sleep(.07)
  write(h,a,b'\xff\x03');time.sleep(1.5)
 capture("00_title")
 time.sleep(3)
 for name,bit in ([] if len(sys.argv)>3 and sys.argv[3]=='manual' else [('01_start',3),('02_start',3),('03_a',0),('04_a',0),('05_skip',3),('06_a',0),('07_skip',3)]):
  key(bit);capture(name)
 control=R/'work/vba_command.json';control.write_text('{}');last=None;deadline=time.monotonic()+1800
 print('CONTROL_READY',flush=True)
 while time.monotonic()<deadline:
  try:cmd=json.loads(control.read_text(encoding='utf-8-sig'))
  except:time.sleep(.1);continue
  if cmd.get('id') is None or cmd['id']==last:time.sleep(.1);continue
  last=cmd['id'];deadline=time.monotonic()+1800
  if cmd.get('stop'):break
  if cmd.get('load_slot'):
   u.PostMessageW(c.c_void_p(window),0x111,40044+cmd['load_slot'],0);time.sleep(1)
  if cmd.get('save_slot'):
   u.PostMessageW(c.c_void_p(window),0x111,40034+cmd['save_slot'],0);time.sleep(1)
  if cmd.get('script') is not None:
   ident=cmd['script'];at=0x09fff000;return_scene=int(cmd.get('return_scene','0800af49'),16)|1
   reset_call='bl 0x080012b4; ' if cmd.get('game_reset') else ''
   asm=f'push {{lr}}; {reset_call}movs r0,#{ident}; ldr r1,ret; bl 0x0800f180; pop {{pc}}; .align 2; ret: .word {return_scene}'
   code=bytes(Ks(KS_ARCH_ARM,KS_MODE_THUMB).asm(asm,at)[0]);write(h,rom_host+0x1fff000,code)
   write(h,regions['iwram'][0]+0x39d8,bytes(160));write(h,regions['iwram'][0]+0x39d8,struct.pack('<IIII',at|1,0,0xffffffff,0x40001));time.sleep(1)
  if cmd.get('chapter') is not None:
   write(h,regions['iwram'][0]+0x4acb,bytes([cmd['chapter']]))
  for item in cmd.get('memory',[]):
   address=int(item['address'],16);blob=bytes.fromhex(item['hex'])
   if 0x02000000<=address and address+len(blob)<=0x02040000:base=regions['ewram'][0]+address-0x02000000
   elif 0x03000000<=address and address+len(blob)<=0x03008000:base=regions['iwram'][0]+address-0x03000000
   else:raise ValueError('runtime RAM write outside allowed regions')
   write(h,base,blob)
  if cmd.get('scene'):
   target=int(cmd['scene'],16)|1
   if cmd.get('scene_cleanup'):
    at=0x09fff000
    code=bytes(Ks(KS_ARCH_ARM,KS_MODE_THUMB).asm(f'push {{lr}}; bl 0x08021a20; ldr r0,next_scene; movs r1,#4; bl 0x080016e8; pop {{pc}}; .align 2; next_scene: .word {target}',at)[0])
    write(h,rom_host+0x1fff000,code);target=at|1
   write(h,regions['iwram'][0]+0x39d8,bytes(160))
   write(h,regions['iwram'][0]+0x39d8,struct.pack('<IIII',target,0,cmd.get('scene_counter',0xffffffff),0x40001))
   time.sleep(3)
  if cmd.get('chapter') is not None:
   write(h,regions['iwram'][0]+0x4acb,bytes([cmd['chapter']]))
  if cmd.get('game_mode') is not None:
   write(h,regions['iwram'][0]+0x4a61,bytes([cmd['game_mode']]))
  if cmd.get('house_choice') is not None:
   write(h,regions['ewram'][0]+0x17674,bytes([cmd['house_choice']]))
   time.sleep(.2)
  for action in cmd.get('actions',[]):
   bits=action.get('bits',[]);mask=0x3ff
   for bit in bits:mask &= ~(1<<bit)
   write(h,rom_host+0x1fffff0,struct.pack('<H',mask));time.sleep(action.get('hold',.07));write(h,rom_host+0x1fffff0,b'\xff\x03');time.sleep(action.get('wait',.5))
  if cmd.get('audit'):
   pages=[];seen=set();started=time.monotonic();limit=cmd.get('seconds',180);lastpress=0;trace=[];lastactive=time.monotonic()
   while time.monotonic()-started<limit:
    state=read(h,regions['ewram'][0]+0x178f4,0x80);ident=state[0];pc=struct.unpack_from('<I',state,8)[0];flags=state[0x14];task=struct.unpack('<I',read(h,regions['iwram'][0]+0x39d8,4))[0]
    entry=(ident,pc,flags);
    if not trace or trace[-1]['state']!=list(entry):trace.append({'t':round(time.monotonic()-started,3),'state':list(entry)})
    if task==0x0800f389:lastactive=time.monotonic()
    if time.monotonic()-lastactive>2:break
    if flags&2 and not flags&4:
     if (ident,pc) not in seen:
      name=f'script_{cmd["script"]:02}_page_{len(pages):03}';capture(name);pages.append(name);seen.add((ident,pc))
     write(h,rom_host+0x1fffff0,b'\xfe\x03');time.sleep(.025);write(h,rom_host+0x1fffff0,b'\xff\x03');time.sleep(.04)
    else:
     write(h,rom_host+0x1fffff0,b'\xfe\x03' if flags&4 else b'\xff\x03');time.sleep(.01)
   (D/f'audit_{cmd["script"]:02}.json').write_text(json.dumps({'script':cmd['script'],'pages':pages,'trace':trace,'elapsed':time.monotonic()-started,'last_task':hex(task),'last_state':list(entry),'timed_out':time.monotonic()-started>=limit},indent=2))
  if cmd.get('credits'):
   write(h,regions['ewram'][0]+0x1a140,struct.pack('<i',-255))
   seen=set();started=time.monotonic()
   while time.monotonic()-started<cmd.get('credits_seconds',180):
    state=read(h,regions['ewram'][0]+0x1a140,4);scroll=struct.unpack('<i',state)[0];page=scroll//256;phase=scroll%256
    if page>=0 and 70<=phase<=170 and page not in seen:
     capture(f'credits_{page:02}');seen.add(page)
    task=struct.unpack('<I',read(h,regions['iwram'][0]+0x39d8,4))[0]
    if task==0x08030f7d:break
    time.sleep(.01)
   (D/'credits_audit.json').write_text(json.dumps({'pages':sorted(seen),'elapsed':time.monotonic()-started,'last_task':hex(task)},indent=2))
  capture(cmd.get('capture','control_'+str(last)))
  (D/('command_'+str(last)+'.json')).write_text(json.dumps(cmd,ensure_ascii=False,indent=2),encoding='utf-8')
  print('COMMAND_DONE',last,flush=True)

finally:
 if h:k.CloseHandle(h)
 if p:p.terminate();p.wait()
 ini.write_bytes(backup)
