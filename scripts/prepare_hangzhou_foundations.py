"""Prepare bounded foundation skins under three rigidly placed landmark models.
Uses only existing solid support footprints, preserving holes and open portals.
This does not grade public roads or claim surveyed construction/entrances.
"""
from __future__ import annotations
import argparse,json,math,time
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon
from hangzhou_surface import Surface,digest
from hangzhou_foundation_mesh import closed_foundation
ROOT=Path(__file__).resolve().parents[1]
def parts(g):return [g] if g.geom_type=='Polygon' else [p for q in g.geoms for p in parts(q)]
def rings(p):return [[[x,z] for x,z in r.coords] for r in [p.exterior,*p.interiors]]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--models',required=True);ap.add_argument('--city-root',required=True);ap.add_argument('--collision',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    models=ROOT/a.models;root=ROOT/a.city_root;out=(ROOT/a.output).resolve();collision_path=ROOT/a.collision
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    field=Surface(root);collision=json.loads(collision_path.read_text());commands=json.loads((models/'commands-for-audit.json').read_text());inputs={};records=[];extra=[];started=time.monotonic()
    def bind(p):inputs[str(p.relative_to(ROOT))]=digest(p);return json.loads(p.read_text())
    bind(collision_path);bind(models/'commands-for-audit.json');bind(root/'geography/manifest.json')
    for p in [Path(__file__),ROOT/'scripts/hangzhou_surface.py',ROOT/'scripts/hangzhou_foundation_mesh.py',root/'geography'/field.manifest['terrainFile'],root/'geography'/field.manifest['roadLevelsFile']]:inputs[str(p.relative_to(ROOT))]=digest(p)
    out.mkdir(parents=True)
    for command in commands:
        name=command['id'];delivery=bind(models/name/'model-delivery.json');placement_file=ROOT/next(p['path'] for p in delivery['sourceInputs'] if p['role']=='placement');placement=bind(placement_file)
        for dep in placement['sourceInputs']:
            if digest(ROOT/dep['path'])!=dep['sha256']:raise ValueError('Changed floor source '+dep['path'])
        proposal_file=ROOT/next(p['path'] for p in placement['sourceInputs'] if p['path'].endswith('-floor-proposal.json'));proposal=bind(proposal_file)
        if name not in ('hangzhou-gate','cainiao-headquarters','little-lotus') or delivery['baseYGame']!=proposal['newBaseYGame']:raise ValueError('Unsupported foundation semantic')
        top=delivery['baseYGame'];supports=proposal['actualCollisionSupportPolygons'];polygons=[Polygon(s['ringsGame'][0],s['ringsGame'][1:]) for s in supports];domain=shapely.union_all(polygons)
        faces=[];worst=0;sampled_max=-math.inf;bottom_min=math.inf
        def ground(x,z):
            nonlocal sampled_max,bottom_min
            y=field.ground(x,z);sampled_max=max(sampled_max,y);bottom_min=min(bottom_min,y-.02)
            if y>top+.0001:raise ValueError('Ground above proposed foundation '+name)
            return y-.02
        for pi,part in enumerate(parts(domain)):
            part=shapely.geometry.polygon.orient(part,sign=1);planar=[]
            for triangle in parts(shapely.constrained_delaunay_triangles(part)):
                t=list(triangle.exterior.coords)[:3]
                if not Polygon(t).exterior.is_ccw:t.reverse()
                planar.append(t)
            closed,error,part_min=closed_foundation(planar,ground,top)
            faces.extend(closed);worst=max(worst,error)
            extra.append({'id':name+':foundation:'+str(pi),'rings':rings(part),'minY':part_min,'maxY':top,'kind':'sampled-terrain-to-authored-floor-support'})
        if worst>.01:raise ValueError('Foundation ground approximation above .01 '+name)
        file=out/(name+'.npz');np.savez_compressed(file,concrete=np.asarray(faces,dtype='<f8'))
        delta=delivery['baseYGame']-proposal['oldBakedBaseYGame'];moved=0
        for solid in collision['collisionFootprints']:
            if solid['id'].startswith(name+':'):
                solid['minY']+=delta;solid['maxY']+=delta;moved+=1
        if moved!=len(supports):raise ValueError('Collision support membership mismatch '+name)
        for mark in collision['landmarks']:
            if mark['id']==name:mark.update(baseYGame=top,artifactSha256=delivery['artifactSha256'],collisionStatus='floor-offset candidate; entry and browser validation pending')
        records.append({'id':name,'file':file.name,'sha256':digest(file),'triangles':len(faces),'oldSupportFootprints':len(supports),'foundationParts':len(parts(domain)),'holes':sum(len(p.interiors) for p in parts(domain)),'maxSampledBottomErrorGame':worst,'sampledMaxGroundGame':sampled_max,'floorYGame':top,'minimumFoundationYGame':bottom_min,'sourceDelivery':str((models/name/'model-delivery.json').relative_to(ROOT)),'sourceDeliverySha256':digest(models/name/'model-delivery.json'),'supportUnionWkbSha256':__import__('hashlib').sha256(shapely.normalize(domain).wkb).hexdigest()})
    collision['collisionFootprints'].extend(extra);collision['status']='three rigid floor offsets and support solids candidate; not integrated'
    (out/'detail-collision-manifest.json').write_text(json.dumps(collision,separators=(',',':')))
    report={'cityId':'hangzhou','kind':'landmark-foundation-and-collision-candidate','inputs':inputs,'objects':records,'collisionFile':'detail-collision-manifest.json','collisionSha256':digest(out/'detail-collision-manifest.json'),'seconds':time.monotonic()-started,'basis':'bounded estimated foundations to current game ground; original support topology, no blanket flattening or invented surveyed entrance','pending':['actual GLB export/mesh parity','independent collision and support footprint proof','ground seam and entrance step interaction','all in-game visual/night/performance']}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='inputs'},indent=2))
if __name__=='__main__':main()
