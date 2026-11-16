"""Bounded cut extension and height-specific render ownership proposal; no shared mutation."""
from pathlib import Path
import json,hashlib,ast,struct,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,shape,mapping
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;PARENT=OUT.parent;bindings={}
def bind(p):
 p=Path(p);rel=str(p.relative_to(ROOT)) if p.is_absolute() else str(p);bindings[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest();return ROOT/rel
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
p=bind('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(p),'exec'),globals())
p=bind(PARENT/'actual-glb-v1-review/relative-position.py');exec(compile(ast.Module(body=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['height','parts']],type_ignores=[]),str(p),'exec'),globals())
site=read('artifacts/cities/hangzhou/render-input-v7/geography/site-surfaces.json');floor,_=glb('artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/city-balcony.glb');shore,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');v2=read(PARENT/'actual-glb-v2-review/actual-report.json');bind('artifacts/cities/hangzhou/city-balcony-terrain-glb-v2/city-balcony-terrain.glb');assert v2['orientedWorldGeometryExactlyEqualsV1']
links=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-envelope-v2/slab-glb-correspondence.json')[1]['actualFaceLinks'];bymesh={p['name']:p for p in floor};upper=site['solidSlabs'][1]['triangles'];bounds={g['id']:shapely.union_all([Polygon([p[:2] for p in t]) for t in g['triangles']]) for g in site['terrainCuts']};dry=shape(next(f['geometry'] for f in read(PARENT/'local-domains.geojson')['features'] if f['properties']['id']=='dry'))
keys=lambda t:tuple(sorted(tuple(round(float(v),9) for v in p[:2]) for p in t));upperkey={keys(t):i for i,t in enumerate(upper)};floorstats=[];features=[]
# Uniform extension .0005g is bounded game adaptation, independent of source OSM.
for group in site['terrainCuts']:
 if not group['id'].endswith('-finger'):continue
 source_poly=bounds[group['id']];actual=[];vertex_errors=[];source_faces=[]
 for t in group['triangles']:
  i=upperkey[keys(t)];ref=links[i]['actualBottomFaces'][0];a=bymesh[ref['mesh']]['triangles'][ref['triangleIndex']];actual.append(a);s=np.array(upper[i]);source_faces.append(i)
  vertex_errors.extend(float(min(np.linalg.norm(p[:2]-q[:2]) for q in s)) for p in a)
 actual_poly=shapely.union_all([Polygon(t[:,:2]) for t in actual]);err=max(vertex_errors);terrainerr=v2['maxSourceVertexErrorGame'];sufficient=err+terrainerr+2e-8;radius=.0005
 expanded=source_poly.buffer(radius,quad_segs=16,join_style=1).intersection(dry);ring=expanded.difference(source_poly)
 # Bound actual rendered floor/terrain discrepancy by corresponding vertex movement + numerical allowance.
 absent=actual_poly.intersection(dry).difference(expanded);actual_directed=max(Point(p[:2]).distance(source_poly) for t in actual for p in t)
 record={'id':group['id'],'sourceTriangleCount':len(source_faces),'originalUpperTriangleIndices':source_faces,'maximumCorrespondingActualFloorXYVertexErrorGame':err,'maximumActualFloorVertexOutsideSourceFootprintGame':actual_directed,'currentTerrainFloatVertexErrorBoundGame':terrainerr,'sufficientUniformRadiusFromTriangleCorrespondenceGame':sufficient,'proposedRadiusGame':radius,'originalFootprintArea':source_poly.area,'additionalDryArea':ring.area,'actualFloorDryAreaOutsideExpandedCut':absent.area,'heightRule':'retain original cut triangles; in added ring cap at nearest original outer boundary point using its existing source cut height, then min with F1 and other cuts; no floor/source movement','physicsAndRenderMustUseSameNewCut':True}
 floorstats.append(record)
 for name,g in [('original',source_poly),('expanded',expanded),('added-ring',ring),('actual-glb-floor',actual_poly)]:features.append({'type':'Feature','properties':{'id':group['id'],'kind':name,'radiusGame':radius if name in ['expanded','added-ring'] else 0},'geometry':mapping(g)})
save('finger-cut-extension.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU XY, not WGS84','features':features});save('finger-cut-extension-contract.json',floorstats)
# Exact actual projected coplanar overlap is the removal mask; no whole-shore cutout.
srows=read(PARENT/'actual-glb-v1-review/shore-relative-position.json')['pairs'];facemap=read(PARENT/'actual-glb-v1-review/actual-face-map.json');groundmap=[m['sourceIndex'] for m in facemap if m['sourceIndex']<len(upper)*1000 and m['sourceIndex']<41906];ground=np.load(bind(PARENT/'actual-glb-v1-review/actual-world-enu.npz'))['top'];shorepart=next(p for p in shore if p['name']=='coastal_shore_5_-4_land');shore_indices=[i for i,t in enumerate(shorepart['triangles']) if np.cross(t[1]-t[0],t[2]-t[0])[2]/np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>.99];shoretop=shorepart['triangles'][shore_indices]
chosen=[r for r in srows if max(abs(r['minTargetMinusGround']),abs(r['maxTargetMinusGround']))<=1e-5];mask=shapely.union_all([shape(r['geometry']) for r in chosen]);mfeatures=[]
for i,r in enumerate(chosen):mfeatures.append({'type':'Feature','properties':{'id':i,'terrainSourceTriangleIndex':groundmap[r['ground']],'terrainActualTopIndex':r['ground'],'shoreActualTriangleIndex':shore_indices[r['target']],'shoreMesh':shorepart['name'],'minimumShoreMinusTerrain':r['minTargetMinusGround'],'maximumShoreMinusTerrain':r['maxTargetMinusGround'],'action':'remove only this actual terrain top fragment; retain shore top, sides, underside and physics ground'},'geometry':r['geometry']})
save('shore-terrain-coplanar-removals.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU XY, not WGS84','features':mfeatures});save('shore-terrain-coplanar-mask.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU XY, not WGS84','features':[{'type':'Feature','properties':{'id':'actual-common-top-only','verticalToleranceGame':1e-5,'renderOnly':True},'geometry':mapping(mask)}]})
ownership=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2-glb-review/ownership-contract.json');cut_edges=shapely.union_all([p.boundary for p in bounds.values()]+[shape(ownership['clipEnvelopeGame']).boundary]);band=cut_edges.buffer(.001);inside=[];outside=[];outsidepolys=[]
for r in srows:
 poly=shape(r['geometry']);narrow=poly.intersection(band);away=poly.difference(band)
 for group,geometry in [(inside,narrow),(outside,away)]:
  for p in parts(geometry):
   if p.area<=1e-12:continue
   ds=[height(shoretop[r['target']],x,z)-height(ground[r['ground']],x,z) for x,z in p.exterior.coords]
   group.append({'area':p.area,'min':min(ds),'max':max(ds),'shoreTopIndex':r['target'],'terrainTopIndex':r['ground'],'geometry':mapping(p)})
