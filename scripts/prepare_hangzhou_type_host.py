"""Inventory the actual locked TypeScript inputs for a bounded alternate host."""
import hashlib,json,os,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--candidate',default='artifacts/cities/hangzhou/city-leisure-v14');p.add_argument('--config',default='tsconfig.browser.json');p.add_argument('--output',default='type-input-v1.json');a=p.parse_args()
candidate=(ROOT/a.candidate).resolve()
candidate.relative_to(ROOT/'artifacts/cities/hangzhou')
out=candidate/a.output
if out.exists():raise SystemExit('Existing type-host input is protected')
files=[];directories=[]
for base in [ROOT/'node_modules',candidate/'src',*candidate.glob('type-declarations*')]:
    for parent,children,names in os.walk(base):
        directories.append(parent)
        files.extend(str(Path(parent)/name) for name in names)
for parent in [ROOT,candidate,*candidate.parents]:directories.append(str(parent))
compiler=ROOT/'node_modules/typescript/lib/typescript.js'
result={'cwd':str(ROOT),'projectDirectory':str(candidate),'compilerFile':str(compiler),'compilerLib':str(compiler.parent),'compilerSha256':hashlib.sha256(compiler.read_bytes()).hexdigest(),'compilerOptions':json.loads((candidate/a.config).read_text())['compilerOptions'],'files':sorted(files),'directories':sorted(set(directories)),'rootNames':sorted(str(p) for p in (candidate/'src').rglob('*.ts'))}
out.write_text(json.dumps(result,separators=(',',':'))+'\n')
print(json.dumps({'fileCount':len(files),'rootFiles':len(result['rootNames']),'bytes':out.stat().st_size,'compilerSha256':result['compilerSha256']}))
