# Extends independent read/decode review. No Blender, producer Surface, or shared mutations.
import runpy
from pathlib import Path
scope=runpy.run_path(str(Path(__file__).with_name('check.py')));globals().update({k:v for k,v in scope.items() if not k.startswith('__')})
# Exact canonical oriented float32 expected faces rather than arbitrary decimal rounding.
def canonical(t):
 ps=[tuple(p) for p in t];return min(tuple(ps),tuple(ps[1:]+ps[:1]),tuple(ps[2:]+ps[:2]))
exact=[]
for rec in em['objects']:
 ts=all_npz[rec['id']];origin=np.array(rec['originENU']);expected=(ts-origin).astype('<f4').astype('f8')+origin;actualpart=next(a for a in actual if a['name']==rec['mesh']);counts1=collections.Counter(canonical(t) for t in expected);counts2=collections.Counter(canonical(t) for t in actualpart['triangles']);exact.append({'id':rec['id'],'orientedFloat32TrianglesExactlyEqual':counts1==counts2,'missing':sum((counts1-counts2).values()),'extra':sum((counts2-counts1).values())})
save('exact-float32-independent.json',exact)
# Actual 3D triangle/triangle surface intersection. XY projection tree is only broad phase.
shorepart=next(a for a in actual if a['name']=='coastal_shore_5_-4_land');sts=shorepart['triangles'];s_polys=[Polygon(t[:,:2]) for t in sts];tree=STRtree(s_polys)
def intri(p,t,eps=1e-6):
 v0=t[1]-t[0];v1=t[2]-t[0];v2=p-t[0];d00=np.dot(v0,v0);d01=np.dot(v0,v1);d11=np.dot(v1,v1);d20=np.dot(v2,v0);d21=np.dot(v2,v1);den=d00*d11-d01*d01
 if abs(den)<1e-20:return False
 v=(d11*d20-d01*d21)/den;w=(d00*d21-d01*d20)/den;return v>=-eps and w>=-eps and v+w<=1+eps
def tri_intersection(a,b):
 na=np.cross(a[1]-a[0],a[2]-a[0]);nb=np.cross(b[1]-b[0],b[2]-b[0]);la=np.linalg.norm(na);lb=np.linalg.norm(nb)
 if la==0 or lb==0:return None
 na/=la;nb/=lb
 if np.linalg.norm(np.cross(na,nb))<1e-8:
  if max(abs((a-b[0])@nb))>1e-6:return None
  axes=[i for i in range(3) if i!=np.argmax(abs(na))];o=Polygon(a[:,axes]).intersection(Polygon(b[:,axes]));return {'type':'coplanar','projectedArea':o.area} if not o.is_empty else None
 hits=[]
 for u,v,n in [(a,b,nb),(b,a,na)]:
  ds=(u-v[0])@n
  if ds.min()>1e-6 or ds.max()<-1e-6:continue
  for i in range(3):
   j=(i+1)%3;d,e=ds[i],ds[j]
   if abs(d)<1e-7 and intri(u[i],v):hits.append(u[i].tolist())
   if d*e<0:
    q=u[i]+(u[j]-u[i])*d/(d-e)
    if intri(q,v):hits.append(q.tolist())
 return {'type':'noncoplanar','pointsENU':hits} if hits else None
rows=[];sample=[]
for part in bal:
 pairs=[]
 for i,t in enumerate(part['triangles']):
  for j in map(int,tree.query(Polygon(t[:,:2]))):
   s=sts[j]
   if t[:,2].min()>s[:,2].max()+1e-6 or t[:,2].max()<s[:,2].min()-1e-6:continue
   hit=tri_intersection(t,s)
   if hit:pairs.append({'balconyTriangle':i,'shoreTriangle':j,'balconyYRange':[float(t[:,2].min()),float(t[:,2].max())],**hit})
 rows.append({'name':part['name'],'pairs':pairs,'pairCount':len(pairs),'uniqueBalconyFaces':len(set(p['balconyTriangle'] for p in pairs)),'uniqueShoreFaces':len(set(p['shoreTriangle'] for p in pairs))})
 print('3D',part['name'],len(pairs),flush=True)
save('city-balcony-actual-3d-intersections.json',{'method':'Actual transformed GLB triangles; GEOS XY broad phase plus 3D edge-plane/barycentric narrow phase; 1e-6 positional/coordinate tolerances. Coplanar projected overlap separate. Not volumetric navigation/collision acceptance.','parts':rows})
# Upper balcony public deck footprint at 3.6g: sample local shore top where footprint is source public upper floor.
specb=read('docs/hangzhou/research/core/city-balcony-round2/spec.json');delivery=read(base+'landmarks/city-balcony-v1/model-delivery.json');axis=specb['axisRadiansEastCCW'];ca,sa=math.cos(axis),math.sin(axis);ax,az=delivery['anchorGame']
def xy(ring):return [(ax+(u*ca-v*sa)*.6,az+(u*sa+v*ca)*.6) for u,v in ring]
upper=Polygon(xy(specb['upperOuterUVMetres']),[xy(r) for r in specb['glazedFootprintsUVMetres']]);inter=shore.intersection(upper);level=specb['estimates']['levels']['value']['upperM']*.6
pts=[]
for t in sts:
 if np.min(t[:,2])<.61:continue
 for p in [t.mean(axis=0),*t]:
  if upper.covers(Point(p[:2])):pts.append({'ENU':p.tolist(),'shoreMinusUpperDeckGame':float(p[2]-level)})
save('city-balcony-upper-deck.json',{'upperYGame':level,'shoreFootprintUpperPublicOverlapAreaGame2':inter.area,'samples':pts,'minDelta':min([p['shoreMinusUpperDeckGame'] for p in pts],default=None),'maxDelta':max([p['shoreMinusUpperDeckGame'] for p in pts],default=None)})
save('input-bindings.json',bindings)
