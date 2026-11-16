"""Actual closed-bank coverage distinct from upward-top ownership subtraction."""
from pathlib import Path
import json,hashlib,ast,struct,sys,math
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,shape,mapping
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;BASE=OUT.parent.parent
bindings={}
def bind(p):
 p=Path(p);p=p if p.is_absolute() else ROOT/p;bindings[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
p=bind(BASE/'shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(p),'exec'),globals())
mesh=np.load(bind(OUT/'local-terrain.npz'));top=mesh['top'];wall=mesh['walls'];domain={f['properties']['id']:shape(f['geometry']) for f in read(OUT/'local-domains.geojson')['features']};dry=domain['dry'];mask=shape(read(OUT.parent/'bank-top-render-owner-mask.geojson')['features'][0]['geometry'])
parts,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');bank=next(p for p in parts if p['name']=='coastal_shore_5_-4_land');body=shapely.union_all([Polygon(t[:,:2]) for t in bank['triangles'] if Polygon(t[:,:2]).area>0]);terrain=shapely.union_all([Polygon(t[:,:2]) for t in top]);combined=terrain.union(body.intersection(dry));gap=dry.difference(combined)
def polys(g):
 if g.geom_type=='Polygon':yield g
 elif hasattr(g,'geoms'):
  for x in g.geoms:yield from polys(x)
rows=[]
for g in polys(gap):
 # Hausdorff to surrounding support is a conservative boundary displacement
 # diagnostic; inradius-like probes measure actual narrow uncovered strips.
 points=[Point(c) for c in g.exterior.coords]+[g.representative_point()]
 for t in shapely.get_parts(shapely.constrained_delaunay_triangles(g)):points.append(t.centroid)
 rows.append({'area':g.area,'bbox':list(g.bounds),'touchesOriginalDryBoundary':g.distance(dry.boundary)<1e-9,'maximumProbeDistanceToCombinedSupport':max(p.distance(combined) for p in points),'maximumBoundaryDistanceToOriginalDryBoundary':max(Point(c).distance(dry.boundary) for c in g.exterior.coords),'geometry':mapping(g)})
frames=[];alltri=np.concatenate([top,wall]);origin=np.array([2560.,-2560.,0.]);local=(alltri-origin).astype('f4').astype('f8');norm=np.cross(local[:,1]-local[:,0],local[:,2]-local[:,0]);uv=[]
for i,t in enumerate(alltri):
 axes=[0,1]
 if i>=len(top):
  n=np.cross(t[1]-t[0],t[2]-t[0]);axes=[1,2] if abs(n[0])>=abs(n[1]) else [0,2]
 u=(t[:,axes]/8-np.floor(origin[axes]/8)).astype('f4');u[:,1]=(1-u[:,1].astype('f8')).astype('f4');uv.append(u.astype('f8'))
uv=np.array(uv);duv=uv[:,1]-uv[:,0];euv=uv[:,2]-uv[:,0];det=duv[:,0]*euv[:,1]-duv[:,1]*euv[:,0]
union_n=shapely.set_precision(combined,1e-8);dry_n=shapely.set_precision(dry,1e-8);external_union=shapely.union_all([Polygon(p.exterior) for p in polys(union_n)]);external_dry=shapely.union_all([Polygon(p.exterior) for p in polys(dry_n)])
report={'inputSha256':bindings,'bankProjectionUse':'closed solid projection verifies support only; terrain removal remains upward top mask','renderGridGame':1e-4,'positionBudgetGame':.001,'closedBankCoverageGapArea':gap.area,'gapComponents':len(rows),'largestGapArea':max((r['area'] for r in rows),default=0),'maximumGapProbeDistanceGame':max((r['maximumProbeDistanceToCombinedSupport'] for r in rows),default=0),'normalizedCombinedExteriorHausdorffGame':external_union.boundary.hausdorff_distance(external_dry.boundary),'normalizedCombinedInternalHoles':[Polygon(r).area for p in polys(union_n) for r in p.interiors],'remainingUpwardOwnerOverlapArea':terrain.intersection(mask).area,'outsideOriginalDryArea':terrain.difference(dry).area,'float32':{'originENU':origin.tolist(),'angleRadians':0,'triangles':len(alltri),'degenerate':int(sum(np.linalg.norm(norm,axis=1)==0)),'nonpositiveTop':int(sum(norm[:len(top),2]<=0)),'maximumVertexErrorGame':float(np.linalg.norm(local+origin-alltri,axis=2).max()),'UVdegenerate':int(sum(det==0)),'UVfinite':bool(np.all(np.isfinite(uv)))},'scope':'bounded CPU rendering approximation; not literal zero gaps or globally closed solid; actual GLB validation remains required'}
save('coverage-report.json',report);save('coverage-gap-details.json',rows);print(json.dumps(report,indent=2))
