import ast
from pathlib import Path
# Reuse independent read/sampler/parser definitions without running costly GLB review or mutating other folders.
source=Path(__file__).with_name('check.py').read_text().split('import ast,importlib.util')[0];exec(compile(source,str(Path(__file__).with_name('check.py')),'exec'),globals())
candidate='docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2/';s=read(candidate+'candidate-spec.json');p=s['floorPlacement'];coll=read(candidate+'collision-candidate.json');ax,az=p['anchorGame'];angle=p['axisRadiansEastCCW'];ca,sa=math.cos(angle),math.sin(angle);lower=p['baseYGame'];slab=.6*s['estimates']['levels']['value']['slabThicknessM'];clearance=.01;cap=lower-slab-clearance

def world(ring):return [(ax+(u*ca-v*sa)*.6,az+(u*sa+v*ca)*.6) for u,v in ring]
mainEnvelope=Polygon(world(s['lowerOuterUVMetres']));mainPublic=Polygon(world(s['lowerOuterUVMetres']),[world(r) for r in s['glazedFootprintsUVMetres']]);props=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/proposals.json')['proposals'];prop=next(r for r in props if r['id']=='qianjiang-city-balcony');line=LineString(prop['geometryGame']['coordinates'])
rec=next(r for r in m['objects'] if r['id']=='qianjiang-city-balcony');npz=np.load(bind(prep+rec['file']));ts=npz['land'];strip=shapely.union_all([Polygon(t[:,:2]) for t in ts if Polygon(t[:,:2]).area>1e-12]);actualIntersections=read(str(OUT.relative_to(ROOT)/'actual-four-shore-intersections.json'));actualDelivery=read(base+'landmarks/city-balcony-floor-v2/model-delivery.json');bind(base+'landmarks/city-balcony-floor-v2/city-balcony.glb')
actualPoints=[q for sr in actualIntersections for part in sr['parts'] for hit in part['pairs'] for q in hit.get('pointsENU',[])]
actualExtension=max(mainEnvelope.distance(Point(q[:2])) for q in actualPoints)
hardwareClearance=math.ceil((actualExtension+.001)*100)/100
# Explicit outward extension based on actual triangle intersection points plus float32 tolerance.
clipEnvelope=mainEnvelope.buffer(hardwareClearance,join_style=2)
owned=strip.intersection(clipEnvelope);unowned=strip.difference(clipEnvelope)
def lines(g):
 if g.geom_type=='LineString':return [g]
 return [q for p in g.geoms for q in lines(p)] if hasattr(g,'geoms') else []
def coords(g):
 if g.geom_type=='Polygon':return {'type':'Polygon','coordinates':[list(g.exterior.coords),*[list(h.coords) for h in g.interiors]]}
 if g.geom_type=='MultiPolygon':return {'type':'MultiPolygon','coordinates':[coords(q)['coordinates'] for q in g.geoms]}
 return {'type':g.geom_type,'wkt':g.wkt}
sourceIntervals=[{'fromStationGame':line.project(Point(q.coords[0])),'toStationGame':line.project(Point(q.coords[-1])),'lengthGame':q.length,'frontGeometryGame':list(q.coords)} for q in lines(line.intersection(clipEnvelope))]
piers=[];pierunion=[]
for i,c in enumerate(coll):
 if c['kind']!='representative-pier':continue
 poly=Polygon(c['polygonGame']);over=poly.intersection(strip)
 if over.is_empty or c['maxYGame']<=rec['bottomYGame'] or c['minYGame']>=cap:continue
 buffered=poly.buffer(.001,join_style=2);pierunion.append(buffered);piers.append({'collisionRecordIndex':i,'kind':c['kind'],'sourceFeatureIds':c['sourceFeatureIds'],'polygonGame':c['polygonGame'],'minYGame':c['minYGame'],'maxYGame':c['maxYGame'],'exactStripOverlapAreaGame2':over.area,'subtractHorizontalToleranceGame':.001,'stationRangeFromFootprintProjectionGame':[min(line.project(Point(q)) for q in buffered.exterior.coords),max(line.project(Point(q)) for q in buffered.exterior.coords)]})
remaining=owned.difference(shapely.union_all(pierunion)) if pierunion else owned
# Candidate dry-main cap only lowers current terrain; never create land in river or fill lower hall.
dryMain=clipEnvelope.difference(wet);xmin,zmin,xmax,zmax=dryMain.bounds;sample=[]
for x in np.arange(xmin,xmax+1,1.):
 for z in np.arange(zmin,zmax+1,1.):
  if dryMain.covers(Point(x,z)):
   h=ground(float(x),float(z));sample.append({'x':float(x),'z':float(z),'currentGroundYGame':h,'candidateCappedGroundYGame':min(h,cap),'cutDepthGame':max(0,h-cap),'inPublicLowerFootprint':mainPublic.covers(Point(x,z))})
