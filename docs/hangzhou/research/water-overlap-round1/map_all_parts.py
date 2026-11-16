"""Audit all runtime water parts against unsimplified fixed-source polygon parts."""
from pathlib import Path
from collections import defaultdict,Counter
import datetime,hashlib,json,time
import shapely
from shapely.geometry import Polygon,shape,box
from shapely.ops import transform
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[3]
CITY=PROJECT/'artifacts/cities/hangzhou/runtime-data-v4/city.json';WATER=PROJECT/'data/processed/hangzhou-261011-extended/water.geojson'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parts(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return [g]
 return [p for q in getattr(g,'geoms',[]) for p in parts(q)]
def vc(g):
 rs=[g.exterior,*g.interiors];closed=sum(len(r.coords) for r in rs);unique=sum(len(r.coords)-int(r.coords[0]==r.coords[-1]) for r in rs)
 return dict(rings=len(rs),holes=len(g.interiors),coordinatesIncludingClosure=closed,verticesExcludingRingClosure=unique,theoreticalTrianglesWithoutSteinerOrCollinearRemoval=unique+2*len(g.interiors)-2)
t0=time.monotonic();c=json.loads(CITY.read_text());w=json.loads(WATER.read_text());m=c['meta'];o=m['originWGS84'];e=m['eastMetresPerDegree'];n=m['northMetresPerDegree'];sc=m['horizontalScale'];bounds=box(*m['extent'])
def proj(x,y,z=None):return ((x-o[0])*e*sc,(y-o[1])*n*sc)
raw={};dropped=[];sourceCounts=Counter()
for f in w['features']:
 g=transform(proj,shape(f['geometry'])).intersection(bounds);pp=parts(g);sourceCounts[g.geom_type]+=1
 for i,p in enumerate(pp):
  if p.area<20:dropped.append(dict(id=f['id'],sourcePartIndex=i,areaGameSquared=p.area,reason='original builder rejects source polygon area<20 game² before simplification'))
  else:raw[(f['id'],i)]=p
byid=defaultdict(list)
for key,p in raw.items():byid[key[0]].append((key[1],p))
rows=[];unmatched=[];used=Counter();totalRuntime=Counter();totalRaw=Counter()
for i,b in enumerate(c['water']):
 p=Polygon(b['rings'][0],b['rings'][1:]);cand=byid.get(b['id'],[])
 if not cand:unmatched.append(dict(runtimeIndex=i,id=b['id'],reason='no eligible raw Polygon part'));continue
 overlaps=[(q.intersection(p).area,j,q) for j,q in cand];area,j,q=max(overlaps,key=lambda z:z[0]);positive=sum(a>1e-8 for a,_,_ in overlaps);used[(b['id'],j)]+=1
 rawvc=vc(q);runvc=vc(p)
 for k,v in runvc.items():totalRuntime[k]+=v
 for k,v in rawvc.items():totalRaw[k]+=v
 # GEOS discrete Hausdorff with vertices and hundredth-edge samples; measured delta, not survey accuracy.
 haus=float(shapely.hausdorff_distance(q.boundary,p.boundary,densify=.01))
 rows.append(dict(runtimeIndex=i,id=b['id'],sourcePartIndex=j,sourcePartCountForFeature=len(cand),sourcePartsWithPositiveOverlap=positive,matchedBy='maximum intersection area among same-feature eligible raw Polygon parts',intersectionGameSquared=area,sourceAreaGameSquared=q.area,runtimeAreaGameSquared=p.area,intersectionOverUnion=area/q.union(p).area,sourceVertices=rawvc,runtimeVertices=runvc,sampledBoundaryHausdorffGame=haus,sampledBoundaryHausdorffRealMetres=haus/sc,sourceToRuntimeSymmetricDifferenceGameSquared=q.symmetric_difference(p).area,actualBuilderSimplifyMatch=p.equals_exact(q.simplify(.3,preserve_topology=True),.0001),heightGame=b.get('height'),heightStatus=b.get('heightStatus')))
duplicate=[dict(id=k[0],sourcePartIndex=k[1],mappedRuntimeParts=v) for k,v in used.items() if v!=1];unused=[dict(id=k[0],sourcePartIndex=k[1]) for k in raw if not used[k]]
worst=sorted(rows,key=lambda r:r['sampledBoundaryHausdorffGame'],reverse=True)
out=dict(kind='all-runtime-water-parts-fixed-source-crosswalk',asOfDate='2026-10-16',inputs=dict(citySha256=sha(CITY),waterSha256=sha(WATER)),units='game metres from frozen city metadata; horizontal scale0.60 applied once; real metres=game/0.60',runtimeWaterParts=len(c['water']),eligibleUnsimplifiedSourceParts=len(raw),matchedRuntimeParts=len(rows),oneToOne=(len(rows)==len(c['water'])==len(raw) and not duplicate and not unused and not unmatched),unmatchedRuntimeParts=unmatched,duplicateSourceMappings=duplicate,unmappedEligibleSourceParts=unused,droppedSmallSourceParts=dropped,sourceGeometryTypeCounts=sourceCounts,vertexBudget=dict(runtime=totalRuntime,unsimplified=totalRaw,coordinateIncrease=totalRaw['coordinatesIncludingClosure']-totalRuntime['coordinatesIncludingClosure'],coordinateRatio=totalRaw['coordinatesIncludingClosure']/totalRuntime['coordinatesIncludingClosure'],note='2D ring budget and topology triangle formula only; no GLB/GPU/Blender validation, holes and source parts retained. Actual earcut/collinear/deck batching may differ.'),maximumSampledBoundaryChange=({k:v for k,v in worst[0].items() if k not in ['sourceVertices','runtimeVertices']} if worst else None),boundaryMeasurement='GEOS discrete Hausdorff of full polygon boundaries, original vertices plus hundredth-edge samples (densify=.01). This is a sampled geometric change metric, not a certified continuous Hausdorff upper bound or real-world survey error.',allCurrentPartsMatchBuilderSimplify=all(z['actualBuilderSimplifyMatch'] for z in rows),worstBoundaryChanges=[{k:v for k,v in z.items() if k in ['runtimeIndex','id','sourcePartIndex','sampledBoundaryHausdorffGame','sampledBoundaryHausdorffRealMetres']} for z in worst[:25]],parts=rows,elapsedSeconds=round(time.monotonic()-t0,3),checkedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
(ROOT/'all-parts-crosswalk.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['parts','droppedSmallSourceParts','worstBoundaryChanges']},ensure_ascii=False,indent=2))
