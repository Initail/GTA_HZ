"""Source-bound Hangzhou near-camera grass masks; no Blender/public writes.

Retains the existing binary format, blade geometry, shader and streaming budget.
Mapped green land supplies eligibility, not an assertion of measured lawn cover.
Buildings, pavements, water, authored sites and source site discontinuities reserve
whole grass discs. Slopes sample the existing physical surface, never flatten it.
"""
from __future__ import annotations
import argparse,json,math,time
from pathlib import Path
from collections import Counter
import numpy as np
import shapely
from shapely.geometry import Polygon,MultiPolygon,LineString,Point,box
from shapely.strtree import STRtree
from hangzhou_surface import Surface,digest

ROOT=Path(__file__).resolve().parents[1]
RADIUS=2.9
GUARD=.02

def polygon(rings):
    p=Polygon(rings[0],rings[1:])
    if not p.is_valid:raise ValueError('Invalid source polygon')
    return p

def polygonal_area(geometry, audit=None):
    """Retain every positive-area polygon, including nested thin components.

    Overlay may return GeometryCollection with detached zero-area lines/points;
    its .boundary is None. Those objects cannot host a finite grass disc, but
    every polygon and its holes must survive before boundary-distance queries.
    """
    polygons=[]; leaves=Counter()
    def visit(part):
        if part.is_empty:return
        if part.geom_type=='Polygon':
            leaves['Polygon']+=1
            if part.area<=0:raise ValueError('Nonempty zero-area source polygon')
            polygons.append(part)
        elif hasattr(part,'geoms'):
            for child in part.geoms:visit(child)
        else:
            if part.area!=0:raise ValueError('Unexpected positive-area geometry')
            leaves[part.geom_type]+=1
    visit(geometry)
    # Do not re-run overlay or reorder/snap retained rings. Only remove the
    # collection wrapper and its zero-area leaves.
    result=polygons[0] if len(polygons)==1 else MultiPolygon(polygons) if polygons else Polygon()
    if polygons and (not result.is_valid or result.boundary is None):
        raise ValueError('Invalid polygonal source boundary')
    missing=geometry.difference(result).area;extra=result.difference(geometry).area
    if missing!=0 or extra!=0:
        raise ValueError('Polygon extraction changed source area')
    if audit is not None:audit.update({'rawType':geometry.geom_type,'leafCounts':dict(leaves),
        'positivePolygonCount':len(polygons),'minimumPositivePolygonAreaGame2':min((p.area for p in polygons),default=0),
        'rawAreaGame2':geometry.area,'retainedAreaGame2':result.area,'areaSumRoundoffGame2':result.area-geometry.area,'missingAreaGame2':missing,'extraAreaGame2':extra,
        'rawBoundaryWasNone':geometry.boundary is None,'boundaryAvailable':result.boundary is not None,
        'discardedOnlyZeroAreaLinesAndPoints':True,'thinPositiveAreasRemoved':0})
    return result

def noise(x,z):
    def hashed(a,b):
        n=np.sin(a*127.1+b*311.7)*43758.5453123
        return n-np.floor(n)
    a,b=np.floor(x),np.floor(z);u,v=x-a,z-b;u=u*u*(3-2*u);v=v*v*(3-2*v)
    return (hashed(a,b)*(1-u)+hashed(a+1,b)*u)*(1-v)+(hashed(a,b+1)*(1-u)+hashed(a+1,b+1)*u)*v

def ground_batch(field,x,z):
    """Vector equivalent of uncut_ground, preserving source segment order."""
    x,z=np.asarray(x,dtype=float),np.asarray(z,dtype=float)
    g=field.grid;u=(x-g['x0'])/g['step'];v=(z-g['z0'])/g['step']
    ii,jj=np.floor(u).astype(int),np.floor(v).astype(int)
    valid=(ii>=0)&(jj>=0)&(ii<g['columns']-1)&(jj<g['rows']-1)
    i,j=np.clip(ii,0,g['columns']-2),np.clip(jj,0,g['rows']-2);fx,fz=u-ii,v-jj
    a,b,c,d=[q.astype(float) for q in [field.values[j,i],field.values[j,i+1],field.values[j+1,i+1],field.values[j+1,i]]]
    result=np.where(valid,np.where(fx+fz<=1,a+(b-a)*fx+(d-a)*fz,c+(d-c)*(1-fx)+(b-c)*(1-fz)),0)
    keys=np.column_stack((np.floor(x/100).astype(int),np.floor(z/100).astype(int)))
    unique,inverse=np.unique(keys,axis=0,return_inverse=True)
    for n,key in enumerate(unique):
        indices=np.flatnonzero(inverse==n);xx,zz=x[indices],z[indices]
        total=np.zeros(len(indices));weighted=total.copy();influence=total.copy()
        for a,b,ya,yb,width in field.cells.get(tuple(key),[]):
            dx,dz=b[0]-a[0],b[1]-a[1];t=np.clip(((xx-a[0])*dx+(zz-a[1])*dz)/(dx*dx+dz*dz or 1),0,1)
            distance=np.hypot(xx-a[0]-dx*t,zz-a[1]-dz*t)
            edge=np.clip((distance-width/2)/field.transition,0,1);weight=1-edge*edge*(3-2*edge)
            total+=weight;weighted+=(ya+(yb-ya)*t)*weight;influence=np.maximum(influence,weight)
        active=total>0;take=indices[active]
        result[take]+=(weighted[active]/total[active]-result[take])*influence[active]
    return result

