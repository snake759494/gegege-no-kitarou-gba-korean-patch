"""Relocate all quoted scene scripts and supplement padded UI text."""
import json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def load_complete_text():
 unique=json.loads((ROOT/'work/source/script_unique.json').read_text(encoding='utf-8'))
 translated=[]
 for p in sorted((ROOT/'translation').glob('script_*.txt')):
  start=int(p.stem.split('_')[1]);assert start==len(translated),(p,start,len(translated))
  translated.extend(p.read_text(encoding='utf-8-sig').splitlines())
 assert len(translated)==len(unique)==1252
 assert all(t and len(t)<=19 for t in translated)
 mapping=dict(zip(unique,translated))
 menu=json.loads((ROOT/'work/source/extra_menu.json').read_text(encoding='utf-8'))
 ko=(ROOT/'translation/extra_menu.txt').read_text(encoding='utf-8-sig').splitlines()
 assert len(menu)==len(ko)==79
 for r,t in zip(menu,ko):
  assert r['text'].count('%s')==t.count('%s')
  r['korean']=t
 return mapping,menu

def patch_scripts(source,out,mapping,codes,encode):
 rows=json.loads((ROOT/'work/source/script_lines.json').read_text(encoding='utf-8'))
 blocks=json.loads((ROOT/'work/source/script_blocks.json').read_text(encoding='utf-8'))
 reports=[];total=0
 for block in blocks:
  start,end,skip=block['start'],block['end'],block['skip']
  entries=[r for r in rows if start<=r['offset']<end]
  cursor=start;blob=bytearray();new_skip=None
  for row in entries:
   pos=row['offset'];n=row['length']
   assert source[pos:pos+n].decode('cp932')==row['text']
   blob.extend(source[cursor:pos]);data=encode(mapping[row['text']],codes)[:-2]
   assert not any(x in data for x in (0,34,92)),(pos,'unsafe script byte')
   blob.extend(data);cursor=pos+n;total+=1
  blob.extend(source[cursor:end])
  delta=len(blob)-(end-start);new_skip=skip-start+delta
  assert source[skip:end]==blob[new_skip:],('closing commands changed',hex(start))
  out.extend(b'\xff'*((-len(out))%16));dest=len(out)
  struct.pack_into('<I',blob,1,0x8000000+dest+new_skip)
  out.extend(blob)
  for ref in block['refs']:
   assert struct.unpack_from('<I',source,ref)[0]==0x8000000+start
   struct.pack_into('<I',out,ref,0x8000000+dest)
  reports.append(dict(original_offset=hex(start),new_offset=hex(dest),size=len(blob),lines=len(entries),table_refs=block['refs']))
 assert total==2638
 (ROOT/'work/build/script_report.json').write_text(json.dumps({'blocks':reports,'translated_occurrences':total,'unique_lines':1252,'max_glyphs_per_line':19},ensure_ascii=False,indent=2),encoding='utf-8')
 return {'blocks':len(blocks),'translated_occurrences':total,'unique_lines':1252,'table_references':sum(len(b['refs']) for b in blocks),'untranslated':0}
