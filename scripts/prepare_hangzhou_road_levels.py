"""Source-node-bound road elevations, with explicitly estimated arcade clearances.

No geometric crossing becomes a junction. Heights/ramps are an intermediate
physical surface proposal, not measured bridge/tunnel profiles or driving QA.
"""
from __future__ import annotations
import argparse,hashlib,heapq,json,math
from pathlib import Path
import numpy as np
from city_config import ROOT,load_city

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def road_tier(road):
 try:grade=float(road.get('grade','0'))
 except ValueError:raise ValueError('Unknown OSM road layer: '+road['id'])
 if not math.isfinite(grade):raise ValueError('Non-finite road layer')
 if road.get('tunnel','no')!='no':return min(-1,grade)
 if road.get('bridge','no')!='no':return max(1,grade)
 return grade

def shared_node_offsets(roads,clearance_game=3.6,max_ramp_gradient=.06):
 """Limit nominal offsets by distance to source-identity tier transitions."""
 tiers={};adj={};points={}
 for road in roads:
  tier=road_tier(road)
  for ref,p in zip(road['nodeIds'],road['points']):
   key=str(ref);tiers.setdefault(key,set()).add(tier);adj.setdefault(key,{})
   if key in points and math.dist(points[key],p)>.02:raise ValueError('Inconsistent shared source node '+key)
   points[key]=p
  for a,b,p,q in zip(road['nodeIds'],road['nodeIds'][1:],road['points'],road['points'][1:]):
   a,b=str(a),str(b);d=math.dist(p,q)
   if tier>0 or tier<0:
    adj[a][b]=min(adj[a].get(b,math.inf),d);adj[b][a]=min(adj[b].get(a,math.inf),d)
 def limit(sign):
  # Every target starts as its declared nominal tier; the shortest admissible
  # rise from any lower tier replaces it. Source-shared endpoints meet exactly.
  cap={k:(min(v) if sign>0 else -max(v))*clearance_game for k,v in tiers.items()}
  queue=[(h,k) for k,h in cap.items()];heapq.heapify(queue)
  while queue:
   h,k=heapq.heappop(queue)
   if h!=cap[k]:continue
   for other,d in adj[k].items():
    if not any(sign*t>0 for t in tiers[other]):continue
    new=h+d*max_ramp_gradient
    if new<cap[other]:cap[other]=new;heapq.heappush(queue,(new,other))
  return cap
 positive,negative=limit(1),limit(-1)
 offsets={k:(min(0,negative[k])*-1 if max(v)<0 else max(0,positive[k]) if min(v)>0 else 0) for k,v in tiers.items()}
 # Negative tunnel ramps approach the shared ground endpoint from below.
 for k,v in tiers.items():
  if max(v)<0:offsets[k]=-max(0,negative[k])
 return offsets,tiers

def smooth_source_ground(roads,initial,max_gradient):
 """Balanced upper/lower Lipschitz envelopes along real source road edges.

 This is road earthwork adaptation of a biased DSM, not a measured DTM.
 Disconnected and overlapping source nodes remain independent.
 """
 if not math.isfinite(max_gradient) or max_gradient<=0:raise ValueError('Positive estimated grade limit required')
 adj={str(k):{} for k in initial}
 for road in roads:
  for a,b,p,q in zip(road['nodeIds'],road['nodeIds'][1:],road['points'],road['points'][1:]):
   a,b=str(a),str(b);d=math.dist(p,q)*max_gradient
   adj[a][b]=min(adj[a].get(b,math.inf),d);adj[b][a]=min(adj[b].get(a,math.inf),d)
 def envelope(sign):
  result={str(k):float(v)*sign for k,v in initial.items()};queue=[(v,k) for k,v in result.items()];heapq.heapify(queue)
  while queue:
   value,key=heapq.heappop(queue)
   if value!=result[key]:continue
   for other,cap in adj[key].items():
    estimate=value+cap
    if estimate<result[other]:result[other]=estimate;heapq.heappush(queue,(estimate,other))
  return result
 low,negative_high=envelope(1),envelope(-1)
 return {k:(low[k]-negative_high[k])/2 for k in low}

