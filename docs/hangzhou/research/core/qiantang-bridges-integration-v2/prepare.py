from pathlib import Path
import json,sys,hashlib,math,collections,heapq
import numpy as np
P=Path(__file__).resolve().parent;ROOT=P.parents[4];sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=ROOT/'docs/hangzhou/research/core/qiantang-bridges-round2/spec.json';original=json.loads(source.read_text());fpath=ROOT/'docs/hangzhou/research/core/fuxing-alignment-round1/spec.json';fuxing=json.loads(fpath.read_text());rpath=ROOT/'artifacts/cities/hangzhou/render-input-v7/geography/road-levels.json';roads=json.loads(rpath.read_text())['roads'];city=load_city('hangzhou');anchor=project(original['anchor']['lon'],original['anchor']['lat'],city);byway={r['id'].split('#')[0]:r for r in roads};bridges={};audit=[];heightOverrides={'fuxing-bridge':{'upperWaterRelativeM':26.25}}
for b in original['bridges']:
 fix=fuxing['candidateAxis'] if b['id']=='fuxing-bridge' else {'centerWGS84':b['centerWGS84'],'radiansEastCCW':b['axisRadiansEastCCW']};center=project(*fix['centerWGS84'],city);angle=fix['radiansEastCCW'];u=np.array([math.cos(angle),math.sin(angle)]);n=np.array([-u[1],u[0]]);effectiveProfile={**b['profile'],**heightOverrides.get(b['id'],{})};targets={level:.9+(effectiveProfile[level+'WaterRelativeM']+(.25 if b['id']=='qiantang-bridge' and level=='upper' else 0))*.6 for level in ['upper','lower','single'] if level+'WaterRelativeM' in b['profile']};bridges[b['id']]={'centerWGS84':fix['centerWGS84'],'axisRadiansEastCCW':angle,'mainIntervalM':b['profile']['mainIntervalM'],'targetsGame':targets,'datumBasis':'reference-informed estimated rigid core heights; explicit Fuxing upper and Qiantang upper revisions are in heightRevisionBasis/qiantangDeckOffsetBasis; old values preserved; .9 legacy display reference is not measured current river level','reported':b['reported'],'uncertainties':b['estimates'],'sourceRoads':[],'railways':b['railways'],'pending':b['pending']}
 for entry in b['roads']+b.get('outsideOldBoundsContinuations',[]):
  r=byway.get(entry['id']);rec={'sourceWayId':entry['id'],'bridgeId':b['id'],'mode':'road','deck':entry['deck'],'existsInRuntime':r is not None}
  if r:
   pts=np.array(r['points']);st=(pts-center)@u/.6;lat=(pts-center)@n/.6;rec.update({'sourceRoadId':r['id'],'nodeIds':r['nodeIds'],'points':r['points'],'sourceCoordinatesUnchanged':max(math.dist(project(*w,city),p) for w,p in zip(entry['coordinatesWGS84'],r['points']))<1e-7 and len(entry['coordinatesWGS84'])==len(r['points']),'originalHeights':r['heights'],'heightBasis':r['heightBasis'],'widthGame':r['width'],'stationM':st.tolist(),'lateralM':lat.tolist(),'coreTargetGame':targets[entry['deck']],'maxCoreNodeHeightDifference':max([abs(h-targets[entry['deck']]) for h,s in zip(r['heights'],st) if abs(s)<b['profile']['mainIntervalM'][1]] or [0])})
  bridges[b['id']]['sourceRoads'].append(rec);audit.append(rec)
