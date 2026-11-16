"""Select bounded continuous shoreline candidates from fixed source; no model output."""
from pathlib import Path
import json,math,hashlib
from shapely.geometry import shape,Polygon,Point,LineString,mapping
from shapely.ops import substring
ROOT=Path(__file__).resolve().parents[6];OUT=Path(__file__).resolve().parent
c=json.loads((ROOT/'artifacts/cities/hangzhou/water-data-v3/city.json').read_text());m=c['meta'];w=next(w for w in c['water'] if w['id']=='relation/8227206');water=Polygon(w['rings'][0],w['rings'][1:]);boundary=LineString(water.exterior.coords)
features=lambda name:json.loads((OUT/name).read_text())['features']
structures=features('structures.geojson');paths=features('riverside-paths.geojson');members=features('river-boundary-members.geojson')
def unproject(p):return [m['originWGS84'][0]+p[0]/(m['eastMetresPerDegree']*.6),m['originWGS84'][1]+p[1]/(m['northMetresPerDegree']*.6)]
def classification(tags):
 if tags.get('barrier')=='retaining_wall':return 'explicit-source-retaining-wall'
 if tags.get('man_made') in ['embankment','dyke','seawall','quay']:return 'explicit-source-bank-structure'
 if tags.get('natural')=='cliff':return 'source-natural-cliff-not-manmade-wall'
 if tags.get('waterway') in ['dam','weir']:return 'source-water-control-not-generic-shore-wall'
 if tags.get('barrier') in ['wall','city_wall']:return 'source-wall-function-as-bank-unconfirmed'
 if tags.get('embankment'):return 'raised-transport-earthwork-not-shore-wall-proof'
 return 'other-mapped-waterfront-structure'
anchors=[('qianjiang-city-balcony',[3324.221245460762,-1978.9980965522925]),('olympic-big-lotus',[4005.567432034517,-2814.6957618141437]),('binjiang-park',[2627.204642643804,-3870.1813782132194])];proposals=[]
for ident,xy in anchors:
 s=boundary.project(Point(xy));lo=max(0,s-300);hi=min(boundary.length,s+300);part=substring(boundary,lo,hi);near=[];sources=[];nearpaths=[]
 for f in structures:
  line=shape(f['geometryGame']);d=line.distance(part)
  if d<=60:near.append({'id':f['id'],'classification':classification(f['properties']['tags']),'distanceGame':d,'parallelWithin1GameLength':line.intersection(part.buffer(1)).length,'tags':f['properties']['tags'],'geometry':f['geometry'],'geometryGame':f['geometryGame'],'sourceVersion':f['properties']['version'],'sourceTimestamp':f['properties']['timestamp']})
 for f in members:
  line=shape(f['geometryGame']);length=part.intersection(line.buffer(1e-6)).length
  if length>1e-4:sources.append({'id':f['id'],'coverageLengthGame':length,'sourceVersion':f['properties']['version'],'sourceTimestamp':f['properties']['timestamp'],'sourceTags':f['properties']['tags'],'sourceNodeIds':f['properties']['nodeIds'],'geometry':f['geometry'],'geometryGame':f['geometryGame']})
 for f in paths:
  line=shape(f['geometryGame']);d=line.distance(part);t=f['properties']['tags']
  if d<=35 and t.get('access') not in ['private','no'] and t.get('foot')!='no':nearpaths.append({'id':f['id'],'distanceGame':d,'within35GameLength':line.intersection(part.buffer(35)).length,'tags':t,'sourceNodeIds':f['properties']['nodeIds'],'geometry':f['geometry'],'geometryGame':f['geometryGame']})
 proposals.append({'id':ident,'anchorGame':xy,'anchorWGS84':unproject(xy),'anchorToBankGame':Point(xy).distance(part),'waterSourceId':w['id'],'waterSourcePartIndex':w['sourcePartIndex'],'provisionalWaterHeightGame':w['height'],'boundaryStationGame':[lo,hi],'lengthGame':part.length,'geometryGame':mapping(part),'geometry':mapping(LineString(list(map(unproject,part.coords)))),'bankMemberSources':sources,'nearbyStructures':sorted(near,key=lambda r:r['distanceGame']),'nearbyPublicPaths':sorted(nearpaths,key=lambda r:r['distanceGame']),'boundaryCoincidenceMaxDistanceGame':part.hausdorff_distance(boundary.intersection(part.buffer(1e-7))),'status':'source-bound continuous bank proposal; wall type/height not implied by wet-dry outline'})
