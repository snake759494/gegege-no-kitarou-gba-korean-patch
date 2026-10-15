"""Read VBA 1.7.2's native screenshot framebuffer without a window or OS input."""
import ctypes as c,struct,json,hashlib,sys
from pathlib import Path
from PIL import Image

def framebuffer(read):
 # Verified from this vba.exe's GBA PNG/BMP exporters at 0041DCE0/0041DD10.
 ptr=struct.unpack('<I',read(0x604f14,4))[0]
 depth=struct.unpack('<I',read(0x58c014,4))[0]
 shifts=[struct.unpack('<I',read(a,4))[0] for a in (0x78b100,0x78b108,0x78b104)]
 assert depth in (16,24,32) and ptr>0x10000
 stride=240*(depth//8)+(4 if depth in (16,32) else 0)
 data=read(ptr,stride*162);im=Image.new('RGB',(240,160));pix=im.load()
 for y in range(160):
  for x in range(240):
   at=(y+1)*stride+x*(depth//8);v=int.from_bytes(data[at:at+depth//8],'little')
   pix[x,y]=tuple(((v>>s)&31)*8 for s in shifts)
 return im,{'capture_method':'VBA native pix framebuffer; no PPU reconstruction or window capture','depth':depth,'stride':stride,'rgb_shifts':shifts}

if __name__=='__main__':
 pid=int(sys.argv[1]);out=Path(sys.argv[2]);out.parent.mkdir(exist_ok=True,parents=True)
 k=c.WinDLL('kernel32');k.OpenProcess.restype=c.c_void_p;k.ReadProcessMemory.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.c_size_t,c.c_void_p];k.CloseHandle.argtypes=[c.c_void_p];h=k.OpenProcess(0x410,False,pid)
 def rd(a,n):
  b=c.create_string_buffer(n);z=c.c_size_t();assert k.ReadProcessMemory(h,a,b,n,c.byref(z));assert z.value==n;return b.raw
 try:im,meta=framebuffer(rd);im.save(out);out.with_suffix('.json').write_text(json.dumps(meta,indent=2))
 finally:k.CloseHandle(h)
 print(out)