inputs=['scripts/landmarks/qiantang_bridges.py',str(source.relative_to(ROOT)),'scripts/landmarks/fuxing_alignment.py',str(fpath.relative_to(ROOT)),'scripts/landmarks/qiantang_bridge_collision.py','config/cities/hangzhou.json',str(rpath.relative_to(ROOT))]
spec={'schemaVersion':1,'id':'qiantang-bridges-integration-v2','cityId':'hangzhou','scope':'Original three identifiable structural bridges, corrected Fuxing axis, semantic removal of road-deck primitives only. Source renderer sole road-deck owner; independent estimated node-height proposal must be integrated simultaneously','originalModule':inputs[0],'originalSpec':inputs[1],'frozenInputs':{f:sha(ROOT/f) for f in inputs},'placementGame':{'x':anchor[0],'z':anchor[1],'y':.9},'scale':.6,'qiantangUpperDeckAboveChordM':.25,'qiantangDeckOffsetBasis':'estimated road slab on top of retained .24m upper truss chord radius plus .01m geometric seam allowance; original truss and railway unchanged; original upper road height12.3game retained in failure snapshot, proposed12.45','heightOverridesPhysicalM':heightOverrides,'heightRevisionBasis':{'fuxingUpper':{'oldRelativeWaterM':22,'newRelativeWaterM':26.25,'status':'estimated constructibility revision; not measured','formula':'lower12 +smallArchRise12.15 +smallTubeRadius.85 +upperDeckThickness1.25; upper road entirely above small arches, preserving all arches','evidence':'same frozen original primary PDF figure8 + identified old small arch/upper road physical overlap; exact deck/tide datum unknown'}},'bridges':bridges,'budget':original['budget'],'stage':'planned; source heights and ownership under CPU review','nightPolicy':'retain all original materials/guardrails; original source has 0 new lights and no verified bridge luminaires; do not claim invented night-light reconstruction','pending':['source renderer bridge support domains and road height proposal not installed','near-end Fuxing lower-way full-width compatibility','approach/rail clearances and current permissions','actual GLB, day/night/browser/performance']};(P/'spec.json').write_text(json.dumps(spec,indent=2));(P/'source-road-audit.json').write_text(json.dumps({'sourceRoadLevelsSha256':sha(rpath),'rows':audit},indent=2))
# Source graph only: original shared node identities, never geometric crossings.
graph=collections.defaultdict(dict);occ=collections.defaultdict(list);pos={}
for r in roads:
 for i,(node,p,h) in enumerate(zip(r['nodeIds'],r['points'],r['heights'])):node=str(node);occ[node].append((r['id'],i,h));pos[node]=p
 for i,(a,b) in enumerate(zip(r['nodeIds'],r['nodeIds'][1:])):
  a,b=str(a),str(b);L=math.dist(r['points'][i],r['points'][i+1]);
  if L>1e-9:graph[a][b]=min(graph[a].get(b,math.inf),L);graph[b][a]=min(graph[b].get(a,math.inf),L)
seeds={};seedSources=collections.defaultdict(list);conflicts=[];seedRows=[]
for b in original['bridges']:
 fix=bridges[b['id']];half=fix['mainIntervalM'][1]
 for rec in fix['sourceRoads']:
  if not rec.get('existsInRuntime'):continue
  if rec['sourceWayId'] not in [r['id'] for r in b['roads']]:continue
  st=rec['stationM'];selected=set()
  # Include both original endpoints of each source segment crossing the finite
  # structural main interval. Thus interpolating unchanged graph edges keeps
  # the whole visible main span rigid; no synthetic graph nodes are inserted.
  for i,(a,c) in enumerate(zip(st,st[1:])):
   if max(min(a,c),-half)<min(max(a,c),half)-1e-8:selected.update([i,i+1])
  for i in sorted(selected):
   node=str(rec['nodeIds'][i]);target=rec['coreTargetGame']
   if node in seeds and abs(seeds[node]-target)>1e-8:conflicts.append({'nodeId':node,'oldTarget':seeds[node],'newTarget':target,'bridge':b['id']})
   seeds[node]=target;seedSources[node].append({'bridgeId':b['id'],'deck':rec['deck'],'sourceRoadId':rec['sourceRoadId'],'stationM':st[i]});seedRows.append({'nodeId':node,'target':target,'stationM':st[i],'coreHalfLengthM':half,'reason':'original source segment endpoint covering finite main span; may extend flat core beyond nominal hinge station'})
# Candidate boundary radius uses only source-edge graph distance. It extends
# original road-node values through genuine approach branches to avoid cracks.
# All radius-boundary nodes retain their old heights exactly.
radii={b['id']:b['profile']['transitionM']*.6 for b in original['bridges']};dist={};inside=set();distanceByBridge={}
for bridge_id,radius in radii.items():
 local_seeds=[n for n in seeds if any(v['bridgeId']==bridge_id for v in seedSources[n])];localdist={n:0. for n in local_seeds};queue=[(0.,n) for n in local_seeds];heapq.heapify(queue)
 while queue:
  d,a=heapq.heappop(queue)
  if d!=localdist[a] or d>=radius:continue
  for b,L in graph[a].items():
   v=d+L
   if v<localdist.get(b,math.inf):localdist[b]=v;heapq.heappush(queue,(v,b))
 inside.update(n for n,d in localdist.items() if d<radius);distanceByBridge[bridge_id]=localdist
 for n,d in localdist.items():dist[n]=min(dist.get(n,math.inf),d/radius)
