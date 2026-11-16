"""Subtract only the actual new paving/bank footprint from base surface faces."""
import json,sys,hashlib
from pathlib import Path
import shapely
from shapely.geometry import Polygon,box

source,site,output=map(Path,sys.argv[1:]);data=json.loads(source.read_text());sites=json.loads(site.read_text())
if output.exists():raise ValueError('Fresh clip output required')
mask=shapely.union_all([Polygon([p[:2] for p in t]) for g in sites['walkFloors'] for t in g['triangles']])
if not mask.is_valid:raise ValueError('Invalid actual paving mask')
shapely.prepare(mask);records=[];deleted=0;cut=0
for row in data['triangles']:
    tri=Polygon([p[:2] for p in row['world']])
    if tri.area<=1e-12 or not mask.intersects(tri):continue
    overlap=tri.intersection(mask)
    if overlap.area<=1e-12:continue
    rem=tri.difference(mask);fragments=[]
    for poly in shapely.get_parts(rem):
        if poly.geom_type!='Polygon' or poly.area<=1e-12:continue
        for t in shapely.get_parts(shapely.constrained_delaunay_triangles(poly)):
            points=list(t.exterior.coords)[:3]
            if not Polygon(points).exterior.is_ccw:points.reverse()
            fragments.append(points)
    records.append({'primitive':row['primitive'],'offset':row['offset'],'pieces':fragments})
    deleted+=not bool(fragments);cut+=bool(fragments)
output.write_text(json.dumps({'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'siteSha256':hashlib.sha256(site.read_bytes()).hexdigest(),'maskAreaGame2':mask.area,'maskBounds':mask.bounds,
    'deletedTriangles':deleted,'cutTriangles':cut,'records':records},separators=(',',':'))+'\n')
print(json.dumps({'deleted':deleted,'cut':cut,'maskAreaGame2':mask.area}))
