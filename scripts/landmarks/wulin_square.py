"""Wulin's source-bound plaza/fountain candidate, built with shared B.face.

Original parametric sculpture geometry, not photographs or imported meshes.
The fixed map bounds/POI are source data; basin dimensions, garden placements,
poses, decorative forms and paving spacing remain documented estimates.
Importing has no Blender/scene/export side effects. No surrounding buildings.
"""
from __future__ import annotations
import math

try:
    from city_config import load_city,project
except ImportError:
    from scripts.city_config import load_city,project


def _v(spec,key):return spec['estimates'][key]['value']


def _area(ring):return sum(x*v-u*y for (x,y),(u,v) in zip(ring,ring[1:]+ring[:1]))/2


def _cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _inside(point,ring):
    x,y=point;inside=False
    for (u,v),(a,b) in zip(ring,ring[1:]+ring[:1]):
        if (v>y)!=(b>y) and x<(a-u)*(y-v)/(b-v)+u:inside=not inside
    return inside


def _triangulate(ring):
    remaining=list(range(len(ring)));out=[]
    while len(remaining)>3:
        found=False
        for j,b in enumerate(remaining):
            a,c=remaining[j-1],remaining[(j+1)%len(remaining)]
            if _cross(ring[a],ring[b],ring[c])<=1e-9:continue
            contained=any(all(_cross(ring[p],ring[q],ring[k])>=-1e-9 for p,q in ((a,b),(b,c),(c,a)))
                          for k in remaining if k not in (a,b,c))
            if not contained:
                out.append((a,b,c));remaining.pop(j);found=True;break
        if not found:raise ValueError('Mapped square polygon cannot be triangulated')
    out.append(tuple(remaining));return out


def _context(lm,spec):
    if spec.get('id')!='wulin-square' or spec.get('cityId')!='hangzhou':
        raise ValueError('Wulin builder requires the Hangzhou specification')
    city=load_city('hangzhou');geo=city['geography'];a=spec['anchor']
    ax,ay=project(a['lon'],a['lat'],city)
    raw=spec['footprintWGS84']
    if raw[0]!=raw[-1]:raise ValueError('Mapped plaza ring must be closed')
    ring=[((x-ax)/geo['scale'],(y-ay)/geo['scale']) for x,y in [project(*p,city) for p in raw[:-1]]]
    if _area(ring)<0:ring.reverse()
    fx,fy=project(*spec['fountain']['centerWGS84'],city)
    lx,ly=project(lm.get('lon',a['lon']),lm.get('lat',a['lat']),city)
    return ring,((fx-ax)/geo['scale'],(fy-ay)/geo['scale']),((ax-lx)/geo['scale'],(ay-ly)/geo['scale']),geo


class _Mesh:
    def __init__(self,b,scale,offset,base_y):
        self.b,self.scale,self.offset,self.base_y=b,scale,offset,base_y
        self.faces=self.triangles=0;self.materials=set()
    def point(self,p):
        return ((p[0]+self.offset[0])*self.scale,(p[1]+self.offset[1])*self.scale,p[2]*self.scale+self.base_y)
    def face(self,mat,points):
        self.b.face(mat,[self.point(p) for p in points]);self.faces+=1;self.triangles+=len(points)-2;self.materials.add(mat)
    def box(self,mat,p,s):
        x,y,z=p;a,b,c=[q/2 for q in s]
        q=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
           (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        for ids in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):self.face(mat,[q[i] for i in ids])
    def tube(self,mat,a,b,r,n=6,r2=None):
        d=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(v*v for v in d))
        if length<1e-8:raise ValueError('Zero-length sculpture member')
        d=[v/length for v in d];q=(0,0,1) if abs(d[2])<.9 else (1,0,0)
        u=(d[1]*q[2]-d[2]*q[1],d[2]*q[0]-d[0]*q[2],d[0]*q[1]-d[1]*q[0]);ul=math.sqrt(sum(v*v for v in u));u=[v/ul for v in u]
        v=(d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0]);rows=[]
        for p,rr in ((a,r),(b,r if r2 is None else r2)):
            rows.append([tuple(p[k]+rr*(math.cos(i*math.tau/n)*u[k]+math.sin(i*math.tau/n)*v[k]) for k in range(3)) for i in range(n)])
        _shell(self,mat,rows)