def prepare(source,terrain,output):
 source,terrain,output=map(lambda p:Path(p).resolve(),[source,terrain,output])
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
 city=json.loads((source/'city.json').read_text());manifest=json.loads((terrain/'manifest.json').read_text())
 if city['meta']['cityId']!='hangzhou' or manifest['cityId']!='hangzhou':raise ValueError('Hangzhou inputs required')
 name='ground-estimate-egm2008-metres.bin';record=manifest['files'][name]
 if digest(terrain/name)!=record['sha256']:raise ValueError('Changed DSM grid')
 if manifest['units']!='real metres above EGM2008; not yet game-scaled':raise ValueError('Unexpected source elevation units')
 g=manifest['grid'];heights=np.fromfile(terrain/name,dtype='<f4').reshape(g['rows'],g['columns'])
 profile=load_city('hangzhou');scale=profile['geography']['scale'];policy=profile['roadSurfaces']
 def base(p):
  u=(p[0]-g['x0'])/g['step'];v=(p[1]-g['z0'])/g['step'];i=math.floor(u);j=math.floor(v)
  if not 0<=i<g['columns']-1 or not 0<=j<g['rows']-1:raise ValueError('Road outside DSM grid')
  a,b,d,c=map(float,[heights[j,i],heights[j,i+1],heights[j+1,i],heights[j+1,i+1]])
  fx,fz=u-i,v-j
  return ((a+(b-a)*fx+(d-a)*fz) if fx+fz<=1 else (c+(d-c)*(1-fx)+(b-c)*(1-fz)))*scale
 offsets,tiers=shared_node_offsets(city['roads'],policy['defaultTierClearanceRealMetres']*scale,policy['maxOffsetRampGradient'])
 raw_ground={str(ref):base(p) for road in city['roads'] for ref,p in zip(road['nodeIds'],road['points'])}
 ground=smooth_source_ground(city['roads'],raw_ground,policy['maxGroundGradient'])
 node_heights={};surfaces=[];maximum_slope=0
 for road in city['roads']:
  values=[]
  for ref,p in zip(road['nodeIds'],road['points']):
   key=str(ref);y=ground[key]+offsets[key];node_heights[key]=y;values.append(y)
  slopes=[abs(b-a)/max(.001,math.dist(p,q)) for a,b,p,q in zip(values,values[1:],road['points'],road['points'][1:])]
  maximum_slope=max(maximum_slope,max(slopes,default=0))
  surfaces.append({'id':road['id'],'name':road['name'],'points':road['points'],'nodeIds':road['nodeIds'],
   'width':road['width'],'grade':road['grade'],'bridge':road['bridge'],'tunnel':road['tunnel'],'heights':values,
   'groundHeights':[ground[str(ref)] for ref in road['nodeIds']],
   'tier':road_tier(road),'maxGradient':max(slopes,default=0),'heightBasis':'DSM ground estimate smoothed along source edges + estimated source-tier clearance/ramp'})
 output.mkdir(parents=True,exist_ok=True)
 payload={'schemaVersion':1,'cityId':'hangzhou','units':'game metres; scale already applied once','roads':surfaces,
  'heightPolicy':{'nominalTierClearanceRealMetres':policy['defaultTierClearanceRealMetres'],'basis':policy['basis'],
   'scale':scale,'maxOffsetRampGradient':policy['maxOffsetRampGradient'],'groundGradientLimit':policy['maxGroundGradient'],'groundSmoothing':policy['groundSmoothing'],'unknownTunnelPortals':True},
  'inputs':{'citySha256':digest(source/'city.json'),'terrainManifestSha256':digest(terrain/'manifest.json'),'terrainGridSha256':record['sha256']}}
 (output/'road-levels.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')))
 navigation=json.loads((source/'navigation.json').read_text())
 navigation['nodeHeights']=[node_heights[str(ref)] for ref in navigation['sourceNodeIds']]
 navigation['meta']['heightStatus']='DSM filtered ground plus estimated tiers; physical acceptance pending'
 navigation['meta']['roadLevelsSha256']=digest(output/'road-levels.json')
 (output/'navigation.json').write_text(json.dumps(navigation,separators=(',',':')))
 report={'kind':'estimated-source-bound-physical-surface-candidate','roadCount':len(surfaces),'nodeCount':len(node_heights),
  'groundSmoothing':{'method':policy['groundSmoothing'],'maxGradient':policy['maxGroundGradient'],'maximumAbsoluteChangeGame':max(abs(ground[k]-raw_ground[k]) for k in ground),
   'changedNodesAbovePoint01Game':sum(abs(ground[k]-raw_ground[k])>.01 for k in ground),'measuredGroundClaim':False},
  'sharedTierTransitionCount':sum(len(v)>1 for v in tiers.values()),'maximumTotalGradient':maximum_slope,
  'roadsAbove20PercentGradient':[s['id'] for s in surfaces if s['maxGradient']>.20],
  'roadLevelsSha256':digest(output/'road-levels.json'),'navigationSha256':digest(output/'navigation.json'),'sourceIdentityJunctionsOnly':True,
  'pending':['measured bridge/tunnel profiles','steep road smoothing/earthworks','mesh geometry','water levels and clearance',
    'stacked surface actor selection','collision/traffic/autopilot','actual driving']}
 (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--terrain',required=True);p.add_argument('--output',required=True)
 a=p.parse_args();prepare(a.input,a.terrain,a.output)
