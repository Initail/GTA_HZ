"""Read-only transverse feasibility proof using frozen source lines and deck widths."""
from pathlib import Path
import json,math,hashlib,html
import numpy as np
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union
P=Path(__file__).resolve().parent;S=P.parent;R=S.parents[4];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();s=json.loads((S/'spec.json').read_text());b=s['bridges']['fuxing-bridge'];audit=json.loads((S/'source-road-audit.json').read_text());roads=[r for r in audit['rows'] if r['bridgeId']=='fuxing-bridge' and r['deck']=='lower'];full=json.loads((R/s['originalSpec']).read_text());raw=next(v for v in full['bridges'] if v['id']=='fuxing-bridge');tags={r['id']:r['tags'] for r in raw['roads']};a=b['axisRadiansEastCCW'];u=np.array([math.cos(a),math.sin(a)]);n=np.array([-u[1],u[0]]);centers=np.array(json.loads((S/'deck-ownership.json').read_text())['domains'][0]['polygonGame']);sys=None
# Recover exact reviewed centre through original source station/lateral decomposition.
q=roads[0];center=np.array(q['points'][0])-.6*(q['stationM'][0]*u+q['lateralM'][0]*n)
domains=[d for d in json.loads((S/'deck-ownership.json').read_text())['domains'] if d['bridgeId']=='fuxing-bridge' and d['deck']=='lower'];polys=[Polygon(np.stack([(np.array(d['polygonGame'])-center)@u/.6,(np.array(d['polygonGame'])-center)@n/.6],axis=1)) for d in domains];domain=unary_union(polys);samples=[];margin=1.15/.6;radius=.045

def lateralAt(r,station):
 out=[]
 for i,(a,b) in enumerate(zip(r['stationM'],r['stationM'][1:])):
  if min(a,b)-1e-9<=station<=max(a,b)+1e-9 and abs(b-a)>1e-10:
   t=(station-a)/(b-a);value=r['lateralM'][i]+t*(r['lateralM'][i+1]-r['lateralM'][i]);out.append({'segment':i,'t':t,'lateralM':value,'nodeIds':[r['nodeIds'][i],r['nodeIds'][i+1]]})
 # Duplicate exact shared endpoint is one location, not separate transport layer.
 uniq=[]
 for r in out:
  if not any(abs(r['lateralM']-x['lateralM'])<1e-8 for x in uniq):uniq.append(r)
 return uniq
for station in range(-687,688):
 cross=domain.intersection(LineString([(station,-100),(station,100)]));bounds=cross.bounds
 if not bounds:continue
 hits={r['sourceRoadId']:lateralAt(r,station) for r in roads};flat=[h['lateralM'] for hs in hits.values() for h in hs]
 if any(len(h)!=1 for h in hits.values()):continue
 lo,hi=min(flat),max(flat);width=bounds[3]-bounds[1];required=hi-lo+2*(margin+radius);samples.append({'stationM':station,'supportLateralM':[bounds[1],bounds[3]],'supportWidthM':width,'sourceLaterals':hits,'outerCentreSeparationM':hi-lo,'anyRigidCenterRequiredWidthM':required,'minimumOuterWallMarginM':margin+radius,'bestPossibleUniformAxisClearanceDeficitM':max(0,required-width),'sourceStripMinMaxM':[min(hs[0]['lateralM']-next(r for r in roads if r['sourceRoadId']==id)['widthGame']/.6/2 for id,hs in hits.items()),max(hs[0]['lateralM']+next(r for r in roads if r['sourceRoadId']==id)['widthGame']/.6/2 for id,hs in hits.items())]})
