"""Estimated, non-activated height options; source nodes and XY are unchanged."""
from pathlib import Path
import json,math,heapq,collections,hashlib
import numpy as np
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
city=read(ROOT/'artifacts/cities/hangzhou/render-input-v7/city.json');audit=read(OUT/'source-graph-and-clearance.json');rs={r['id']:r for r in city['roads']};adj=collections.defaultdict(list);cum={}
for r in rs.values():
 s=[0.]
 for i,(a,b) in enumerate(zip(r['points'],r['points'][1:])):
  d=math.dist(a,b);s.append(s[-1]+d);u,v=r['nodeIds'][i:i+2];adj[u].append((v,d));adj[v].append((u,d))
 cum[r['id']]=s
decay=.04;results=[]
for scenario,include_service in [('confirmed-tunnel-only',False),('service-under-lower-floor-hypothesis',True)]:
 seeds=collections.defaultdict(list);delta={};heap=[]
 for r in audit:
  if r['id']=='way/336828925#0' and not include_service:continue
  for p in r['occupiedCrossSections']:
   drop=max(0,p['rawEstimatedRoadY']-p['conservativeTargetYAt3point6Clearance']);seeds[r['id']].append((p['station'],drop))
   s=cum[r['id']];j=min(len(s)-2,max(0,int(np.searchsorted(s,p['station'],side='right')-1)))
   for i in [j,j+1]:
    n=r['sourceRoad']['nodeIds'][i];d=drop-decay*abs(s[i]-p['station'])
    if d>delta.get(n,0):delta[n]=d;heapq.heappush(heap,(-d,n))
 while heap:
  negative,n=heapq.heappop(heap);d=-negative
  if d<delta.get(n,0)-1e-12:continue
  for v,l in adj[n]:
   other=d-decay*l
   if other>delta.get(v,0)+1e-12:delta[v]=other;heapq.heappush(heap,(-other,v))
 affected=[];junctions=collections.defaultdict(list);clearance=[]
 for r in rs.values():
  if not any(delta.get(n,0)>1e-10 for n in r['nodeIds']) and r['id'] not in seeds:continue
  s=cum[r['id']];stations=sorted(set(s+list(np.arange(0,s[-1],1))+[p[0] for p in seeds[r['id']]]));profile=[]
  for station in stations:
   j=min(len(s)-2,max(0,int(np.searchsorted(s,station,side='right')-1)));u=(station-s[j])/(s[j+1]-s[j]);raw=r['heights'][j]*(1-u)+r['heights'][j+1]*u
   lowering=max(0,delta.get(r['nodeIds'][j],0)-decay*(station-s[j]),delta.get(r['nodeIds'][j+1],0)-decay*(s[j+1]-station),max((d-decay*abs(station-pos) for pos,d in seeds[r['id']]),default=0));xy=(np.array(r['points'][j])*(1-u)+np.array(r['points'][j+1])*u).tolist();profile.append({'station':float(station),'point':xy,'rawEstimatedY':float(raw),'loweringGame':float(lowering),'proposedEstimatedY':float(raw-lowering)})
  slopes=[abs(b['proposedEstimatedY']-a['proposedEstimatedY'])/(b['station']-a['station']) for a,b in zip(profile,profile[1:]) if b['station']-a['station']>1e-8]
  source_node_rows=[]
  for i,n in enumerate(r['nodeIds']):
   value=r['heights'][i]-delta.get(n,0);junctions[n].append((r['id'],value));source_node_rows.append({'nodeId':n,'station':s[i],'rawEstimatedY':r['heights'][i],'proposedEstimatedY':value})
  affected.append({'id':r['id'],'kind':r['kind'],'name':r['name'],'grade':r['grade'],'tunnel':r['tunnel'],'originalPointsAndNodeIdsUnchanged':True,'maximumLoweringGame':max(p['loweringGame'] for p in profile),'maximumSampledAbsoluteGrade':max(slopes,default=0),'sourceNodes':source_node_rows,'profile':profile})
 for r in audit:
  if r['id']=='way/336828925#0' and not include_service:continue
  ar=next((a for a in affected if a['id']==r['id']),None)
  if ar:
   by={round(p['station'],9):p for p in ar['profile']}
   for p in r['occupiedCrossSections']:clearance.append(p['minimumActualSlabBottomY']-by[round(p['station'],9)]['proposedEstimatedY'])
 mismatch=[{'nodeId':n,'values':a} for n,a in junctions.items() if max(y for _,y in a)-min(y for _,y in a)>1e-8]
 report={'scenario':scenario,'status':'non-activated estimated geometry option; service identity unresolved','sourceXYTopologyWidthsUnchanged':True,'clearanceGame':3.6,'clearanceBasis':'existing city default tier clearance 6 real metres times 0.60; conservative game adaptation, not surveyed tunnel headroom','loweringTransitionGradient':decay,'transitionRule':'max of nonnegative source-station lowering cones, propagated through every original shared node; same node receives same lowering','affectedRoads':len(affected),'affectedSourceNodes':len(delta),'maximumLoweringGame':max(a['maximumLoweringGame'] for a in affected),'maximumSampledAbsoluteGrade':max(a['maximumSampledAbsoluteGrade'] for a in affected),'minimumProposedActualSlabClearanceGame':min(clearance),'sourceNodeHeightMismatchCount':len(mismatch),'sourceNodeHeightMismatches':mismatch,'affectedRoadIds':[r['id'] for r in affected],'pending':['source role of service 336828925 cannot be inferred from geometric fit','road corridor terrain excavation and retaining walls, no generic grass over an open sunken road','reconcile road surfaces and navigation/collision/dynamic vehicle supports','independent actual source junction and longitudinal grade validation','full-width continuous ceiling, piers and shell clearance beyond <=.5g finite probes','real browser driving under complete tunnel and ramps']}
 save(scenario+'-profiles.json',{'report':report,'roads':affected});results.append(report)
save('options-summary.json',results);print(json.dumps(results,indent=2))
