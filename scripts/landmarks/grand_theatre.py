"""Hangzhou Grand Theatre finite exterior candidate; scene/export free.

Source-bound crescent plans are lofted as an original continuous metal rear
shell and inclined glass front. Two-tier inverted-conical front volume, broad
shallow cap, mapped low wing and representative exterior fan stairs.
Intermediate levels/sections/details are estimates; no water planes or photos.
"""
from __future__ import annotations
import math

try:
    from city_config import load_city,project
except ImportError:
    from scripts.city_config import load_city,project


def _v(spec,key):return spec['estimates'][key]['value']


def _context(lm,spec):
    if spec.get('id')!='grand-theatre' or spec.get('cityId')!='hangzhou':raise ValueError('Grand Theatre needs Hangzhou spec')
    city=load_city('hangzhou');g=city['geography'];a=spec['anchor'];ax,ay=project(a['lon'],a['lat'],city)
    def ring(raw):
        if raw[0]!=raw[-1]:raise ValueError('Source polygon must be closed')
        return [((x-ax)/g['scale'],(y-ay)/g['scale']) for x,y in [project(*p,city) for p in raw[:-1]]]
    parts=[dict(c,ring=ring(c['footprintWGS84'])) for c in spec['components']]
    contours=[dict(c,ring=ring(c['footprintWGS84'])) for c in spec['moonContours']]
    if len(contours)!=11 or len(parts)!=4:raise ValueError('Need mapped main/low-wing/cone and eleven crescent control plans')
    lx,ly=project(lm.get('lon',a['lon']),lm.get('lat',a['lat']),city)
    return parts,contours,((ax-lx)/g['scale'],(ay-ly)/g['scale']),g


class _Mesh:
    def __init__(self,b,scale,offset,base):self.b=b;self.scale=scale;self.offset=offset;self.base=base;self.faces=0;self.triangles=0;self.materials=set()
    def point(self,p):return ((p[0]+self.offset[0])*self.scale,(p[1]+self.offset[1])*self.scale,self.base+p[2]*self.scale)
    def face(self,mat,p):self.b.face(mat,[self.point(q) for q in p]);self.faces+=1;self.triangles+=len(p)-2;self.materials.add(mat)
    def tube(self,mat,a,b,r,n=4):
        d=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(v*v for v in d))
        if length<1e-8:raise ValueError('Zero-length structural depiction')
        d=[v/length for v in d];q=(0,0,1) if abs(d[2])<.9 else (1,0,0)
        u=(d[1]*q[2]-d[2]*q[1],d[2]*q[0]-d[0]*q[2],d[0]*q[1]-d[1]*q[0]);ul=math.sqrt(sum(v*v for v in u));u=[v/ul for v in u]
        v=(d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0])
        rows=[[tuple(p[k]+r*(math.cos(i*math.tau/n)*u[k]+math.sin(i*math.tau/n)*v[k]) for k in range(3)) for i in range(n)] for p in (a,b)]
        for i in range(n):j=(i+1)%n;self.face(mat,[rows[0][i],rows[0][j],rows[1][j],rows[1][i]])
        self.face(mat,list(reversed(rows[0])));self.face(mat,rows[1])


def _cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _triangulate(raw):
    p=list(raw)
    if sum(x*v-u*y for (x,y),(u,v) in zip(p,p[1:]+p[:1]))<0:p.reverse()
    todo=list(range(len(p)));out=[]
    while len(todo)>3:
        for j,b in enumerate(todo):
            a,c=todo[j-1],todo[(j+1)%len(todo)]
            if _cross(p[a],p[b],p[c])<=1e-8:continue
            if any(all(_cross(u,v,p[k])>=-1e-8 for u,v in ((p[a],p[b]),(p[b],p[c]),(p[c],p[a]))) for k in todo if k not in (a,b,c)):continue
            out.append([p[a],p[b],p[c]]);todo.pop(j);break
        else:raise ValueError('Mapped cap triangulation failed; refuse a boundingbox cap')
    out.append([p[i] for i in todo]);return out


def _cap(m,mat,ring,z):
    for tri in _triangulate(ring):m.face(mat,[(x,y,z) for x,y in tri])


def _walls(m,mat,ring,lo,hi):
    for a,b in zip(ring,ring[1:]+ring[:1]):m.face(mat,[(*a,lo),(*b,lo),(*b,hi),(*a,hi)])


def _sample_open(points,count):
    lengths=[math.dist(a,b) for a,b in zip(points,points[1:])];total=sum(lengths);out=[]
    if total<=1e-8:raise ValueError('Empty contour edge')
    for j in range(count):
        want=total*j/(count-1);acc=0
        for k,length in enumerate(lengths):
            if want<=acc+length+1e-7 or k==len(lengths)-1:
                t=min(1,max(0,(want-acc)/length));a,b=points[k],points[k+1]
                out.append(tuple(a[i]+(b[i]-a[i])*t for i in range(2)));break
            acc+=length
    return out


