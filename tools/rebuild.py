"""Build and check the published ROM digest. External dependencies are user supplied."""
from pathlib import Path
import hashlib,json,subprocess,sys
R=Path(__file__).resolve().parents[1]
for f in json.loads((R/'data/font_manifest.json').read_text()):
 p=R/'work/fonts/galmuri'/f['name']
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:
  raise SystemExit('Missing or mismatched font: '+f['name']+'; see docs/BUILD.md')
subprocess.run([sys.executable,'-X','utf8',str(R/'tools/prepare_inputs.py')],cwd=R,check=True)
subprocess.run([sys.executable,'-X','utf8',str(R/'tools/build_patch.py')],cwd=R,check=True)
p=R/'Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Korean).gba'
h=hashlib.sha256(p.read_bytes()).hexdigest()
if h!='8fc91da197a79cd2e447c9fe38da12a12f361d4e257ceb1c81d76decfcb73307':raise SystemExit('Output digest differs: '+h)
print('Release ROM reproduced: '+h)
