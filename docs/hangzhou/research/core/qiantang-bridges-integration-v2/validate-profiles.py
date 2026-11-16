from pathlib import Path
import json,hashlib,math,collections
import numpy as np
from shapely.geometry import Point,Polygon,LineString
from shapely import union_all
P=Path(__file__).resolve().parent;ROOT=P.parents[4];proposal=json.loads((P/'source-height-proposal.json').read_text());spec=json.loads((P/'spec.json').read_text());original=json.loads((ROOT/'artifacts/cities/hangzhou/render-input-v7/geography/road-levels.json').read_text())['roads'];rows={r['sourceRoadId']:r for r in proposal['rows']};domains=json.loads((P/'deck-ownership.json').read_text())['domains'];checks=[]
def check(name,ok,value=None):checks.append({'name':name,'pass':bool(ok),'value':value})
changed=[];allNode=collections.defaultdict(list);actual=[]
for r in original:
 copy={**r};row=rows.get(r['id'])
 if row:
  check(r['id']+' exact source identity/points/original heights/width',row['nodeIds']==r['nodeIds'] and row['points']==r['points'] and row['originalHeights']==r['heights'] and row['widthUnchangedGame']==r['width']);copy['heights']=row['resultHeights'];changed.append(r['id'])
 for n,h in zip(r['nodeIds'],copy['heights']):allNode[str(n)].append(h)
 actual.append(copy)
nodeErrors=[max(v)-min(v) for v in allNode.values()];check('all original shared-node heights remain exactly continuous',max(nodeErrors)==0,max(nodeErrors));check('no contradictory pinned decks',not proposal['seedConflicts']);check('all raw source shared nodes agreed before proposal',not proposal['rawNodeDisagreements']);check('no new roads/nodes or altered source width',proposal['rawSourceGraphChanged'] is False and proposal['newGraphNodes']==0 and proposal['roadWidthsChanged'] is False)
byid={r['id']:r for r in actual};samples=[];summary=[];maxCoreDelta=0
for bridgeId,b in spec['bridges'].items():
 for rec in b['sourceRoads']:
  if not rec.get('existsInRuntime'):continue
  road=byid[rec['sourceRoadId']];st=rec['stationM'];support=union_all([Polygon(d['polygonGame']) for d in domains if d['bridgeId']==bridgeId and d['deck']==rec['deck']]);half=b['mainIntervalM'][1];rr=[]
  for i,(a,c) in enumerate(zip(road['points'],road['points'][1:])):
   count=max(1,math.ceil(math.dist(a,c)/1.))
   for j in range(count+1):
    t=j/count;station=st[i]*(1-t)+st[i+1]*t
    if abs(station)>half+1e-8:continue
    xy=np.array(a)*(1-t)+np.array(c)*t;h=road['heights'][i]*(1-t)+road['heights'][i+1]*t;delta=h-rec['coreTargetGame'];maxCoreDelta=max(maxCoreDelta,abs(delta));point=Point(xy);distance=support.distance(point);inside=support.covers(point);clearance=support.boundary.distance(point) if inside else -distance
    row={'bridgeId':bridgeId,'sourceRoadId':road['id'],'deck':rec['deck'],'sourceSegment':i,'t':t,'stationM':station,'point':xy.tolist(),'height':h,'target':rec['coreTargetGame'],'heightDifference':delta,'insideReportedSupport':inside,'supportSignedClearanceGame':clearance,'sourceStripHalfWidthGame':road['width']/2};rr.append(row);samples.append(row)
  summary.append({'bridgeId':bridgeId,'sourceRoadId':road['id'],'coreSamples':len(rr),'outsideSupport':sum(not r['insideReportedSupport'] for r in rr),'fullSourceStripOutsideReportedSupport':sum(r['supportSignedClearanceGame']<r['sourceStripHalfWidthGame'] for r in rr),'minSignedClearanceGame':min((r['supportSignedClearanceGame'] for r in rr),default=None),'maxHeightDifference':max((abs(r['heightDifference']) for r in rr),default=0)})
check('all source segment interpolation across finite main core matches rigid model ordinate',maxCoreDelta<1e-10,maxCoreDelta)
zh=[r for r in proposal['rows'] if r['sourceRoadId'] in ['way/306360721#0','way/589558021#0','way/306360739#0']];check('Zhijiang original named bridge source grade below reported .0298',all(r['maxGradientAfter']<=.0298 for r in zh),[(r['sourceRoadId'],r['maxGradientAfter']) for r in zh]);check('source-gradient vertical change at original max car dt below .7',proposal['maxGradientAfter']*53*.05<.7,proposal['maxGradientAfter']*53*.05);check('source-gradient vertical change at original max run dt below .48',proposal['maxGradientAfter']*4.2*.05<.48,proposal['maxGradientAfter']*4.2*.05)
(P/'candidate-road-levels.json').write_text(json.dumps({'cityId':'hangzhou','roads':actual},separators=(',',':')));(P/'core-samples.json').write_text(json.dumps(samples,separators=(',',':')));report={'scope':'exact source node/edge continuity, finite main-span interpolation and actual support domains; not runtime or real driving','checks':checks,'passed':sum(c['pass'] for c in checks),'failed':sum(not c['pass'] for c in checks),'sampleCount':len(samples),'supportSummary':summary,'supportFailureIsNotSuppressed':True,'blockers':['source strip entire width cannot be declared within reported deck when row signed clearance is too small; no source width was silently changed','Fuxing near-end lower way support gaps remain','Actor paths and retained railings/arch members require actual CPU collision and browser checks']};(P/'validation-profiles.json').write_text(json.dumps(report,indent=2));print({k:report[k] for k in ['passed','failed','sampleCount']});print([r for r in summary if r['outsideSupport']]);print([c for c in checks if not c['pass']])
