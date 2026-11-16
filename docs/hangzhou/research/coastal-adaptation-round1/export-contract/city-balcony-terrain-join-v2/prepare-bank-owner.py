from pathlib import Path
import json,hashlib,ast,struct,math,collections,sys
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,shape,mapping
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import Surface
from hangzhou_site_surfaces import SiteSurfaces
from hangzhou_site_partition import polygon_parts,plane
bindings={}
def bind(p):
 p=Path(p);rel=str(p.relative_to(ROOT)) if p.is_absolute() else str(p);bindings[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest();return ROOT/rel
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
p=bind('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(p),'exec'),globals())
site=read(OUT/'site-surfaces-repair.json');field=Surface(ROOT/'artifacts/cities/hangzhou/render-input-v7');field.sites=SiteSurfaces(site);domain={f['properties']['id']:shape(f['geometry']) for f in read(OUT/'local-domains.geojson')['features']};edges=shapely.union_all([domain[g['id']].boundary for g in site['terrainCuts']]);shore,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');part=next(p for p in shore if p['name']=='coastal_shore_5_-4_land');features=[];regular=[];band=[];fail=[]
for i,t in enumerate(part['triangles']):
 n=np.cross(t[1]-t[0],t[2]-t[0]);nz=n[2]/np.linalg.norm(n)
 if nz<=.99:continue
 h=plane(t);poly=Polygon(t[:,:2]).intersection(domain['dry'])
 for p in polygon_parts(poly):
  if p.area<=0:continue
  rp=p.representative_point();points=[(rp.x,rp.y)]+list(p.exterior.coords)[:-1]
  for a,b in zip(list(p.exterior.coords),list(p.exterior.coords)[1:]):points.extend([(a[0]*.25+b[0]*.75,a[1]*.25+b[1]*.75),((a[0]+b[0])/2,(a[1]+b[1])/2)])
  values=[]
  for x,z in points:
   delta=h(x,z)-field.ground(x,z);distance=edges.distance(Point(x,z));r={'actualShoreTriangle':i,'point':[x,z],'shoreMinusPhysics':delta,'distanceToCutBoundary':distance};values.append(delta)
   if distance>.001:
    regular.append(r)
    if abs(delta)>.01:fail.append(r)
   else:band.append(r)
  features.append({'type':'Feature','properties':{'actualShoreMesh':part['name'],'actualTriangleIndex':i,'normalUp':float(nz),'scope':'actual upward closed-bank top only; source physics retained','minSampleDelta':min(values),'maxSampleDelta':max(values)},'geometry':mapping(p)})
mask=shapely.union_all([shape(f['geometry']) for f in features]);save('bank-top-render-owner-mask.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU XY, not WGS84','features':[{'type':'Feature','properties':{'id':'actual-upward-bank-top-owner','renderOnly':True,'sourcePhysicsUnchanged':True,'interiorHeightBudgetGame':.01},'geometry':mapping(mask)}]});save('bank-top-source-faces.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU XY, not WGS84','features':features});report={'actualShoreSha256':bindings['artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb'],'newPhysicsSha256':bindings[str((OUT/'site-surfaces-repair.json').relative_to(ROOT))],'ownerArea':mask.area,'actualTopFragments':len(features),'interiorHeightBudgetGame':.01,'sourceDiscontinuityBandGame':.001,'interiorSamples':len(regular),'interiorMinimumShoreMinusPhysics':min(r['shoreMinusPhysics'] for r in regular),'interiorMaximumShoreMinusPhysics':max(r['shoreMinusPhysics'] for r in regular),'interiorFailures':len(fail),'boundaryBandSamples':len(band),'boundaryBandMinimumShoreMinusPhysics':min(r['shoreMinusPhysics'] for r in band),'boundaryBandMaximumShoreMinusPhysics':max(r['shoreMinusPhysics'] for r in band),'physicsSupportDeleted':False,'wholeSolidProjectionUsed':False,'passedSampledInteriorHeightGate':not fail,'notClaimed':'continuous analytic error bound, exact unique height at closed cliff edges, browser acceptance'};save('bank-top-render-owner-contract.json',report);save('bank-top-height-details.json',{'regular':regular,'band':band,'failures':fail});save('bank-top-input-bindings.json',bindings);print(json.dumps(report,indent=2))