boundary={b for a in inside for b in graph[a] if b not in inside};nodes=sorted(inside|boundary);index={n:i for i,n in enumerate(nodes)};raw={n:occ[n][0][2] for n in nodes};rawDisagreements=[{'nodeId':n,'occurrences':occ[n],'range':max(v[2] for v in occ[n])-min(v[2] for v in occ[n])} for n in nodes if max(v[2] for v in occ[n])-min(v[2] for v in occ[n])>1e-8]
y=np.array([raw[n] for n in nodes]);fixed=np.array([n in seeds or n in boundary for n in nodes]);fixedValues=y.copy()
for n,h in seeds.items():fixedValues[index[n]]=h
y[fixed]=fixedValues[fixed];aa=[];bb=[];ww=[]
for a in nodes:
 for b,L in graph[a].items():
  if b in index:aa.append(index[a]);bb.append(index[b]);ww.append(1/L)
aa,bb,ww=np.array(aa),np.array(bb),np.array(ww);den=np.bincount(aa,weights=ww,minlength=len(nodes));error=math.inf
for iteration in range(100000):
 avg=np.bincount(aa,weights=ww*y[bb],minlength=len(nodes))/np.maximum(den,1e-30);avg[fixed]=fixedValues[fixed];fresh=y*.2+avg*.8;fresh[fixed]=fixedValues[fixed];error=float(np.abs(fresh-y).max());y=fresh
 if error<1e-10:break
if error>=1e-10:raise RuntimeError('Harmonic source-node proposal failed to converge')
nodeResult={n:(float(y[index[n]]) if abs(float(y[index[n]])-raw[n])>1e-9 else raw[n]) for n in nodes};changed={n for n in nodes if abs(nodeResult[n]-raw[n])>1e-9};proposal=[]
for r in roads:
 if not any(str(n) in changed for n in r['nodeIds']):continue
 result=[nodeResult.get(str(n),h) for n,h in zip(r['nodeIds'],r['heights'])];slopes=[abs(b-a)/max(1e-9,math.dist(p,q)) for a,b,p,q in zip(result,result[1:],r['points'],r['points'][1:])];originalSlopes=[abs(b-a)/max(1e-9,math.dist(p,q)) for a,b,p,q in zip(r['heights'],r['heights'][1:],r['points'],r['points'][1:])];ends=[]
 for i in [0,len(r['nodeIds'])-1]:
  n=str(r['nodeIds'][i]);ends.append({'nodeId':n,'originalHeight':r['heights'][i],'resultHeight':result[i],'allAdjacentSourceRoads':[{'sourceRoadId':rid,'nodeIndex':j,'oldHeight':h,'proposedHeight':nodeResult.get(n,h),'mustUpdate':n in changed} for rid,j,h in occ[n]],'sameNodeHeightDifferenceAfter':0 if n in nodeResult else max(v[2] for v in occ[n])-min(v[2] for v in occ[n])})
 proposal.append({'sourceRoadId':r['id'],'name':r.get('name'),'nodeIds':r['nodeIds'],'points':r['points'],'widthUnchangedGame':r['width'],'originalHeights':r['heights'],'resultHeights':result,'originalHeightBasis':r['heightBasis'],'basis':'estimated reconstruction: reported structural form + explicitly revised estimated rigid main core; harmonic original-source-node ramps, exact original heights at bounded graph frontier; not DSM or surveyed elevations','coreConstraintNodes':[str(n) for n in r['nodeIds'] if str(n) in seeds],'maxGradientBefore':max(originalSlopes,default=0),'maxGradientAfter':max(slopes,default=0),'endCompatibility':ends})
report={'kind':'independent estimated source-node height candidate','sourceRoadLevelsSha256':sha(rpath),'rawSourceGraphChanged':False,'newGraphNodes':0,'roadWidthsChanged':False,'approachGraphRadiusGameByBridge':radii,'solver':'Dirichlet weighted graph Laplacian with 1/original edge length conductance; core pin target, outer original node heights pin; actual original node connectivity only','iterations':iteration+1,'finalIterationDifferenceGame':error,'unknownHeightStatus':'estimated, not measured','seeds':seedRows,'seedConflicts':conflicts,'rawNodeDisagreements':rawDisagreements,'affectedRoadCount':len(proposal),'changedNodeCount':len(changed),'boundaryNodeCount':len(boundary),'maxGradientAfter':max(r['maxGradientAfter'] for r in proposal),'rows':proposal,'pending':['Graph radius is game adaptation; classify approach span/grade suitability and deck ownership before integration','Neighbour city assets still carry old heights until root rebuild','Actual driving and actor permissions pending']};(P/'source-height-proposal.json').write_text(json.dumps(report,separators=(',',':')));print({k:report[k] for k in ['iterations','affectedRoadCount','changedNodeCount','boundaryNodeCount','maxGradientAfter']});print('raw disagreement',len(rawDisagreements),'seed conflicts',len(conflicts))