summary=lambda rows:{'pairs':len(rows),'area':sum(r['area'] for r in rows),'min':min((r['min'] for r in rows),default=None),'max':max((r['max'] for r in rows),default=None),'absAbovePoint02':sum(max(abs(r['min']),abs(r['max']))>.02 for r in rows)}
save('shore-boundary-band-comparison.json',{'bandHalfWidthGame':.001,'nearSourceDiscontinuities':summary(inside),'awayFromSourceDiscontinuities':summary(outside),'nearRows':inside,'awayRows':outside})
report={'status':'frozen v1 repair proposal only; not integrated','sourceTerrainV2Sha256':v2['actualGlbSha256'],'sourceFloorSha256':bindings['artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/city-balcony.glb'],'sourceShoreSha256':bindings['artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb'],'fingerCutExtension':floorstats,'coplanarRenderMaskArea':mask.area,'coplanarRemovalFragments':len(chosen),'totalActualShoreTerrainProjectedOverlapArea':sum(r['area'] for r in srows),'retainedNonCoplanarOverlapArea':sum(r['area'] for r in srows)-mask.area,'heightCondition':'abs(actual shore top Y - actual terrain top Y)<=1e-5 at every overlap polygon vertex; both are planes','sourceFaceBound':True,'groundPhysicsUntouchedByRenderMask':True,'shoreDiscontinuityBand':summary(inside),'shoreAwayFromDiscontinuityBand':summary(outside),'remaining':['Noncoplanar shore/terrain intersection and discontinuity alignment must be resolved separately','Finger extension requires new shared physical terrainCuts and derived render candidate; old frozen source unchanged','Apply exact per-source-triangle removal, not unconditional whole-shore projection','Actual reexport/visual/body/crop-to-world acceptance pending']}
save('proposal.json',report);save('input-bindings.json',bindings);print((OUT/'proposal.json').read_text())