class _Sculpt:
    def __init__(self,mesh,center,angle=0,scale=1):self.m,self.center,self.angle,self.scale=mesh,center,angle,scale
    def pt(self,p):
        x,y,z=[v*self.scale for v in p];c,s=math.cos(self.angle),math.sin(self.angle)
        return (self.center[0]+x*c-y*s,self.center[1]+x*s+y*c,self.center[2]+z)
    def face(self,mat,points):self.m.face(mat,[self.pt(p) for p in points])
    def tube(self,mat,a,b,r,n=6,r2=None):self.m.tube(mat,self.pt(a),self.pt(b),r*self.scale,n,None if r2 is None else r2*self.scale)
    def box(self,mat,p,size):
        x,y,z=p;a,b,c=[q/2 for q in size]
        q=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
           (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        for ids in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):self.face(mat,[q[i] for i in ids])


def _shell(m,mat,rows,cap=True):
    for a,b in zip(rows,rows[1:]):
        for i in range(len(a)):
            j=(i+1)%len(a);m.face(mat,[a[i],a[j],b[j],b[i]])
    if cap:m.face(mat,list(reversed(rows[0])));m.face(mat,rows[-1])


def _ellipse(x,y,z,rx,ry,n=12,fold=0):
    return [(x+rx*(1+fold*math.cos(5*i*math.tau/n))*math.cos(i*math.tau/n),
             y+ry*(1+fold*math.cos(5*i*math.tau/n))*math.sin(i*math.tau/n),z) for i in range(n)]


def _ovoid(m,mat,p,size,n=10):
    x,y,z=p;rx,ry,rz=size;rows=[]
    # Small nonzero polar rings give stable closed faces and no collapsed quads.
    for j in range(1,6):
        a=math.pi*j/6;rows.append(_ellipse(x,y,z+rz*math.cos(a),rx*math.sin(a),ry*math.sin(a),n))
    _shell(m,mat,list(reversed(rows)))


def _ribbon(m,points,width=.28,thick=.065):
    rows=[]
    for i,p in enumerate(points):
        a,b=points[i-1],points[(i+1)%len(points)];dx,dz=b[0]-a[0],b[2]-a[2];length=math.hypot(dx,dz)
        nx,nz=dz/length*width/2,-dx/length*width/2
        rows.append([(p[0]-nx,p[1]-thick/2,p[2]-nz),(p[0]+nx,p[1]-thick/2,p[2]+nz),
                     (p[0]+nx,p[1]+thick/2,p[2]+nz),(p[0]-nx,p[1]+thick/2,p[2]-nz)])
    for a,b in zip(rows,rows[1:]+rows[:1]):
        for j in range(4):k=(j+1)%4;m.face('roadline',[a[j],a[k],b[k],b[j]])


def _dancer(m,x,y,variant):
    lean=(-.18,.10,.22)[variant];high=(3.75,4.1,3.9)[variant]
    _shell(m,'roadline',[_ellipse(x,y,.12,.52,.30,12,.04),_ellipse(x+lean*.3,y,.85,.72,.29,12,.08),
                          _ellipse(x+lean*.8,y,2.5,.22,.18,12),_ellipse(x+lean,y,3.25,.34,.20,12),
                          _ellipse(x+lean,y,high-.35,.20,.16,12)])
    m.tube('roadline',(x+lean,y,high-.4),(x+lean,y,high-.18),.14)
    _ovoid(m,'roadline',(x+lean,y-.015,high),(.25,.21,.31))
    _ovoid(m,'roadline',(x+lean,y+.13,high+.04),(.24,.18,.25),n=8)
    # Varied upward arm gestures converge into the overhead silk loop.
    left=[(x-.24,y,3.28),(x-.74,y-.08,4.10),(x-.92,y-.03,4.75 if variant else 5.30)]
    right=[(x+.24,y,3.28),(x+.72,y+.10,3.70 if variant==0 else 4.5),(x+.92,y+.02,4.05 if variant==0 else 5.45)]
    for arm in (left,right):
        for a,b in zip(arm,arm[1:]):m.tube('roadline',a,b,.13,n=6,r2=.105)
        _ovoid(m,'roadline',arm[-1],(.13,.11,.14),n=8)
    # Flowing hair swept backward, an original simplified volume.
    _shell(m,'roadline',[_ellipse(x+lean,y+.12,high+.15,.22,.18,8),
                          _ellipse(x+lean+.2,y+.4,high-.1,.28,.12,8),
                          _ellipse(x+lean+.65,y+.65,high-.2,.06,.06,8)])


