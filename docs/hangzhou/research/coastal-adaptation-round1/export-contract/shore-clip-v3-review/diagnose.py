from pathlib import Path
source=Path(__file__).with_name('check.py').read_text().split('ap=argparse.ArgumentParser')[0];exec(compile(source,str(Path(__file__).with_name('check.py')),'exec'),globals())
old,_=glb('artifacts/cities/hangzhou/shore-glb-v2/coastal-shoreline.glb');new,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');target='coastal_shore_5_-4_land';oldts=next(p['triangles'] for p in old if p['name']==target);newts=next(p['triangles'] for p in new if p['name']==target);c=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2-glb-review/ownership-contract.json');pier=shapely.union_all([Polygon(p['polygonGame']).buffer(p['subtractHorizontalToleranceGame'],join_style=2) for p in c['sourcePiersToSubtract']])
def fp(ts):return shapely.union_all([Polygon(t[:,:2]) for t in ts if Polygon(t[:,:2]).area>1e-12])
a,b=fp(oldts).difference(pier),fp(newts)
def polys(g):return list(g.geoms) if hasattr(g,'geoms') else [g]
def rings(g):return [r for p in polys(g) for r in [p.exterior,*p.interiors]]
def desc(g):return {'type':g.geom_type,'area':g.area,'polygons':len(polys(g)),'holes':sum(len(p.interiors) for p in polys(g)),'holeAreas':sorted([Polygon(h).area for p in polys(g) for h in p.interiors]),'smallestPolygonAreas':sorted(p.area for p in polys(g))[:20]}
max1=max((Point(x).distance(b.boundary),x) for r in rings(a) for x in r.coords);max2=max((Point(x).distance(a.boundary),x) for r in rings(b) for x in r.coords)
precision=[]
for grid in [1e-10,1e-9,1e-8,1e-7]:
 aa=shapely.set_precision(a,grid);bb=shapely.set_precision(b,grid);precision.append({'gridGame':grid,'expected':desc(aa),'actual':desc(bb),'boundaryHausdorffGame':aa.boundary.hausdorff_distance(bb.boundary),'expectedSymDiffFromRawGame2':aa.symmetric_difference(a).area,'actualSymDiffFromRawGame2':bb.symmetric_difference(b).area})
uv=[]
for p in new:
 t=p['uv'];areas=np.abs((t[:,1,0]-t[:,0,0])*(t[:,2,1]-t[:,0,1])-(t[:,1,1]-t[:,0,1])*(t[:,2,0]-t[:,0,0]));uv.append({'name':p['name'],'zeroUvAreaFaces':int((areas==0).sum()),'minUvDoubleArea':float(areas.min())})
save('projection-diagnostic.json',{'rawExpected':desc(a),'rawActual':desc(b),'largestExpectedBoundaryPointDistanceToActual':max1,'largestActualBoundaryPointDistanceToExpected':max2,'precisionDiagnostics':precision,'uvAreas':uv});print(json.dumps({'rawExpected':desc(a),'rawActual':desc(b),'max1':max1,'max2':max2,'precision':precision,'uv':uv},indent=2))
