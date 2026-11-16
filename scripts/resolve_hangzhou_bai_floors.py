"""Visible upper envelope of intersecting exported walk triangles.

Crop buried portions of support faces instead of relaxing runtime step/contact
thresholds. Every remaining point stays on an actual original GLB triangle.
"""
import json,sys,hashlib,shutil,math
from pathlib import Path
import shapely
from shapely.geometry import Polygon

source,output=map(Path,sys.argv[1:])
if output.exists():raise ValueError('Fresh support candidate required')
data=json.loads((source/'site-surfaces.json').read_text());triangles=[t for g in data['walkFloors'] for t in g['triangles']]
polygons=[Polygon([p[:2] for p in t]) for t in triangles];tree=shapely.STRtree(polygons)
def height(i,x,z):
    a,b,c=triangles[i];det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    u=((x-a[0])*(c[1]-a[1])-(z-a[1])*(c[0]-a[0]))/det
    v=((b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0]))/det
    return a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])
def higher_region(poly,i,j):
    ps=list(poly.exterior.coords)[:-1];values=[height(j,*p)-height(i,*p) for p in ps]
    if max(abs(v) for v in values)<1e-10:return poly if j<i else Polygon()
    if max(values)<=0:return Polygon()
    if min(values)>=0:return poly
    out=[]
    for k,a in enumerate(ps):
        b=ps[(k+1)%len(ps)];v,w=values[k],values[(k+1)%len(ps)]
        if v>=0:out.append(a)
        if (v>=0)!=(w>=0):
            t=v/(v-w);out.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
    return Polygon(out) if len(out)>=3 else Polygon()
resolved=[];cut=0;overlap_max=0
for i,poly in enumerate(polygons):
    cuts=[]
    for j in tree.query(poly):
        j=int(j)
        if i==j:continue
        overlap=poly.intersection(polygons[j])
        if overlap.geom_type!='Polygon' or overlap.area<=1e-12:continue
        overlap_max=max(overlap_max,max(abs(height(j,*p)-height(i,*p)) for p in overlap.exterior.coords))
        higher=higher_region(overlap,i,j)
        if not higher.is_empty:cuts.append(higher)
    rem=poly.difference(shapely.union_all(cuts)) if cuts else poly
    cut+=bool(cuts)
    for piece in shapely.get_parts(rem):
        if piece.geom_type!='Polygon' or piece.area<=1e-12:continue
        for t in shapely.get_parts(shapely.constrained_delaunay_triangles(piece)):
            ps=list(t.exterior.coords)[:3]
            if not Polygon(ps).exterior.is_ccw:ps.reverse()
            resolved.append([[x,z,height(i,x,z)] for x,z in ps])
before=shapely.union_all(polygons);after=shapely.union_all([Polygon([p[:2] for p in t]) for t in resolved])
lost=before.difference(after).area
if lost>1e-7:raise ValueError(f'Upper envelope lost support area {lost}')
shutil.copytree(source,output)
data['walkFloors']=[{'id':'bai-route:actual-paved-and-bank','triangles':resolved}]
data['terrainCuts']=[{'id':'bai-route:under-paving','triangles':[[[x,z,y-.15] for x,z,y in t] for t in resolved]}]
(output/'site-surfaces.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
report={'sourceSiteSha256':hashlib.sha256((source/'site-surfaces.json').read_bytes()).hexdigest(),
    'resolvedSiteSha256':hashlib.sha256((output/'site-surfaces.json').read_bytes()).hexdigest(),
    'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sourceTriangles':len(triangles),
    'resolvedTriangles':len(resolved),'cutFaces':cut,'maximumActualOverlapHeightGame':overlap_max,'lostAreaGame2':lost,
    'method':'subtract only higher actual triangle planes; stable source-index ownership for coplanar duplicate faces; original gameplay thresholds unchanged'}
(output/'upper-envelope-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