def _central_group(m,center,z,spec):
    x,y=center;pedestal=_v(spec,'centralPedestalHeightM')
    _shell(m,'roadline',[_ellipse(x,y,z,2.3,2.3,24),_ellipse(x,y,z+pedestal,2.05,2.05,24)])
    # Max raw silk-loop height is 6.60m; scale to source-reported approximate
    # 7m group including the pedestal, not an asserted pose measurement.
    s=(_v(spec,'centralGroupHeightM')-pedestal)/6.6
    group=_Sculpt(m,(x,y,z+pedestal),scale=s)
    for i,(u,v) in enumerate(((-1.08,-.25),(0,.50),(1.06,-.22))):_dancer(group,u,v,i)
    points=[(2.55*math.cos(i*math.tau/48),.20*math.sin(2*i*math.tau/48),4.85+1.6*math.sin(i*math.tau/48)) for i in range(48)]
    _ribbon(group,points,width=.30)
    # A second wavy loop/strand gives the characteristic open double arc.
    points=[(2.30*math.cos(i*math.tau/40),.25+.16*math.sin(i*math.tau/40),4.68+1.18*math.sin(i*math.tau/40)+.12*math.sin(3*i*math.tau/40)) for i in range(40)]
    _ribbon(group,points,width=.22)


def _instrument(m,kind):
    if kind=='pipa':
        _ovoid(m,'roadline',(.1,-.38,1.70),(.40,.12,.58),12)
        m.tube('roadline',(.1,-.38,1.92),(-.35,-.38,2.88),.09,n=6)
    elif kind=='sheng':
        _ovoid(m,'roadline',(.12,-.42,2.05),(.24,.14,.25),8)
        for i in range(6):m.tube('roadline',(-.14+i*.08,-.44,2.03),(-.14+i*.08,-.44,2.48+abs(i-2.5)*.12),.026,n=4)
    elif kind=='guzheng':
        m.box('roadline',(0,-.55,1.08),(1.65,.55,.18))
        for i in range(6):m.tube('roadline',(-.73,-.77+i*.07,1.2),(.73,-.77+i*.07,1.2),.012,n=4)
    elif kind=='konghou':
        frame=[(-.40,-.36,1.25),(.52,-.36,1.25),(-.30,-.36,2.75)]
        for a,b in zip(frame,frame[1:]+frame[:1]):m.tube('roadline',a,b,.07,n=6)
        for i in range(1,6):
            t=i/6;m.tube('roadline',(-.4+.92*t,-.36,1.25),(-.4+.92*t,-.36,2.75-1.5*t),.018,n=4)
    elif kind=='flute':m.tube('roadline',(-.58,-.40,2.42),(.75,-.40,2.52),.045,n=6)


def _musician(m,center,z,angle,kind,spec):
    x,y=center;pedestal=_v(spec,'outerPedestalHeightM')
    _shell(m,'roadline',[_ellipse(x,y,z,.95,.95,16),_ellipse(x,y,z+pedestal,.88,.88,16)])
    figure=_Sculpt(m,(x,y,z+pedestal),angle,(_v(spec,'outerGroupHeightM')-pedestal)/2.98)
    # Bent, seated/crouching figure, with draped skirts rather than a vertical
    # column. Instruments and gestures differ; exact clockwise assignment pending.
    _shell(figure,'roadline',[_ellipse(.05,0,.06,.69,.48,12,.05),_ellipse(.1,-.1,.45,.80,.47,12,.07),
                              _ellipse(0,.1,.92,.45,.32,12),_ellipse(0,.1,1.42,.23,.19,12),
                              _ellipse(-.05,.08,2.14,.32,.21,12)])
    _ovoid(figure,'roadline',(-.06,.02,2.53),(.25,.21,.32),10)
    figure.tube('roadline',(-.04,.08,2.08),(-.06,.02,2.35),.13,n=6)
    _ovoid(figure,'roadline',(-.03,.17,2.60),(.28,.19,.30),8)
    arms=(((-.28,0,2.06),(-.48,-.34,1.73),(-.20,-.51,1.61)),
          ((.28,0,2.06),(.52,-.24,2.27),(.38,-.43,2.45)))
    if kind=='flute':arms=(((-.28,0,2.06),(-.57,-.20,2.30),(-.40,-.40,2.44)),((.28,0,2.06),(.58,-.20,2.30),(.51,-.40,2.48)))
    for arm in arms:
        for a,b in zip(arm,arm[1:]):figure.tube('roadline',a,b,.12,n=6,r2=.10)
        _ovoid(figure,'roadline',arm[-1],(.11,.10,.13),8)
    _instrument(figure,kind)


