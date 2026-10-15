from pathlib import Path
import struct,json
r=next(Path('.').glob('*Japan*.gba')).read_bytes();rows=json.loads(Path('work/source/script_lines.json').read_text());blocks=[]
for start in range(0xc80000,0xcc1e20,16):
 if r[start]!=1:continue
 end=struct.unpack_from('<I',r,start+1)[0]-0x8000000
 if not start+5<end<min(start+0x10000,0xcc1e20):continue
 p=end
 while p<end+20 and r[p] in (0x13,5,7,0x12):p+={0x13:2,5:3,7:3,0x12:2}[r[p]]
 if r[p]!=2:continue
 refs=[];needle=struct.pack('<I',0x8000000+start);at=0
 while True:
  at=r.find(needle,at)
  if at<0:break
  if at%4==0:refs.append(at)
  at+=1
 blocks.append(dict(start=start,end=p+1,skip=end,refs=refs,lines=sum(start<=x['offset']<p for x in rows)))
print('blocks',len(blocks),'lines',sum(b['lines'] for b in blocks),'refs',sum(len(b['refs']) for b in blocks));print('missingrefs',[(hex(b['start']),b['lines']) for b in blocks if not b['refs']]);print('refregions',sorted(set(hex(i//0x100) for b in blocks for i in b['refs'])))
assert sum(b['lines'] for b in blocks)==len(rows)
Path('work/source/script_blocks.json').write_text(json.dumps(blocks,indent=2))