def source_geometry(city,detail,sites,life,audit=None):
    audit={} if audit is None else audit
    land=polygonal_area(shapely.union_all([polygon(r) for r in city['land']]),audit.setdefault('land',{}))
    green=polygonal_area(shapely.union_all([polygon(g['rings']) for g in city['green']]).intersection(land),audit.setdefault('green',{}))
    # Use distance to exact source geometry; do not approximate safety circles
    # with an inscribed polygon. Margins retain the original grass exclusions.
    groups={
        'roads':([LineString(r['points']).buffer(r['width']/2+2.8,cap_style=2,join_style=2) for r in city['roads']],RADIUS+GUARD),
        'buildings':([polygon(b['rings']) for b in city['buildings']+detail['collisionFootprints']],RADIUS+GUARD+3),
        'water':([polygon(w['rings']) for w in city['water']],RADIUS+GUARD+6),
        'coast':([LineString(r) for r in city['coast'] if len(r)>1],RADIUS+GUARD+9),
        'life':([Polygon(s['footprint']) for s in life['sites']],RADIUS+GUARD+3),
        'site-surfaces':([Polygon([[p[0],p[1]] for p in tri]) for kind in ['terrainCuts','walkFloors','solidSlabs','terrainPatches'] for group in sites.get(kind,[]) for tri in group['triangles']],RADIUS+GUARD),
        'authored-bases':([Point(m['x'],m['z']).buffer(m['excludeRadius']+3,quad_segs=256) for m in city['landmarks'] if m.get('excludeRadius',0)>0],RADIUS+GUARD),
    }
    return green,land,{key:(STRtree(geometries),distance) for key,(geometries,distance) in groups.items()}