def _sample_closed(ring,count):return _sample_open(ring+[ring[0]],count+1)[:-1]


def _crescent_row(contour,spec):
    raw=contour['ring'];split=contour['splitIndex'];n=int(_v(spec,'facadeGridSamples')['moonAlongHalf'])
    # Every mapped curve begins at its NW tip and turns at its SE tip.
    inner=_sample_open(raw[:split+1],n+1)[:-1]
    outer=_sample_open(raw[split:]+[raw[0]],n+1)[:-1]
    return [(x,y,contour['candidateHeightM']) for x,y in inner+outer]


def _moon(m,contours,spec):
    rows=[_crescent_row(c,spec) for c in contours];n=len(rows[0]);half=n//2
    for a,b in zip(rows,rows[1:]):
        for i in range(n):j=(i+1)%n;m.face('landmarkglass' if i<half else 'silver',[a[i],a[j],b[j],b[i]])
    _cap(m,'roof',contours[0]['ring'],rows[0][0][2]);_cap(m,'silver',contours[-1]['ring'],rows[-1][0][2])
    radius=_v(spec,'frameRadiusM');stride=max(1,half//int(_v(spec,'facadeGridSamples')['verticalStepSampling']))
    for i in range(0,half+1,stride):
        for a,b in zip(rows,rows[1:]):m.tube('silver',a[i],b[i],radius,n=4)
    # Combined horizontal strips retain curtainwall rhythm without thousands
    # of individual pane meshes or undocumented engineering members.
    for row in rows[1:-1]:
        for i in range(half):
            a,b=row[i],row[i+1];w=.055
            m.face('silver',[(a[0],a[1],a[2]-w),(b[0],b[1],b[2]-w),(b[0],b[1],b[2]+w),(a[0],a[1],a[2]+w)])
    for i in range(half,n,8):
        for a,b in zip(rows,rows[1:]):m.tube('steel',a[i],b[i],.035,n=4)
    # Representative horizontal ventilation bands on metal back lower zone.
    # Width/count/location are estimated from 2019 high photograph.
    for row in rows[1:7]:
        for i in range(half+28,min(n-3,half+54)):
            if i%9 in (0,1):continue
            a,b=row[i],row[i+1];w=.40
            m.face('roof',[(a[0],a[1],a[2]-w),(b[0],b[1],b[2]-w),(b[0],b[1],b[2]+w),(a[0],a[1],a[2]+w)])
    return rows


def _wing(m,part,spec):
    raw=part['ring'];base=_v(spec,'platformM');height=_v(spec,'frontWingHeightM')
    _walls(m,'darkglass',raw,base,height);_cap(m,'silver',raw,height)
    for a,b in zip(raw,raw[1:]+raw[:1]):
        length=math.dist(a,b);n=max(1,math.ceil(length/4.5))
        for i in range(n):
            t=(i+.5)/n;x,y=a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
            m.tube('silver',(x,y,base),(x,y,height),.11,n=4)
def _loft(m,rows,mat):
    n=len(rows[0])
    for a,b in zip(rows,rows[1:]):
        for i in range(n):j=(i+1)%n;m.face(mat,[a[i],a[j],b[j],b[i]])


def _front(m,part,spec):
    raw=part['ring'];cx,cy=sum(x for x,y in raw)/len(raw),sum(y for x,y in raw)/len(raw);n=int(_v(spec,'facadeGridSamples')['operaAround'])
    sample=_sample_closed(raw,n);profile=_v(spec,'operaProfile')
    def scaled(z,f):return [(cx+(x-cx)*f,cy+(y-cy)*f,z) for x,y in sample]
    rows=[scaled(z,f) for z,f in profile];_loft(m,rows,'landmarkglass')
    _cap(m,'roof',[(x,y) for x,y,z in rows[0]],rows[0][0][2])
    for i in range(0,n,4):
        for a,b in zip(rows,rows[1:]):m.tube('silver',a[i],b[i],.075,n=4)
    # Fine horizontal pane rhythm is a set of flat bands on the curved cone.
    for (z0,f0),(z1,f1) in zip(profile,profile[1:]):
        steps=max(1,math.floor((z1-z0)/2.4))
        for j in range(steps):
            t=j/steps;z=z0+(z1-z0)*t;f=f0+(f1-f0)*t;row=scaled(z,f)
            for i,a in enumerate(row):b=row[(i+1)%n];m.face('steel',[(a[0],a[1],z),(b[0],b[1],z),(b[0],b[1],z+.07),(a[0],a[1],z+.07)])
    roof=[scaled(z,f) for z,f in _v(spec,'operaRoofProfile')];_loft(m,roof,'silver')
    top_z=roof[-1][0][2]
    for i,a in enumerate(roof[-1]):m.face('silver',[a,roof[-1][(i+1)%n],(cx,cy,top_z)])
    for row in [roof[1],roof[2]]:
        for i,a in enumerate(row):m.tube('steel',a,row[(i+1)%n],.07,n=4)
    return cx,cy,sample


def _stairs(m,center,sample,spec):
    params=_v(spec,'stairProfile');angle=math.radians(90-spec['frontBearingDegreesFromNorth']);u=(math.cos(angle),math.sin(angle));v=(-u[1],u[0])
    radius=sum(math.hypot(x-center[0],y-center[1]) for x,y in sample)/len(sample)*params['startRadiusFactor'];steps=int(params['steps'])
    def point(t,w,z):return (center[0]+u[0]*t+v[0]*w,center[1]+u[1]*t+v[1]*w,z)
    for i in range(steps):
        # Fan width expands toward the plaza; a source-photo shape sample,
        # not current collision, accessible slope or surveyed stair geometry.
        f=i/steps;w=params['topHalfWidthM']+(params['bottomHalfWidthM']-params['topHalfWidthM'])*f
        t=radius+i*params['runM'];z=(steps-i)*params['riseM']
        m.face('concrete',[point(t,-w,z),point(t+params['runM'],-w,z),point(t+params['runM'],w,z),point(t,w,z)])
        m.face('concrete',[point(t+params['runM'],-w,z-params['riseM']),point(t+params['runM'],w,z-params['riseM']),point(t+params['runM'],w,z),point(t+params['runM'],-w,z)])
    for sign in (-1,1):
        start=point(radius,sign*params['topHalfWidthM'],steps*params['riseM']+.9)
        end=point(radius+steps*params['runM'],sign*params['bottomHalfWidthM'],.9)
        m.tube('silver',start,end,.07,n=4)
        for i in range(0,steps,4):
            t=i/steps;w=params['topHalfWidthM']+(params['bottomHalfWidthM']-params['topHalfWidthM'])*t;z=(steps-i)*params['riseM']
            m.tube('silver',point(radius+i*params['runM'],sign*w,z),point(radius+i*params['runM'],sign*w,z+.9),.04,n=4)


def build(b,lm,spec,scale=.6):
    if not math.isfinite(scale) or scale<=0:raise ValueError('scale must be positive and finite')
    parts,contours,offset,g=_context(lm,spec);old=b.frame;b.frame=(lm['x'],lm['z'],0);m=_Mesh(b,scale,offset,lm.get('y',0))
    try:
        ground=next(c for c in parts if c['role']=='main-ground');base=_v(spec,'platformM')
        _walls(m,'concrete',ground['ring'],0,base);_cap(m,'concrete',ground['ring'],base)
        moon=_moon(m,contours,spec);_wing(m,next(c for c in parts if c['role']=='low-wing'),spec)
        cx,cy,sample=_front(m,next(c for c in parts if c['role']=='front-cone'),spec);_stairs(m,(cx,cy),sample,spec)
    finally:b.frame=old
    if m.triangles>spec['budget']['maxTriangles'] or len(m.materials)>spec['budget']['maxMaterials']:raise ValueError('Theatre candidate exceeds CPU budget')
    return {'id':'grand-theatre','scope':spec['scope'],'moonContourCount':len(contours),'architecturalRoles':['crescent metal back','inclined glass front','two-tier inverted-conical front','mapped low wing','estimated fan stairs'],
        'sourceFeatureCoverageCount':len(spec['baseBuildingIdsToExclude']),'reportedMainHeightM':spec['reported']['mainHeightM'],
        'generatedFaces':m.faces,'triangleCountBeforeExport':m.triangles,'materials':sorted(m.materials),'newLights':0,'candidateWaterPlanes':0,
        'geographyCityId':'hangzhou','projectionOriginWGS84':g['originWGS84'],'sourceSpec':'docs/hangzhou/research/core/grand-theatre-round2/spec.json',
        'collisionStatus':'pending; source main conservative envelope only; stairs/doors/pool and terrain not accepted'}


def ground_footprints(lm,spec,scale=.6):
    parts,contours,offset,g=_context(lm,spec);ring=next(c['ring'] for c in parts if c['role']=='main-ground')
    return [[[lm['x']+(x+offset[0])*scale,lm['z']+(y+offset[1])*scale] for x,y in ring]]