wall=next(f for f in structures if f['id']=='way/157906999');start,end=15,28;coordinates=wall['geometryGame']['coordinates'][start:end+1];part=LineString(coordinates);nodeids=wall['properties']['nodeIds'][start:end+1];water_member=next(f for f in members if f['id']=='way/638705820');nearpaths=[]
for f in paths:
 line=shape(f['geometryGame']);d=line.distance(part);t=f['properties']['tags']
 if d<=35 and t.get('access') not in ['private','no'] and t.get('foot')!='no':nearpaths.append({'id':f['id'],'distanceGame':d,'within35GameLength':line.intersection(part.buffer(35)).length,'tags':t,'geometry':f['geometry'],'geometryGame':f['geometryGame'],'sourceNodeIds':f['properties']['nodeIds']})
side=[];worst=0.
for i,(a,b) in enumerate(zip(coordinates,coordinates[1:])):
 line=LineString([a,b]);mid=line.interpolate(.5,normalized=True);dx=b[0]-a[0];dz=b[1]-a[1];length=line.length;n=(-dz/length,dx/length);probes=[[mid.x+n[0]*s*.5,mid.y+n[1]*s*.5] for s in [1,-1]];wet_side=[water.contains(Point(q)) for q in probes];error=max(line.interpolate(k/20,normalized=True).distance(boundary) for k in range(21));worst=max(worst,error);side.append({'sourceSegmentIndex':start+i,'sourceNodeIds':nodeids[i:i+2],'max21ProbeBoundaryDistanceGame':error,'leftNormalGame':n,'leftProbeWet':wet_side[0],'rightProbeWet':wet_side[1],'drySide':'right' if wet_side==[True,False] else 'left' if wet_side==[False,True] else 'ambiguous'})
proposals.insert(0,{'id':'binjiang-source-retaining-wall','priority':'first structural wall candidate','sourceId':wall['id'],'sourceVersion':wall['properties']['version'],'sourceTimestamp':wall['properties']['timestamp'],'sourceTags':wall['properties']['tags'],'sourceNodeIndexInclusive':[start,end],'sourceSegmentIndexInclusive':[start,end-1],'sourceNodeIds':nodeids,'allSelectedNodesSharedWithRiverBoundaryMember':all(n in water_member['properties']['nodeIds'] for n in nodeids),'riverBoundaryMemberId':water_member['id'],'waterSourceId':w['id'],'waterSourcePartIndex':w['sourcePartIndex'],'provisionalWaterHeightGame':w['height'],'lengthGame':part.length,'geometryGame':mapping(part),'geometry':mapping(LineString(wall['geometry']['coordinates'][start:end+1])),'boundaryCoincidenceMaxSampledDistanceGame':worst,'segmentEvidence':side,'nearbyPublicPaths':sorted(nearpaths,key=lambda r:r['distanceGame']),'bankMemberSources':[{'id':water_member['id'],'sourceVersion':water_member['properties']['version'],'sourceTimestamp':water_member['properties']['timestamp']}],'nearbyStructures':[{'id':wall['id'],'classification':'explicit-source-retaining-wall','distanceGame':0,'parallelWithin1GameLength':part.length}],'heightStatus':'unknown; any model top/bottom must be explicitly estimated using current terrain and local provisional water reference, not tag-derived measurement','materialStatus':'unknown; do not infer concrete from retaining_wall','status':'source-tagged continuous structural footprint candidate, not surveyed or current-condition verification'})
(OUT/'proposals.json').write_text(json.dumps({'sourceSnapshot':'2026-10-11','coordinateUnits':'WGS84 and game EN .60 applied once','selectionScopeGame':{'structuralWall':'source node indices15..28','otherBankWindows':600},'selectionIsGameScopeNotSurveyBoundary':True,'proposals':proposals},ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{'id':p['id'],'lengthGame':p['lengthGame'],'memberSources':[s['id'] for s in p['bankMemberSources']],'structures':[(s['id'],s['classification'],round(s['distanceGame'],3),round(s['parallelWithin1GameLength'],3)) for s in p['nearbyStructures']],'paths':[(s['id'],round(s['distanceGame'],3)) for s in p['nearbyPublicPaths']]} for p in proposals],ensure_ascii=False,indent=2))
