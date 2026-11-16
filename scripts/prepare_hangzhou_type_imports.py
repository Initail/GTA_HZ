"""Copy locked Babylon declarations, resolving only barrel type imports.

Every target is the unique original declaration reachable through the original
barrel's export graph. All actual API declarations and augmentations are kept.
No stub, any substitution, suppressed diagnostic, or dependency update is used.
"""
import re,json,hashlib,os,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'node_modules/@babylonjs/core'
C=ROOT/'artifacts/cities/hangzhou/city-leisure-v15'
p=argparse.ArgumentParser();p.add_argument('--revision',default='v1');args=p.parse_args()
assert re.fullmatch(r'v[0-9]+',args.revision)
suffix='' if args.revision=='v1' else '-'+args.revision
OUT=C/('type-declarations'+suffix)/'core'
PAT=re.compile(r"import\s+(type\s+)?\{([^{}]+)\}\s+from\s*['\"]([^'\"]*index\.js)['\"];?")
INLINE=re.compile(r'''import\((["'])([^"']*index\.js)\1\)\.(\w+)''')
DEFS=re.compile(r'^export\s+(?:declare\s+)?(?:abstract\s+)?(?:class|function|const|let|var|interface|type|enum)\s+(\w+)',re.M)
EX=re.compile(r"export\s+(?:\*|\{[^{}]*\})\s+from\s*['\"]([^'\"]+)['\"]")
def sha(data):return hashlib.sha256(data).hexdigest()
def declaration(parent,specifier):return (parent/specifier).resolve().with_suffix('.d.ts')
def main():
    if OUT.exists():raise SystemExit('Existing declarations are protected')
    texts={p:p.read_text() for p in BASE.rglob('*.d.ts')};origins={};needed=set();edges={}
    for p,text in texts.items():
        edges[p]=[declaration(p.parent,m) for m in EX.findall(text) if m.startswith('.')]
        for name in DEFS.findall(text):origins.setdefault(name,[]).append(p)
        for m in PAT.finditer(text):needed.update(re.sub(r'^type\s+','',v.strip()).split(' as ')[0] for v in m.group(2).split(',') if v.strip())
        for m in INLINE.finditer(text):needed.add(m.group(3))
    assert all(len(origins.get(n,[]))==1 for n in needed),'Ambiguous or missing declaration origin'
    closures={}
    def reachable(p):
        if p in closures:return closures[p]
        todo=[p];seen=set()
        while todo:
            q=todo.pop()
            if q in seen:continue
            seen.add(q);todo.extend(edges.get(q,[]))
        closures[p]=seen;return seen
    rewrites=[];unchanged={}
    for source,text in texts.items():
        def replace(m):
            barrel=declaration(source.parent,m.group(3));groups={}
            for item in m.group(2).split(','):
                item=item.strip()
                if not item:continue
                name=re.sub(r'^type\s+','',item).split(' as ')[0];target=origins[name][0]
                assert target in reachable(barrel),(name,str(barrel),str(target))
                relative=os.path.relpath(target,source.parent).replace('.d.ts','.js')
                if not relative.startswith('.'):relative='./'+relative
                groups.setdefault(relative,[]).append(item)
            return '\n'.join('import '+(m.group(1) or '')+'{ '+', '.join(items)+' } from "'+name+'";' for name,items in groups.items())
        def replace_inline(m):
            barrel=declaration(source.parent,m.group(2));target=origins[m.group(3)][0]
            assert target in reachable(barrel)
            relative=os.path.relpath(target,source.parent).replace('.d.ts','.js')
            if not relative.startswith('.'):relative='./'+relative
            return 'import('+m.group(1)+relative+m.group(1)+').'+m.group(3)
        rewritten=INLINE.sub(replace_inline,PAT.sub(replace,text));target=OUT/source.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(rewritten)
        if rewritten!=text:rewrites.append({'file':str(source.relative_to(BASE)),'beforeSha256':sha(text.encode()),'afterSha256':sha(rewritten.encode()),'importStatements':len(PAT.findall(text)),'inlineImports':len(INLINE.findall(text))})
        else:unchanged[str(source.relative_to(BASE))]=sha(text.encode())
    config=json.loads((ROOT/'artifacts/cities/hangzhou/city-leisure-v14/tsconfig.browser.json').read_text())
    prefix='./type-declarations'+suffix+'/core/'
    config['compilerOptions']['paths']={'@babylonjs/core':[prefix+'index.d.ts'],'@babylonjs/core/*':[prefix+'*']}
    (C/('tsconfig.declarations'+suffix+'.json')).write_text(json.dumps(config,indent=2)+'\n')
    report={'schemaVersion':1,'lockedVersion':json.loads((BASE/'package.json').read_text())['version'],'packageLockSha256':sha((ROOT/'package-lock.json').read_bytes()),'rewrites':rewrites,'unchangedDeclarations':unchanged,'originalApiBodiesPreserved':True,'uniqueOriginalBindingsAndExportReachabilityChecked':True,'strictTypecheckPassed':False,'scope':'import graph normalization only; complete diagnostics still required'}
    (C/('type-import-report'+suffix+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'declarations':len(texts),'rewrittenFiles':len(rewrites),'rewrittenImports':sum(r['importStatements'] for r in rewrites),'inlineImports':sum(r['inlineImports'] for r in rewrites),'unchangedDeclarations':len(unchanged),'stubDeclarations':0}))
if __name__=='__main__':main()
