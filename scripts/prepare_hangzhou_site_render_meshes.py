"""Bake site-aware nonflat city meshes into a fresh, inspectable candidate.

This successor keeps the frozen v9 preparation script intact. Local terrain
assets must replace the declared crops before the result is a complete city.

The road-height and terrain data share the runtime frame and single scale.
Mesh approximation errors and unresolved decks/shorelines remain reported.
No Blender or public writes; the companion exporter is the only scene owner.
"""
from __future__ import annotations
import argparse,hashlib,json,math,time,heapq
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,box
from shapely.strtree import STRtree
from city_config import ROOT
from hangzhou_surface import Surface,digest
from hangzhou_site_render import SiteRender
from hangzhou_site_partition import SitePartition

def poly(rings):
    p=Polygon(rings[0],rings[1:])
    if not p.is_valid:raise ValueError('Invalid source polygon')
    return p
def parts(g):
    if g.geom_type=='Polygon':return [] if g.is_empty else [g]
    return [p for child in getattr(g,'geoms',[]) for p in parts(child)]
def triangles(g):
    return [list(p.exterior.coords)[:3] for p in parts(shapely.constrained_delaunay_triangles(g)) if p.area>0]
def refine(points,max_edge):
    pending=[points]
    while pending:
        p=pending.pop();lengths=[math.dist(p[i],p[(i+1)%3]) for i in range(3)];i=max(range(3),key=lengths.__getitem__)
        if lengths[i]<=max_edge:yield p;continue
        a,b,c=p[i],p[(i+1)%3],p[(i+2)%3];m=((a[0]+b[0])/2,(a[1]+b[1])/2);pending.extend([[a,m,c],[m,b,c]])

