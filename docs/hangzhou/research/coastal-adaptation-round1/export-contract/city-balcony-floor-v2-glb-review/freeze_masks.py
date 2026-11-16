from pathlib import Path
import json,hashlib,math
from shapely.geometry import shape,Polygon,Point,mapping
from shapely.ops import unary_union
ROOT=Path.cwd();OUT=Path(__file__).parent
c=json.loads((OUT/'ownership-contract.json').read_text());spec=json.loads((ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2/candidate-spec.json').read_text());p=spec['floorPlacement'];ax,az=p['anchorGame'];ca,sa=math.cos(p['axisRadiansEastCCW']),math.sin(p['axisRadiansEastCCW']);maskfiles=[]
def feature(ident,geom,props):return {'type':'Feature','id':ident,'geometry':geom,'properties':props}
def save(name,features):
 d={'type':'FeatureCollection','coordinateSystem':'Hangzhou game ENU metres; XY east/north and optional third coordinate up; WGS84-derived local projection scale0.60 already applied','sourceArtifactSha256':c['actualBalconyArtifactSha256'],'features':features};path=OUT/name;path.write_text(json.dumps(d,indent=2)+'\n');maskfiles.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
def poly(coords):return {'type':'Polygon','coordinates':[coords+[coords[0]] if coords[0]!=coords[-1] else coords]}
main=shape(c['mainEnvelopeGame']);clip=shape(c['clipEnvelopeGame'])
save('source-floor-support.geojson',[feature('main-envelope',c['mainEnvelopeGame'],{'sourceId':'relation/8718551','role':'source main building envelope, fingers excluded; source glass holes deliberately identified separately below','lowerFloorYGame':c['baseYGame'],'capTopYGame':c['capTopYGame']}),feature('public-lower-floor',c['publicLowerFootprintGame'],{'sourceId':'relation/8718551','role':'public lower source footprint; glass-part interiors not public floors','lowerFloorYGame':c['baseYGame'],'keepPublicVolumeOpen':True})])
save('hardware-allowance.geojson',[feature('clip-envelope',c['clipEnvelopeGame'],{'role':'source main envelope plus actual lower hardware extent','allowanceGame':c['hardwareClearanceGame'],'maxActualNearShoreHardwareExtensionGame':c['actualMaximumNearShoreStructureExtensionGame']}),feature('hardware-only-annulus',mapping(clip.difference(main)),{'role':'only added plan allowance; estimated game tolerance, not expanded source building footprint','allowanceGame':c['hardwareClearanceGame']})])
piers=[];pierShapes=[]
for q in c['sourcePiersToSubtract']:
 original=Polygon(q['polygonGame']);expanded=original.buffer(q['subtractHorizontalToleranceGame'],join_style=2);pierShapes.append(expanded)
 piers.extend([feature('pillar-'+str(q['collisionRecordIndex'])+'-source',mapping(original),{**q,'role':'actual module representative pier plan, estimated location'}),feature('pillar-'+str(q['collisionRecordIndex'])+'-subtract',mapping(expanded),{'role':'subtract this through stated Y range; close resulting shore solids','sourceCollisionRecordIndex':q['collisionRecordIndex'],'minYGame':q['minYGame'],'maxYGame':q['maxYGame'],'horizontalSerializationToleranceGame':q['subtractHorizontalToleranceGame']})])
save('pillar34-subtraction.geojson',piers)
save('shore-owned-mask.geojson',[feature('owned-original-strip',c['actualOwnedShoreStripGame'],{'role':'only this part of original .12g dry-side shoreline may receive cap; front/source water line unchanged'}),feature('capped-after-pier-subtraction',c['remainingCappedShoreAfterPierCutsGame'],{'role':'closed capped shore candidate footprint','topHeightRule':'min(original top, capTopYGame)','capTopYGame':c['capTopYGame'],'bottomYGame':c['originalShoreBottomYGame'],'waterYGame':c['originalWaterYGame'],'notYetBuiltOrAccepted':True})])
save('source-shore-stations.geojson',[feature('shore-interval-'+str(i),{'type':'LineString','coordinates':q['frontGeometryGame']},{'fromStationGame':q['fromStationGame'],'toStationGame':q['toStationGame'],'sourceLineSha256':c['shoreFrontSourceLineSha256'],'sourceShoreId':c['shoreSourceId'],'capTopYGame':c['capTopYGame'],'stationIsSourcePolylineArcLength':True}) for i,q in enumerate(c['sourceStationIntervals'])])
save('dry-main-terrain-cut.geojson',[feature('dry-main-terrain-cap',c['dryMainTerrainCutBoundaryGame'],{'heightRule':'min(oldTerrain, capTopYGame)','capTopYGame':c['capTopYGame'],'noNewWaterOrLandOrFill':True,'keepLowerPublicVolumeOpen':True,'originalWaterYGame':c['originalWaterYGame'],'actualDryTerrainSamplerChanged':False})])
for f in p['fingers']:
 def world(q):u,v=q[:2];return [ax+(u*ca-v*sa)*.6,az+(u*sa+v*ca)*.6]
 features=[feature(f['id']+'-exact-source-footprint',poly([world(q) for q in f['polygonUVMetres']]),{'sourceId':'relation/8718551','sourceUpperIndices':f['sourceIndices'],'role':'bounded exact source upper-only finger; no new lower floor','noGroundRaiseOrFill':True})]
 for i,t in enumerate(f['trianglesUVHMetres']):
  coords=[[*world(q),c['baseYGame']+q[2]*.6-c['lowerSlabThicknessGame']-c['hiddenClearanceGame']] for q in t]
  features.append(feature(f['id']+'-terrain-profile-'+str(i),poly(coords),{'heightRule':'min(oldTerrain, barycentric interpolated third coordinate on this triangle)','frozenUpperTriangleIndex':i,'slabThicknessGame':c['lowerSlabThicknessGame'],'hiddenClearanceGame':c['hiddenClearanceGame'],'exactSourceFootprintOnly':True,'sourceFloorPlacementId':p['id']}))
 save(f['id']+'-finger-terrain-cut.geojson',features)
# Existing actual triangle-intersection witnesses must lie either in planned height cap or pier subtraction.
actual=json.loads((OUT/'actual-four-shore-intersections.json').read_text());points=[q for sr in actual for part in sr['parts'] for hit in part['pairs'] for q in hit.get('pointsENU',[])];pierUnion=unary_union(pierShapes);miss=[]
for q in points:
 pt=Point(q[:2]);removedByCap=q[2]>c['capTopYGame']+1e-6 and clip.covers(pt);removedByPier=pierUnion.covers(pt) and any(r['minYGame']<=q[2]<=r['maxYGame'] for r in c['sourcePiersToSubtract'])
 if not (removedByCap or removedByPier):miss.append(q)
(OUT/'existing-witness-coverage.json').write_text(json.dumps({'existingActualIntersectionWitnessPoints':len(points),'uncoveredPoints':len(miss),'examples':miss[:20],'status':'existing point witnesses covered by proposed cap/pier domains; NOT regenerated-solid positive-volume or runtime acceptance'},indent=2)+'\n')
c['maskFiles']=maskfiles;c['existingWitnessPointsUncovered']=len(miss);(OUT/'ownership-contract.json').write_text(json.dumps(c,indent=2)+'\n')
print(json.dumps({'maskFiles':len(maskfiles),'existingWitnessPoints':len(points),'uncovered':len(miss),'stationIntervals':[(q['fromStationGame'],q['toStationGame']) for q in c['sourceStationIntervals']]},indent=2))