def _clover(radius,amplitude,z,center,n=100,angle=math.pi/2):
    return [(center[0]+(radius+amplitude*math.cos(5*(t-angle)))*math.cos(t),
             center[1]+(radius+amplitude*math.cos(5*(t-angle)))*math.sin(t),z) for t in [i*math.tau/n for i in range(n)]]


def _annulus(m,mat,a,b):
    for i in range(len(a)):
        j=(i+1)%len(a);m.face(mat,[a[i],b[i],b[j],a[j]])


def _fountain(m,center,spec):
    f=spec['fountain'];r=_v(spec,'poolMeanRadiusM');amp=_v(spec,'poolLobeAmplitudeM');height=_v(spec,'raisedPoolHeightM')
    moat=_v(spec,'moatWidthM');taper=_v(spec,'poolTopRadiusFactor');topr=r*taper;topamp=amp*taper
    base=_clover(r,amp,.12,center);top=_clover(topr,topamp,height,center)
    _shell(m,'roof',[base,top],cap=False)
    # Shallow water ring around the raised five-petal bowl, visible in 2026.
    outer=_clover(r+moat,amp,.13,center)
    _annulus(m,'water',base,outer)
    _annulus(m,'steel',outer,_clover(r+moat+.38,amp,.14,center))
    _annulus(m,'steel',top,_clover(topr-.3,topamp,height,center))
    surface=_clover(topr-.32,topamp,height-.06,center)
    c=(*center,height-.06)
    for i,p in enumerate(surface):m.face('water',[c,p,surface[(i+1)%len(surface)]])
    # Representative dark tiled wall courses, not per-brick objects.
    for i in range(1,6):
        h=.12+(height-.12)*i/6;ratio=1+(taper-1)*(h-.12)/(height-.12)
        _shell(m,'concrete',[_clover(r*ratio+.008,amp*ratio,h,center),
                             _clover(r*ratio+.008,amp*ratio,h+.018,center)],cap=False)
    _central_group(m,center,height,spec)
    positions=[]
    angle=math.radians(_v(spec,'petalAxisAngleDegrees'))
    instruments=spec['fountain']['outerInstrumentsClockwiseEstimated']
    for i,kind in enumerate(instruments):
        a=angle-i*math.tau/5;distance=_v(spec,'outerStatueRadiusM');p=(center[0]+distance*math.cos(a),center[1]+distance*math.sin(a))
        _musician(m,p,height,a+math.pi/2,kind,spec);positions.append({'instrument':kind,'centerRealEN':list(p)})
    # A bounded nozzle representation. Performance and active jets are deferred.
    for i in range(25):
        a=i*math.tau/25;distance=8.3
        m.tube('steel',(center[0]+distance*math.cos(a),center[1]+distance*math.sin(a),height-.08),
               (center[0]+distance*math.cos(a),center[1]+distance*math.sin(a),height+.04),.045,n=4)
    return positions