conflict=[r for r in samples if r['bestPossibleUniformAxisClearanceDeficitM']>1e-7];central=[r for r in samples if abs(r['stationM'])<=500];summary={'samples':len(samples),'stepPhysicalM':1,'axisInvariantConflictStations':len(conflict),'maxRigidCenterWidthDeficitM':max(r['bestPossibleUniformAxisClearanceDeficitM'] for r in samples),'centralAbsStationLe500':{'samples':len(central),'conflictStations':sum(r['bestPossibleUniformAxisClearanceDeficitM']>1e-7 for r in central),'maxDeficitM':max(r['bestPossibleUniformAxisClearanceDeficitM'] for r in central)},'narrowSupportWidthRangeM':[min(r['supportWidthM'] for r in samples),max(r['supportWidthM'] for r in samples)],'requiredWidthRangeM':[min(r['anyRigidCenterRequiredWidthM'] for r in samples),max(r['anyRigidCenterRequiredWidthM'] for r in samples)]};roadsummary=[]
for r in roads:
 vals=[h[r['sourceRoadId']][0]['lateralM'] for h in [v['sourceLaterals'] for v in central]];t=tags[r['sourceWayId']];roadsummary.append({'sourceRoadId':r['sourceRoadId'],'sourceWayId':r['sourceWayId'],'tags':t,'runtimeWidthGame':r['widthGame'],'runtimeWidthPhysicalM':r['widthGame']/.6,'hasSourceWidthOrLaneEvidence':any(k in t for k in ['width','lanes','lanes:forward','lanes:backward','sidewalk','cycleway']),'centralLateralM':{'min':min(vals),'median':float(np.median(vals)),'max':max(vals)},'purpose':'source primary transport way; oneway tag maps separate external one-way lines and central bidirectional line, not explicit footpath/road edge'})
report={'kind':'read-only axis-invariant lower bridge transverse feasibility proof','inputs':{str(p.relative_to(R)):sha(p) for p in [S/'spec.json',S/'source-road-audit.json',S/'deck-ownership.json',R/s['originalSpec']]},'axisCenterGame':center.tolist(),'summary':summary,'roads':roadsummary,'originalActorWallMarginGame':1.15,'outerRailRadiusPhysicalM':.045,'proof':'At fixed source longitudinal station, width needed for BOTH outer source centre points to clear preserved external rails is max(lateral)-min(lateral)+2*(1.15/.6+.045). Any rigid lateral translation leaves separation unchanged. If this exceeds actual reported-width support, shifting only axis cannot clear both outer lines. This is an exact necessary condition for the original player collision, not a surveyed real-road width. Bank/arch/internal-rail constraints can only add blockers.','samples':samples,'notChanged':['frozen source coordinates or node graph','reported widths','actual model/rails','actor margins','runtime/source road widths'],'blockers':['No source width/lanes/sidewalk tags establish correct external car lane centres','No primary transverse design dimension/location survey justifies widening26.4m small span','Three lower strips carry class-default10m widths, not measured three independent10m carriageways','Primary publication supports central reserved transport plus side bus/slow routes but not exact current per-way interpretation','Reported190m/85m structural station sequence remains estimated placement; bank curvature/cantilever/viewing-platform ownership unknown']};(P/'cross-section-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(summary);print(roadsummary)
# Standalone exact-data plot; no claimed real image or gameplay screenshot.
W,H=1200,470;X=lambda s:55+(s+688)/1376*1100;Y=lambda y:240-y*8
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/><g font-family="sans-serif" font-size="13">', '<text x="55" y="25">Fuxing lower deck: fixed source centrelines vs reported support (physical metres)</text>']
for y in range(-20,21,5):svg +=[f'<line x1="55" x2="1155" y1="{Y(y)}" y2="{Y(y)}" stroke="#ddd"/><text x="15" y="{Y(y)+4}">{y}</text>']
for z in [-600,-400,-200,0,200,400,600]:svg +=[f'<line x1="{X(z)}" x2="{X(z)}" y1="65" y2="415" stroke="#eee"/><text x="{X(z)-12}" y="435">{z}</text>']
for sign in [0,1]:
 pts=' '.join(f'{X(r["stationM"]):.2f},{Y(r["supportLateralM"][sign]):.2f}' for r in samples);svg +=[f'<polyline points="{pts}" fill="none" stroke="#222" stroke-width="2"/>']
for i,r in enumerate(roads):
 color=['#b42318','#315de2','#047857'][i];pts=' '.join(f'{X(v["stationM"]):.2f},{Y(v["sourceLaterals"][r["sourceRoadId"]][0]["lateralM"]):.2f}' for v in samples);svg +=[f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.6"/><text x="{55+i*330}" y="55" fill="{color}">{html.escape(r["sourceRoadId"])} (original source)</text>']
svg+=['<text x="55" y="463">Black: model support edge. Red/blue/green: immutable source lines. No axis or width changes applied.</text></g></svg>'];(P/'source-cross-section.svg').write_text(''.join(svg))