def prepare(source,street,inventory,output,minimum_edge=2,target_error=.04,site_plan=None):
    source,street,inventory,output=map(lambda p:Path(p).resolve(),[source,street,inventory,output]);began=time.monotonic()
    if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
    city_path=source/'city.json';city=json.loads(city_path.read_text());field=Surface(source);objects=json.loads(inventory.read_text())
    if city['meta']['cityId']!='hangzhou' or objects['cityId']!='hangzhou':raise ValueError('Wrong city')
    site=SiteRender(ROOT,field,site_plan)
    levels={r['id']:r for r in field.levels['roads']}
    for r in city['roads']:
        q=levels[r['id']]
        if any(r[k]!=q[k] for k in ['points','nodeIds','heights','width']):raise ValueError('Road renderer/runtime mismatch '+r['id'])
    for o in objects['objects']:
        d=json.loads((ROOT/o['deliveryFile']).read_text())
        for key,sha in [('artifact','artifactSha256'),('sourceModule','sourceModuleSha256'),('spec','specSha256')]:
            if digest(ROOT/d[key])!=d[sha]:raise ValueError('Changed object '+o['id'])
    if not 0<minimum_edge<=2 or not 0<target_error<=.04:raise ValueError('Refinement may tighten, not relax the previous acceptance threshold')
    output.mkdir(parents=True,exist_ok=True);(output/'mesh-data').mkdir();records=[];counts=Counter();errors=Counter();worst=[];sequence=0
    def write(name,groups):
        # Keep source precision until the exporter has subtracted a local
        # origin. World float32 around x=-13000 collapsed thin clipped faces.
        arrays={key:np.asarray(v,dtype='<f8').reshape(-1,3,3) for key,v in groups.items() if v}
        if not arrays:return
        p=output/'mesh-data'/(name+'.npz');np.savez_compressed(p,**arrays)
        counts.update({key:len(v) for key,v in arrays.items()});records.append({'name':name,'file':str(p.relative_to(output)),'sha256':digest(p),'triangles':{key:len(v) for key,v in arrays.items()}})
    def face(groups,material,points,height,max_edge=120):
        nonlocal sequence
        pending=[points]
        while pending:
            t=pending.pop();values=[height(*p) for p in t];lengths=[math.dist(t[i],t[(i+1)%3]) for i in range(3)];longest=max(range(3),key=lengths.__getitem__)
            if shapely.Polygon(t).area<=0:raise ValueError('Nonpositive source triangle')
            probes=[((t[i][0]+t[(i+1)%3][0])/2,(t[i][1]+t[(i+1)%3][1])/2,(values[i]+values[(i+1)%3])/2) for i in range(3)]
            probes.append((sum(p[0] for p in t)/3,sum(p[1] for p in t)/3,sum(values)/3));error=max(abs(height(x,z)-estimated) for x,z,estimated in probes)
            if lengths[longest]>max_edge or error>target_error and lengths[longest]>minimum_edge:
                a,b,c=t[longest],t[(longest+1)%3],t[(longest+2)%3];middle=((a[0]+b[0])/2,(a[1]+b[1])/2);pending.extend([[a,middle,c],[middle,b,c]]);continue
            errors['max']=max(errors['max'],error);errors['leaves']+=1;errors['aboveTarget']+=error>target_error+1e-6
            if error>target_error+1e-6:
                sequence+=1;item=(error,sequence,{'material':material,'points':t,'heightValues':values,'errorGame':error,'longestEdgeGame':lengths[longest]})
                if len(worst)<32:heapq.heappush(worst,item)
                elif error>worst[0][0]:heapq.heapreplace(worst,item)
            a,b,c=t
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:t=list(reversed(t))
            vertices=[(x,z,height(x,z)) for x,z in t];groups[material].append(vertices)
    water_polys=[poly(w['rings']) for w in city['water']];water_tree=STRtree(water_polys);green_polys=[poly(g['rings']) for g in city['green']];green_tree=STRtree(green_polys);extent=city['meta']['extent'];g=field.grid
    domain=box(*extent)
    # Each tile retains the original south-east / north-west diagonal. There
    # is no southern sea, mainland crop, opposite shore or second scale.
    tiles=defaultdict(list)
    for j in range(g['rows']-1):
        z=g['z0']+j*g['step']
        for i in range(g['columns']-1):
            x=g['x0']+i*g['step']
            if x>extent[2] or z>extent[3]:continue
            tiles[(math.floor((x+g['step']/2)/640),math.floor((z+g['step']/2)/640))].append((x,z))
    for number,(key,cells) in enumerate(tiles.items()):
        groups=defaultdict(list)
        for x,z in cells:
            square=box(x,z,min(x+g['step'],extent[2]),min(z+g['step'],extent[3]));wet_ids=water_tree.query(square,predicate='intersects');green_ids=green_tree.query(square,predicate='intersects');wet=shapely.union_all([water_polys[int(i)] for i in wet_ids]);green=shapely.union_all([green_polys[int(i)] for i in green_ids])
            a,b,d,c=(x,z),(x+g['step'],z),(x,z+g['step']),(x+g['step'],z+g['step'])
            for raw in [[a,b,d],[b,c,d]]:
                dry=site.terrain_outside(Polygon(raw).intersection(square).difference(wet))
                for material,shape in [('park',dry.intersection(green)),('land',dry.difference(green))]:
                    for tri in triangles(site.pin_geometry(shape)):face(groups,material,tri,lambda x,z:site.terrain_height(x,z,field.uncut_ground))
        write('terrain_'+str(key[0])+'_'+str(key[1]),groups)
        if number%50==0:print('terrain tile',number,'/',len(tiles),'seconds',round(time.monotonic()-began,2),flush=True)
    # Preserve every source TIN face in one record, without tile clipping or
    # adaptive triangulation. Local-frame export handles the thin faces.
    if site.patch_faces:
        source_domain=site.patches
        if source_domain.intersection(shapely.union_all(water_polys)).area>0:
            raise ValueError('Source TIN occupies mapped water; explicit bridge ownership required')
        center=source_domain.centroid;key=(math.floor(center.x/640),math.floor(center.y/640))
        write('terrain_site_'+str(key[0])+'_'+str(key[1]),{'land':site.patch_faces})
    # Separate each water body's source height; no candidate water slabs.
    water_groups=defaultdict(lambda:defaultdict(list))
    for w in city['water']:
        if w.get('renderSurface') is False:continue
        height=w['height']
        for boundary in w.get('renderRings',[w['rings']]):
            p=poly(boundary).intersection(domain);xmin,zmin,xmax,zmax=p.bounds
            # Real tiles keep long rivers resident near the camera instead of
            # treating an entire 10 km water body as one centroid bucket.
            for ix in range(math.floor(xmin/640),math.floor(xmax/640)+1):
                for iz in range(math.floor(zmin/640),math.floor(zmax/640)+1):
                    for tri in triangles(p.intersection(box(ix*640,iz*640,(ix+1)*640,(iz+1)*640))):face(water_groups[ix,iz],'water',tri,lambda x,z:height,max_edge=400)
    for key,groups in water_groups.items():write('terrain_water_'+str(key[0])+'_'+str(key[1]),groups)
    # Ground carriageways union only with ground carriageways. Elevated and
    # tunnel ways keep their own source-selected profiles and independent y.
    ground=[r for r in city['roads'] if levels[r['id']]['tier']==0];lines=[LineString(r['points']) for r in ground];print('ground road unions',len(lines),flush=True)
    asphalt=shapely.union_all([line.buffer(r['width']/2,cap_style=2,join_style=2) for line,r in zip(lines,ground)]).intersection(domain);pavement=shapely.union_all([line.buffer(r['width']/2+1.8,cap_style=2,join_style=2) for line,r in zip(lines,ground)]).intersection(domain).difference(asphalt)
    road_groups=defaultdict(lambda:defaultdict(list))
    for material,shape,offset in [('asphalt',asphalt,.1),('pavement',pavement,.06)]:
        shape=site.roads_outside(shape)
        for p in parts(shape):
            for tri in triangles(p):
                for t in refine(tri,120):
                    key=(math.floor(sum(q[0] for q in t)/3/640),math.floor(sum(q[1] for q in t)/3/640));face(road_groups[key],material,t,lambda x,z:field.uncut_ground(x,z)+offset)
    print('source elevated/tunnel ribbons',len(city['roads'])-len(ground),flush=True)
    for r in city['roads']:
        level=levels[r['id']]
        if level['tier']==0:continue
        for a,b,ya,yb in zip(r['points'],r['points'][1:],r['heights'],r['heights'][1:]):
            dx,dz=b[0]-a[0],b[1]-a[1];ll=dx*dx+dz*dz
            if ll<1e-8:continue
            length=math.sqrt(ll);nx,nz=-dz/length,dx/length;width=r['width']/2
            y=lambda x,z:ya+(yb-ya)*max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/ll))
            pts=[(a[0]+nx*width,a[1]+nz*width),(b[0]+nx*width,b[1]+nz*width),(b[0]-nx*width,b[1]-nz*width),(a[0]-nx*width,a[1]-nz*width)]
            key=(math.floor((a[0]+b[0])/2/640),math.floor((a[1]+b[1])/2/640))
            clipped=Polygon(pts).intersection(domain)
            if r['id'] in site.road_ids:clipped=site.roads_outside(clipped,r['id'])
            clipped=site.decks.ribbon_outside(r['id'],clipped)
            for tri in triangles(clipped):face(road_groups[key],'asphalt',tri,lambda x,z:y(x,z)+.1)
            # Actual visible deck underside and sides, independently above
            # ground; thickness is an explicit generic estimate, not a survey.
            if level['tier']>0:
                for part in parts(site.decks.concrete_outside(r['id'],clipped)):
                    ring=list(part.exterior.coords)[:-1]
                    if not part.exterior.is_ccw:ring.reverse()
                    for p,q in zip(ring,ring[1:]+ring[:1]):
                        v=[(p[0],p[1],y(*p)-.45),(q[0],q[1],y(*q)-.45),(q[0],q[1],y(*q)+.08),(p[0],p[1],y(*p)+.08)]
                        road_groups[key]['concrete'].extend([v[:3],[v[0],v[2],v[3]]])
                    for tri in triangles(part):
                        if Polygon(tri).exterior.is_ccw:tri=list(reversed(tri))
                        road_groups[key]['concrete'].append([(x,z,y(x,z)-.45) for x,z in tri])
    # One owner for complete named bridge deck support, including side strips
    # between source ways. Their old candidate road shells were removed before
    # GLB export; neither those shells nor generic ribbons are overlaid here.
    for deck in site.decks.decks:
        top,bottom=deck['top'],deck['bottom']
        for part in parts(deck['geometry']):
            key=(math.floor(part.centroid.x/640),math.floor(part.centroid.y/640))
            for tri in triangles(part):
                face(road_groups[key],'asphalt',tri,lambda x,z:top+.1)
                face(road_groups[key],'concrete',tri,lambda x,z:top)
                if Polygon(tri).exterior.is_ccw:tri=list(reversed(tri))
                road_groups[key]['concrete'].append([(x,z,bottom) for x,z in tri])
            # Polygon orientation gives the exterior and holes opposite walls.
            part=shapely.orient_polygons(part)
            for ring in [part.exterior,*part.interiors]:
                coords=list(ring.coords)
                for p,q in zip(coords,coords[1:]):
                    vertices=[(*p,bottom),(*q,bottom),(*q,top),(*p,top)]
                    road_groups[key]['concrete'].extend([vertices[:3],[vertices[0],vertices[2],vertices[3]]])
    if site.road_faces:
        center=site.patches.centroid;key=(math.floor(center.x/640),math.floor(center.y/640))
        asphalt_faces=[[[x,z,y+.1] for x,z,y in t] for t in site.road_faces]
        write('roads_site_'+str(key[0])+'_'+str(key[1]),{'asphalt':asphalt_faces})
    marks=street/'roadline-triangles.json';sr=json.loads((street/'report.json').read_text())
    if digest(marks)!=sr['files'][marks.name]:raise ValueError('Changed markings')
    marking_partition=SitePartition({'terrainPatches':[{'id':'site-paint','triangles':site.patch_faces}]})
    for tri in json.loads(marks.read_text()):
        key=(math.floor(sum(q[0] for q in tri)/3/640),math.floor(sum(q[1] for q in tri)/3/640))
        # Source centrelines were clipped earlier; their buffers and markings
        # can still extend past the DSM domain and must be clipped as surfaces.
        shape=Polygon(tri).intersection(domain)
        for clipped_tri in triangles(site.roads_outside(shape)):
            face(road_groups[key],'roadline',clipped_tri,lambda x,z:field.uncut_ground(x,z)+.112)
        if shape.intersects(site.patches):
            for piece in marking_partition.split(shape.intersection(site.patches),field.uncut_ground):
                for clipped_tri in triangles(piece.shape):
                    face(road_groups[key],'roadline',clipped_tri,lambda x,z,h=piece.height:h(x,z)+.112)
    for key,groups in road_groups.items():write('roads_'+str(key[0])+'_'+str(key[1]),groups)
    buildings=[]
    for b in city['buildings']:
        if b['style']=='landmark-detail':continue
        shape=poly(b['rings']);heights=[field.ground(x,z) for ring in b['rings'] for x,z in ring];base=max(heights);buildings.append({**b,'baseYGame':base,'minY':min(heights),'maxY':base+b['height'],'wallBottomHeights':[[field.ground(x,z) for x,z in ring] for ring in b['rings']],'roofTriangles':triangles(shape),'groundBasis':'source DSM-derived terrain/road earthworks, estimated foundation; not surveyed floor'})
    (output/'buildings.json').write_text(json.dumps(buildings,ensure_ascii=False,separators=(',',':')))
    samples=[];rng=np.random.default_rng(261011)
    for _ in range(1200):
        x,z=rng.uniform(extent[0],extent[2]),rng.uniform(extent[1],extent[3]);samples.append({'x':float(x),'z':float(z),'terrain':field.terrain(x,z),'ground':field.ground(x,z)})
    (output/'sampler-fixture.json').write_text(json.dumps(samples,separators=(',',':')))
    result={'schemaVersion':1,'cityId':'hangzhou','kind':'nonflat-source-bound-render-data-candidate','units':'game metres; never scale again','meshRecords':records,'triangles':dict(counts),'ordinaryBuildings':len(buildings),'renderedDetailCollisionBoxes':0,'inputs':{str(p.relative_to(ROOT)):digest(p) for p in [city_path,source/'geography/manifest.json',inventory,street/'report.json',marks,Path(__file__),ROOT/'scripts/hangzhou_surface.py']},'buildingsFile':'buildings.json','buildingsSha256':digest(output/'buildings.json'),'samplerFixtureSha256':digest(output/'sampler-fixture.json'),'preparationCpuSeconds':time.monotonic()-began,'status':'candidate render data; not physical or gameplay accepted','pending':['bridge-specific profile/rigid-structure consistency','adaptive mesh approximation and tile seams','generic deck support/tunnel portals/ceilings','shoreline levels and banks','landmark individual floors and grounds','near facades/rooftops','current Blender/export/browser/performance']}
    result['inputs'].update(site.inputs)
    result['inputs'][str((ROOT/'scripts/hangzhou_site_render.py').relative_to(ROOT))]=digest(ROOT/'scripts/hangzhou_site_render.py')
    result['inputs'][str((ROOT/'scripts/hangzhou_render_seams.py').relative_to(ROOT))]=digest(ROOT/'scripts/hangzhou_render_seams.py')
    result['inputs'][str((ROOT/'scripts/hangzhou_render_decks.py').relative_to(ROOT))]=digest(ROOT/'scripts/hangzhou_render_decks.py')
    result['inputs'][str((ROOT/'scripts/hangzhou_site_partition.py').relative_to(ROOT))]=digest(ROOT/'scripts/hangzhou_site_partition.py')
    result['siteReplacement']=site.report()
    result['pending'].extend(site.report()['pending'])
    result['meshApproximation']={'method':'longest-edge adaptive subdivision using three edge-midpoint and centre runtime-height probes','targetErrorGame':target_error,'minimumLongestEdgeGame':minimum_edge,'maxSampledErrorGame':errors['max'],'probesAboveTarget':errors['aboveTarget'],'worst':[item[2] for item in sorted(worst,reverse=True)],'note':'height field geometry approximation, never increased source measurement resolution; discontinuities/tile seams remain blockers'}
    (output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['meshRecords','inputs']},ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--city-root',required=True);p.add_argument('--street',required=True);p.add_argument('--inventory',required=True);p.add_argument('--output',required=True);p.add_argument('--minimum-edge',type=float,default=2);p.add_argument('--target-error',type=float,default=.04);p.add_argument('--site-plan',required=True);a=p.parse_args();prepare(a.city_root,a.street,a.inventory,a.output,a.minimum_edge,a.target_error,a.site_plan)