# Profile triangle interpolation for bounded finger underside terrain clearance, independent of module code.
def fh(x,z,f):
 dx,dz=(x-ax)/.6,(z-az)/.6;u,v=dx*ca+dz*sa,-dx*sa+dz*ca
 for t in f['trianglesUVHMetres']:
  a,b,c=np.array(t);matrix=np.array([[a[0],b[0],c[0]],[a[1],b[1],c[1]],[1,1,1]]);w=np.linalg.solve(matrix,np.array([u,v,1]))
  if min(w)>=-1e-8:return lower+float(w@np.array(t)[:,2])*.6
 raise ValueError('Point outside frozen finger triangles')
fingerCuts=[]
oldSamples=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-datum-proposal/finger-samples.json')
for f in p['fingers']:
 samples=next(q for q in oldSamples if q['id']==f['id'])['footprintSamples1Game'];depths=[]
 for q in samples:
  target=fh(q['x'],q['z'],f)-slab-clearance;depths.append(max(0,q['groundYGame']-target))
 fingerCuts.append({'id':f['id'],'exactSourceFootprintGame':world(f['polygonUVMetres']),'rule':'newTerrain=min(oldTerrain, frozen upper profile - slabThicknessGame - hiddenClearanceGame); dry source finger only','slabThicknessGame':slab,'hiddenClearanceGame':clearance,'maxCutDepthAtFrozen1GameSamples':max(depths),'minCutDepthAtFrozen1GameSamples':min(depths),'sampleCount':len(depths),'noNewLowerFloor':True,'noGroundRaiseOrFill':True})
contract={'id':'city-balcony-floor-v2-bounded-shore-terrain-ownership-proposal','status':'executable candidate geometry contract, not integrated or physically accepted','sourceBuildingRelation':'relation/8718551','baseYGame':lower,'upperYGame':p['upperYGame'],'lowerSlabThicknessGame':slab,'hiddenClearanceGame':clearance,'capTopYGame':cap,'originalWaterYGame':rec['waterYGame'],'originalShoreBottomYGame':rec['bottomYGame'],'shoreFrontSourceLineSha256':rec['sourceLineSha256'],'shoreSourceId':rec['id'],'sourceStationIntervals':sourceIntervals,'mainEnvelopeGame':coords(mainEnvelope),'clipEnvelopeGame':coords(clipEnvelope),'hardwareClearanceGame':hardwareClearance,'actualMaximumNearShoreStructureExtensionGame':actualExtension,'actualBalconyArtifactSha256':actualDelivery['artifactSha256'],'hardwareClearanceBasis':'actual v2 lower steel shore-intersection points extend .025610007g beyond source plan; .03g includes float32 tolerance, not a surveyed expanded footprint','publicLowerFootprintGame':coords(mainPublic),'actualOwnedShoreStripGame':coords(owned),'remainingCappedShoreAfterPierCutsGame':coords(remaining),'unchangedShoreAreaGame2':unowned.area,'ownedShoreAreaGame2':owned.area,'sourcePiersToSubtract':piers,'dryMainTerrainCutBoundaryGame':coords(dryMain),'dryMainTerrainRule':'newTerrain=min(oldTerrain, capTopYGame) inside source dry main envelope plus explicit .03g hardware tolerance; water identity/height untouched; no fill; lower public-floor provider remains separate','dryMainCutSampleCount':len(sample),'dryMainCutDepthRangeGame':[min(q['cutDepthGame'] for q in sample),max(q['cutDepthGame'] for q in sample)],'fingerTerrainCuts':fingerCuts,'orderedOperations':['split all shore segments at exact clip-envelope intersection (source outline plus explicit .03g actual-hardware tolerance), not rounded station bounds; original front line and water boundary unchanged','within owned main strip only, cap shore top at min(original top, capTopYGame); preserve original bottom and reclose caps/sides','subtract the listed actual representative-pier footprints plus .001g serialization tolerance through their stated vertical ranges; close resulting solids; no generic full-building deletion','preserve source-station segments outside owned clip envelope and all three other shores byte-source geometry','generate isolated dry main terrain cap and exact finger profile underside cut candidates; never modify wet masks or add fill','use identical object ownership in visual terrain and height-aware movement/collision; source public upper/lower floor queries remain explicit','recompute actual GLB positive-volume intersections, source boundary preservation and terminal contacts; browser/body/entrance acceptance still required'],'unknowns':['absolute real-world datum and actual lower entrances','glass-part interior usage/floors remain unimplemented; cutting terrain under source envelope does not invent them','actual side-wall retaining contact where dry terrain meets main source boundary','underground Zhijiang road stays independent; no automatic graph connection','runtime terrain/deck layer ownership and collision precision']}
save('ownership-contract.json',contract);save('dry-main-terrain-samples.json',sample);save('ownership-input-bindings.json',bindings)
print(json.dumps({k:contract[k] for k in ['capTopYGame','sourceStationIntervals','unchangedShoreAreaGame2','ownedShoreAreaGame2','dryMainCutSampleCount','dryMainCutDepthRangeGame','fingerTerrainCuts']},indent=2));print('piers',len(piers))
