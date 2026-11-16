/** Append source-owned walking/paving triangles in an isolated overlay. No public writes. */
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {resolve,relative,join} from 'node:path';import {createHash} from 'node:crypto';
import {CitySiteSurfaces} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-site-surfaces.ts';
import {planSitePaths} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-site-path-plan.ts';
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,all)=>i%2?a:[...a,[v.replace(/^--/,''),all[i+1]]],[]));
for(const key of ['base','addition','addition-sha256','output'])if(!args[key])throw Error('Missing '+key);
const base=resolve(args.base),addition=resolve(args.addition),out=resolve(args.output),artifactRoot=resolve('artifacts');
if(!out.startsWith(artifactRoot+'/')||out.includes('/public/')||existsSync(out))throw Error('Fresh isolated artifact output is required');
const hash=b=>createHash('sha256').update(b).digest('hex'),read=p=>readFileSync(p),record=p=>{const b=read(p);return {file:relative(process.cwd(),p),bytes:b.length,sha256:hash(b)};};
const manifestBytes=read(join(base,'manifest.json')),manifest=JSON.parse(manifestBytes);
if(!/^[a-z0-9-]+\.json$/.test(manifest.siteSurfacesFile))throw Error('Invalid site surface filename');
const originalBytes=read(join(base,manifest.siteSurfacesFile));
if(manifest.cityId!=='hangzhou'||hash(originalBytes)!==manifest.siteSurfacesSha256)throw Error('Base site surfaces are not bound to the current geography manifest');
const additionBytes=read(addition);if(hash(additionBytes)!==args['addition-sha256'])throw Error('Addition changed after review');
const original=JSON.parse(originalBytes),patch=JSON.parse(additionBytes);
if(patch.cityId!==original.cityId||patch.units!==original.units||!patch.pathDisplays?.length)throw Error('Path city/units/display ownership missing');
for(const key of ['terrainCuts','roadSurfaces','solidSlabs'])if(patch[key]?.length)throw Error('This local walking overlay cannot replace ground or road structures');
let groundEvidence=null;
if(patch.terrainPatches?.length){
 if(!args['ground-evidence'])throw Error('Mesh-derived ground patch needs hash-bound contact evidence');
 groundEvidence=JSON.parse(read(args['ground-evidence']));
 if(!groundEvidence.pass||groundEvidence.surface?.sha256!==hash(additionBytes)||groundEvidence.buriedSamples||groundEvidence.floatingSamples||groundEvidence.missingSamples)throw Error('Ground contact evidence failed or belongs to another candidate');
 for(const source of groundEvidence.sources)if(hash(read(source.path))!==source.sha256)throw Error('Ground source GLB changed');
 if(patch.terrainPatches.length!==1||patch.walkFloors.length!==1)throw Error('This ground patch contract is for one coupled path only');
 const ground=patch.terrainPatches[0].triangles,floor=patch.walkFloors[0].triangles;
 if(ground.length!==floor.length||ground.some((t,i)=>t.some((v,k)=>v[0]!==floor[i][k][0]||v[1]!==floor[i][k][1]||Math.abs(floor[i][k][2]-v[2]-.015)>1e-10)))throw Error('Ground and walking floor must have identical planimetric ownership and declared bedding');
}
const merged=structuredClone(original);
const appended=['walkFloors','accessCorridors','pathDisplays',...(patch.terrainPatches?.length?['terrainPatches']:[])];
for(const key of appended){
 const old=original[key]??[],extra=patch[key]??[],identity=key==='accessCorridors'?'sourceId':'id';
 const ids=new Set(old.map(v=>v[identity]));for(const v of extra){if(!v[identity]||ids.has(v[identity]))throw Error('Repeated '+key+' ownership');ids.add(v[identity]);}
 merged[key]=[...old,...extra];
}
// These are the same parsers used by the world; geometry is not re-created from a second path representation.
new CitySiteSurfaces(merged);const plans=planSitePaths(merged.walkFloors,merged.pathDisplays);
const body=JSON.stringify(merged)+'\n',resultManifest={...manifest,siteSurfacesSha256:hash(body)};
mkdirSync(out,{recursive:true});writeFileSync(join(out,manifest.siteSurfacesFile),body);writeFileSync(join(out,'manifest.json'),JSON.stringify(resultManifest)+'\n');
const report={schemaVersion:1,kind:'isolated site path overlay; not runtime installation',baseManifest:record(join(base,'manifest.json')),baseSurfaces:record(join(base,manifest.siteSurfacesFile)),addition:record(addition),
 outputs:[record(join(out,'manifest.json')),record(join(out,manifest.siteSurfacesFile))],appendedFloors:patch.walkFloors.length,appendedSourceCorridors:patch.accessCorridors?.length??0,displayedTriangles:plans.reduce((n,p)=>n+p.indices.length/3,0),
 groundEvidence:args['ground-evidence']?record(args['ground-evidence']):null,
 preserved:{allAppendedFieldPrefixes:appended.every(k=>JSON.stringify(merged[k].slice(0,original[k]?.length??0))===JSON.stringify(original[k]??[])),allOtherOriginalFields:Object.keys(original).filter(k=>!appended.includes(k)).every(k=>JSON.stringify(original[k])===JSON.stringify(merged[k]))},
 runtimeInstalled:false,physicalAcceptance:'depends on source candidate audit; parsing does not prove traversability',browserAccepted:false};
if(!Object.values(report.preserved).every(Boolean))throw Error('Original surfaces changed');
writeFileSync(join(out,'staging-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