def _paving(m,ring,center,spec):
    for a,b,c in _triangulate(ring):m.face('pavement',[(*ring[i],.05) for i in (a,b,c)])
    # Source-visible broad concentric apron and radial paving, not an empty slab.
    r=_v(spec,'apronRadiusM');x,y=center
    for radius in (r-3.2,r-1.6,r):
        a=_ellipse(x,y,.073,radius,radius,100);b=_ellipse(x,y,.073,radius+.08,radius+.08,100)
        _annulus(m,'concrete',a,b)
    inner=_v(spec,'poolMeanRadiusM')+_v(spec,'poolLobeAmplitudeM')+_v(spec,'moatWidthM')+.6
    for i in range(40):
        a=i*math.tau/40;c,s=math.cos(a),math.sin(a);w=.025
        m.face('concrete',[(x+inner*c-w*s,y+inner*s+w*c,.072),(x+r*c-w*s,y+r*s+w*c,.072),
                           (x+r*c+w*s,y+r*s-w*c,.072),(x+inner*c+w*s,y+inner*s-w*c,.072)])
    # North/south approach bands are clipped to the actual mapped plaza ring.
    lo,hi=min(p[1] for p in ring),max(p[1] for p in ring)
    for yy in [lo+i*3 for i in range(int((hi-lo)/3)+1)]:
        if abs(yy-y)<r+1:continue
        for xx in (x-7,x+7):
            pts=[(xx-.40,yy),(xx+.40,yy),(xx+.40,yy+2.8),(xx-.40,yy+2.8)]
            if all(_inside(p,ring) for p in pts):m.face('concrete',[(*p,.071) for p in pts])


def _planters(m,ring,center,spec):
    # Sparse source-informed near-field samples of the reported flower pots;
    # not a claim that all 100+ real pots or their exact current positions match.
    count=0
    for side in (-1,1):
        for j in range(10):
            x=center[0]+side*(34+(j%2)*2.4);y=center[1]-35+j*7
            if not _inside((x,y),ring):continue
            _shell(m,'civicred',[_ellipse(x,y,.05,.40,.40,10),_ellipse(x,y,.60,.58,.58,10),_ellipse(x,y,.67,.58,.58,10)])
            _shell(m,'bark',[_ellipse(x,y,.68,.50,.50,10),_ellipse(x,y,.695,.50,.50,10)])
            for k in range(3):
                a=k*math.tau/3;u,v=x+.2*math.cos(a),y+.2*math.sin(a)
                _ovoid(m,'leaf',(u,v,.91),(.38,.35,.31),8)
                _ovoid(m,'civicred',(u,v,1.11),(.28,.24,.20),6)
            count+=1
    return count


def build(b,lm,spec,scale=.6):
    if not math.isfinite(scale) or scale<=0:raise ValueError('scale must be positive and finite')
    ring,center,offset,geo=_context(lm,spec)
    previous=b.frame;b.frame=(lm['x'],lm['z'],0);m=_Mesh(b,scale,offset,lm.get('y',0))
    try:
        _paving(m,ring,center,spec);positions=_fountain(m,center,spec);pots=_planters(m,ring,center,spec)
    finally:b.frame=previous
    if m.triangles>spec['budget']['maxTriangles'] or len(m.materials)>spec['budget']['maxMaterials']:
        raise ValueError(f'Wulin candidate exceeds budget: {m.triangles} triangles')
    return {'id':'wulin-square','scope':spec['scope'],'centralDancerCount':3,'outerMusicianCount':5,
            'poolPetalCount':5,'flowerPotSamples':pots,'outerMusicians':positions,
            'generatedFaces':m.faces,'triangleCountBeforeExport':m.triangles,'materials':sorted(m.materials),
            'newLights':0,'photosUsedAsTextures':False,'geographyCityId':'hangzhou','projectionOriginWGS84':geo['originWGS84'],
            'sourceSpec':'docs/hangzhou/research/core/wulin-round2/spec.json',
            'pending':'actual GLB, named visual review, terrain/arrival/collision, full gardens/forecourt/nearby buildings, jets/lighting and performance'}


def ground_footprints(lm,spec,scale=.6):
    """Raised fountain envelope only; an open plaza is not a building collider."""
    _,center,offset,_=_context(lm,spec)
    r=_v(spec,'poolMeanRadiusM')+_v(spec,'moatWidthM')+.38
    ring=_clover(r,_v(spec,'poolLobeAmplitudeM'),0,center)
    return [[[lm['x']+(x+offset[0])*scale,lm['z']+(y+offset[1])*scale] for x,y,z in ring]]


def plaza_outline(lm,spec,scale=.6):
    ring,_,offset,_=_context(lm,spec)
    return [[lm['x']+(x+offset[0])*scale,lm['z']+(y+offset[1])*scale] for x,y in ring]
