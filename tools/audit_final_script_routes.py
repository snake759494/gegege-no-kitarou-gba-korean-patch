from pathlib import Path
import json,struct,hashlib
R=Path(__file__).resolve().parent.parent;orig=next(R.glob('*Japan).gba')).read_bytes();rom=next(R.glob('*Korean).gba')).read_bytes()
blocks=json.loads((R/'work/source/script_blocks.json').read_text());lines=json.loads((R/'work/source/script_lines.json').read_text(encoding='utf-8'));mapping={b['start']:b for b in blocks}
def refs(value):
 needle=struct.pack('<I',value);out=[];p=0
 while (at:=orig.find(needle,p))>=0:out.append(hex(at));p=at+1
 return out
pairs=[]
for ident in range(50):
 a=struct.unpack_from('<I',orig,0xc86420+ident*4)[0]-0x8000000;b=struct.unpack_from('<I',orig,0xcb52c0+ident*4)[0]-0x8000000
 x=[z['text'] for z in lines if a<=z['offset']<mapping[a]['end']];y=[z['text'] for z in lines if b<=z['offset']<mapping[b]['end']];assert x==y
 pairs.append({'scene':ident,'active':hex(a),'duplicate':hex(b),'dialogue_occurrences':len(x),'text_equal':True})
orphans=[{'offset':hex(b['start']),'lines':b['lines'],'all_byte_aligned_and_unaligned_pointer_refs':refs(0x8000000+b['start'])} for b in blocks if not b['refs']]
assert not any(b['all_byte_aligned_and_unaligned_pointer_refs'] for b in orphans)
assert not refs(0x08cb52c0)
report={'rom_sha256':hashlib.sha256(rom).hexdigest(),'active_entry_table':'0C86420','active_entries':50,'unused_duplicate_table':'0CB52C0','duplicate_table_pointer_refs':[],'duplicate_dialogue_pairs':pairs,'unreferenced_blocks':orphans,'translated_blocks':103,'translated_occurrences':2638,'scope':'50 active scene entries; duplicate table has identical dialogue and no pointer references; three additional blocks have no full-ROM pointer references.'}
(R/'work/build/final_script_route_audit.json').write_text(json.dumps(report,indent=2));print('50 active; 50 duplicate dialogue pairs equal; 3 unreferenced blocks')