def main():
    parser=argparse.ArgumentParser()
    for key in ['source','detail','life','output']:parser.add_argument('--'+key,required=True)
    args=parser.parse_args();source=(ROOT/args.source).resolve();out=(ROOT/args.output).resolve()
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh artifact directory required')
    began=time.monotonic();inputs={}
    def read(p):
        p=Path(p);inputs[str(p.relative_to(ROOT))]=digest(p);return json.loads(p.read_text())
    city=read(source/'city.json');detail=read(ROOT/args.detail);life=read(ROOT/args.life);m=read(source/'geography/manifest.json')
    if city['meta']['cityId']!='hangzhou' or life['cityId']!='hangzhou':raise ValueError('Wrong city')
    sites=read(source/'geography'/m['siteSurfacesFile']) if m.get('siteSurfacesFile') else {}
    for p in [source/'geography'/m['terrainFile'],source/'geography'/m['roadLevelsFile'],Path(__file__),ROOT/'scripts/hangzhou_surface.py',ROOT/'scripts/hangzhou_site_surfaces.py']:
        inputs[str(p.relative_to(ROOT))]=digest(p)
    geometry_audit={};field=Surface(source);green,land,groups=source_geometry(city,detail,sites,life,geometry_audit)
    green_edges=STRtree(list(shapely.get_parts(green.boundary)));land_edges=STRtree(list(shapely.get_parts(land.boundary)))
    shapely.prepare(green);shapely.prepare(land)
    extent=city['meta']['extent'];counts=Counter();tiles=[];parity=[];sample_points=[]
    (out/'meadow').mkdir(parents=True)
    ix0,iz0=math.floor(extent[0]/128),math.floor(extent[1]/128);ix1,iz1=math.ceil(extent[2]/128),math.ceil(extent[3]/128)
    for iz in range(iz0,iz1):
        for ix in range(ix0,ix1):
            if not green.intersects(box(ix*128,iz*128,(ix+1)*128,(iz+1)*128)):continue
            x,z=np.meshgrid(ix*128+(np.arange(32)+.5)*4,iz*128+(np.arange(32)+.5)*4);x,z=x.ravel(),z.ravel();pts=shapely.points(x,z)
            valid=shapely.contains(green,pts)
            for tree,distance in [(green_edges,RADIUS+GUARD),(land_edges,RADIUS+GUARD+2)]:
                indices=np.flatnonzero(valid)
                if len(indices):
                    pairs=tree.query(pts[indices],predicate='dwithin',distance=distance)
                    valid[indices[np.unique(pairs[0])]]=False
            counts['insideMappedGreen']+=int(valid.sum())
            for key,(tree,distance) in groups.items():
                indices=np.flatnonzero(valid)
                if not len(indices):break
                pairs=tree.query(pts[indices],predicate='dwithin',distance=distance)
                removed=indices[np.unique(pairs[0])];valid[removed]=False;counts['excluded:'+key]+=len(removed)
            indices=np.flatnonzero(valid)
            if not len(indices):continue
            xx,zz=x[indices],z[indices]
            # Evaluate four directions at the centre and edge of each safe disc.
            # This is a sampling approximation, not a measured slope certificate.
            height=ground_batch(field,xx,zz);slope=np.zeros(len(indices))
            for radius in [.25,RADIUS]:
                for dx,dz in [(radius,0),(-radius,0),(0,radius),(0,-radius)]:
                    slope=np.maximum(slope,np.degrees(np.arctan(np.abs(ground_batch(field,xx+dx,zz+dz)-height)/radius)))
            encoded=np.minimum(255,np.ceil(slope*4)).astype('u1')
            mid=noise(xx/65-14,zz/65+2);fine=noise(xx/18+7,zz/18+19)
            soil=np.clip((mid*.74+fine*.26-.64)*3.6,0,1)*.65
            payload=np.zeros((1024,3),dtype='u1');payload[indices,0]=255;payload[indices,1]=np.rint(soil*255).astype('u1');payload[indices,2]=encoded
            counts['safeCells']+=len(indices);counts['runtimeEligibleCells']+=int(np.sum((encoded<=48)&(payload[indices,1]<=198)))
            if len(parity)<2048:
                k=len(indices)//2;scalar=field.ground(float(xx[k]),float(zz[k]));parity.append(abs(scalar-height[k]));sample_points.append([float(xx[k]),float(zz[k]),float(height[k])])
            name=f'tile_{ix}_{iz}.bin';p=out/'meadow'/name;p.write_bytes(payload.tobytes())
            tiles.append({'id':f'{ix}_{iz}','ix':ix,'iz':iz,'url':'meadow/'+name,'bytes':p.stat().st_size,'count':len(indices),'sha256':digest(p)})
        if (iz-iz0)%10==0:print('meadow row',iz-iz0,'/',iz1-iz0,'tiles',len(tiles),'seconds',round(time.monotonic()-began,1),flush=True)
    if not tiles or len(tiles)>20000 or not parity or max(parity)>1e-7:raise ValueError('Meadow coverage/parity gate failed')
    for p,h in inputs.items():
        if digest(ROOT/p)!=h:raise ValueError('Input changed during preparation '+p)
    manifest={'schemaVersion':1,'cityId':'hangzhou','tileSize':128,'step':4,'gridSize':32,'stride':3,'safeRadius':RADIUS,'channels':['safe','soil','slopeDegreesX4'],'sourceSHA':inputs,'tiles':tiles,
        'coordinateRule':'x=ix*128+(col+0.5)*4; z=iz*128+(row+0.5)*4; row-major 3 bytes',
        'heightRule':'Unchanged runtime heightAt for each grass clump; no extra geographic scale.',
        'eligibility':'Whole 2.9g discs within mapped green dry land; not a claim that all mapped green land is surveyed lawn.',
        'proof':{'numericalGuardGame':GUARD,'exactDistanceToPolygonBoundary':True,'polygonalExtraction':geometry_audit,'excluded':list(groups),'siteSurfacesExcluded':True},
        'soilRule':'Original deterministic mid/fine noise style on green parcels; art direction, not measured soil.',
        'slopeRule':'Maximum 8 directional physical-height secants at .25g and 2.9g, rounded upward to quarter degrees; not a full analytic bound.',
        'budgets':{'tiles':len(tiles),'safeCells':counts['safeCells'],'runtimeEligibleCells':counts['runtimeEligibleCells'],'binaryBytes':len(tiles)*3072,'maxTwelveCachedTileBytes':12*3072}}
    (out/'meadow.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'kind':'source-bound offline near-camera grass candidate','inputs':inputs,'manifestSha256':digest(out/'meadow.json'),'counts':dict(counts),'budgets':manifest['budgets'],'scalarParity':{'samples':len(parity),'maximumErrorGame':max(parity)},'samplePoints':sample_points,'seconds':time.monotonic()-began,'pending':['independent binary and whole-disc audit','runtime loader and limits','new geographic inputs require regeneration','browser grass/material/night and performance review'],'status':'candidate; not installed'}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['counts','budgets','scalarParity','seconds']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
