"""Source-bound Little Lotus static exterior/bowl candidate; no scene exports.

24 fixed envelope petals use the actual mapped tip phase/plan radii. Eight upper
petals are an explicitly estimated OPEN static profile, not a simulation of
the real rotating mechanism and not an implemented game roof interaction.
No photograph textures, imported meshes, city_mesh or bpy side effects.
"""
from __future__ import annotations
import math

try:
    from city_config import load_city,project
except ImportError:
    from scripts.city_config import load_city,project


def _v(spec,key):return spec['estimates'][key]['value']


def _context(lm,spec):
    if spec.get('id')!='little-lotus' or spec.get('cityId')!='hangzhou':raise ValueError('Little Lotus requires Hangzhou spec')
    if spec['roof']['state']!='open-static':raise ValueError('Only the documented static open-reference candidate exists')
    city=load_city('hangzhou');g=city['geography'];a=spec['anchor'];ax,ay=project(a['lon'],a['lat'],city)
    raw=spec['footprintWGS84']
    if raw[0]!=raw[-1] or len(raw)!=49:raise ValueError('Little Lotus requires the mapped closed48-point outline')
    ring=[((x-ax)/g['scale'],(y-ay)/g['scale']) for x,y in [project(*p,city) for p in raw[:-1]]]
    area=sum(x*v-u*y for (x,y),(u,v) in zip(ring,ring[1:]+ring[:1]))/2
    if area<=0:raise ValueError('Expected mapped CCW little-lotus ring')
    lx,ly=project(lm.get('lon',a['lon']),lm.get('lat',a['lat']),city)
    return ring,((ax-lx)/g['scale'],(ay-ly)/g['scale']),g


class _Mesh:
    def __init__(self,b,scale,offset,base_y):
        self.b,self.scale,self.offset,self.base_y=b,scale,offset,base_y
        self.faces=self.triangles=0;self.materials=set()
    def point(self,p):return ((p[0]+self.offset[0])*self.scale,(p[1]+self.offset[1])*self.scale,p[2]*self.scale+self.base_y)
    def face(self,mat,points):
        self.b.face(mat,[self.point(p) for p in points]);self.faces+=1;self.triangles+=len(points)-2;self.materials.add(mat)
    def box(self,mat,p,s):
        x,y,z=p;a,b,c=[q/2 for q in s];v=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
                                       (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        for ids in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):self.face(mat,[v[i] for i in ids])
    def tube(self,mat,a,b,r,n=4):
        d=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(v*v for v in d))
        if length<1e-8:raise ValueError('Zero-length roof/bowl member')
        d=[v/length for v in d];q=(0,0,1) if abs(d[2])<.9 else (1,0,0)
        u=(d[1]*q[2]-d[2]*q[1],d[2]*q[0]-d[0]*q[2],d[0]*q[1]-d[1]*q[0]);ul=math.sqrt(sum(v*v for v in u));u=[v/ul for v in u]
        v=(d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0]);rows=[]
        for p in (a,b):rows.append([tuple(p[k]+r*(math.cos(i*math.tau/n)*u[k]+math.sin(i*math.tau/n)*v[k]) for k in range(3)) for i in range(n)])
        _shell(self,mat,rows)


def _circle(radius,z,n=72):return [(radius*math.cos(i*math.tau/n),radius*math.sin(i*math.tau/n),z) for i in range(n)]


def _shell(m,mat,rows,cap=True):
    for a,b in zip(rows,rows[1:]):
        for i in range(len(a)):
            j=(i+1)%len(a);m.face(mat,[a[i],a[j],b[j],b[i]])
    if cap:m.face(mat,list(reversed(rows[0])));m.face(mat,rows[-1])


def _annulus(m,mat,a,b):
    for i in range(len(a)):
        j=(i+1)%len(a);m.face(mat,[a[i],b[i],b[j],a[j]])


def _panel(m,rows,thickness=.28):
    """Closed thin curved panel; underside stays visible without PBR changes."""
    lower=[[(x,y,z-thickness) for x,y,z in row] for row in rows]
    for i in range(len(rows)-1):
        for j in range(len(rows[0])-1):
            top=[rows[i][j],rows[i][j+1],rows[i+1][j+1],rows[i+1][j]]
            bottom=[lower[i][j],lower[i][j+1],lower[i+1][j+1],lower[i+1][j]]
            m.face('silver',top);m.face('concrete',list(reversed(bottom)))
    perimeter=rows[0]+[r[-1] for r in rows[1:]]+list(reversed(rows[-1][:-1]))+[r[0] for r in reversed(rows[1:-1])]
    for p,q in zip(perimeter,perimeter[1:]+perimeter[:1]):
        m.face('steel',[p,(p[0],p[1],p[2]-thickness),(q[0],q[1],q[2]-thickness),q])


def _mix(a,b,t):return tuple(x+(y-x)*t for x,y in zip(a,b))


def _fixed_profile(s,radius,spec):
    # Each record is [path fraction, radius factor, height, half angular width].
    rows=_v(spec,'fixedPetalSections')
    for a,b in zip(rows,rows[1:]):
        if s<=b[0]:return _mix(a[1:],b[1:],(s-a[0])/(b[0]-a[0]))
    return tuple(rows[-1][1:])


def _fixed_petals(m,ring,spec):
    inner=_v(spec,'openingRadiusM');twist=math.radians(_v(spec,'fixedPetalTwistDegrees'))
    for i,p in enumerate(ring[::2]):
        radius=math.hypot(*p);angle=math.atan2(p[1],p[0]);rows=[]
        for j in range(11):
            s=j/10;factor,z,half=_fixed_profile(s,radius,spec)
            rr=inner+(radius-inner)*factor
            row=[]
            for k in range(5):
                v=-1+k/2;a=angle+twist*s+math.radians(half)*v
                h=z-_v(spec,'fixedPetalCrossCamberM')*v*v*math.sin(math.pi*s)
                row.append((rr*math.cos(a),rr*math.sin(a),h))
            rows.append(row)
        _panel(m,rows,_v(spec,'panelThicknessM'))
        # Centerline truss/ridge is bounded; seam schedule remains estimated.
        for a,b in zip(rows,rows[1:]):m.tube('steel',a[2],b[2],.14,n=4)


def _upper_point(s,v,angle,spec):
    wave=math.sin(math.pi*s);profile=_v(spec,'upperStaticProfile')
    r=(_v(spec,'openingRadiusM')+profile['radialSineM']*wave+profile['radialLinearM']*s
       +(profile['minimumEndHalfWidthM']+profile['radialAcrossSineM']*wave)*v)
    a=angle+profile['angularStartRadians']+profile['angularSweepRadians']*s
    z=(_v(spec,'upperRoofBaseM')+(_v(spec,'candidateHeightM')-_v(spec,'upperRoofBaseM'))
       *wave*(1-profile['heightCrossCamberFactor']*v*v))
    return r*math.cos(a),r*math.sin(a),z


def _upper_petals(m,spec,phase):
    points=[]
    for i in range(8):
        angle=phase+i*math.tau/8
        rows=[[_upper_point(j/12,-1+k/2,angle,spec) for k in range(5)] for j in range(13)]
        _panel(m,rows,_v(spec,'panelThicknessM'))
        for a,b in zip(rows,rows[1:]):m.tube('steel',(a[2][0],a[2][1],a[2][2]-.48),(b[2][0],b[2][1],b[2][2]-.48),.18,n=4)
        # Ends remain a finite width at the leaf root; no collapsed quads.
        points.extend(p for row in rows for p in row)
    return min(math.hypot(x,y) for x,y,z in points)


def _base(m,ring,spec):
    deck=_v(spec,'podiumHeightM');inner=.80
    bottom=[(x,y,0) for x,y in ring];outer=[(x,y,deck) for x,y in ring]
    _shell(m,'concrete',[bottom,outer],cap=False)
    for i,p in enumerate(bottom):m.face('concrete',[(0,0,0),bottom[(i+1)%len(bottom)],p])
    _annulus(m,'concrete',[(x*inner,y*inner,deck) for x,y in ring],outer)
    # Low glazed concourse behind the actual envelope's tips, no extra building.
    _shell(m,'darkglass',[_circle(55,deck),_circle(55,12.4)],cap=False)
    for i in range(24):
        a=i*math.tau/24;x,y=55.05*math.cos(a),55.05*math.sin(a)
        m.tube('silver',(x,y,deck),(x,y,12.4),.12,n=4)
    # Eight visual portal heads between petals; positions and clearances are
    # explicitly approximate and do not cut verified traversable door holes.
    phase=math.atan2(ring[0][1],ring[0][0])
    for i in range(8):
        a=phase+i*math.tau/8+.1;c,s=math.cos(a),math.sin(a)
        lo,hi=(55.15*c-3*s,55.15*s+3*c),(55.15*c+3*s,55.15*s-3*c)
        m.face('concrete',[(lo[0],lo[1],deck+3.7),(hi[0],hi[1],deck+3.7),
                           (hi[0],hi[1],deck+4.3),(lo[0],lo[1],deck+4.3)])


def _court(m,spec):
    z=.25;w,l=10.97,23.77;singles=8.23;service=6.40
    m.box('carpaint',(0,0,z-.09),(20,36,.18))
    m.face('landmarkglass',[(-w/2,-l/2,z+.01),(w/2,-l/2,z+.01),(w/2,l/2,z+.01),(-w/2,l/2,z+.01)])
    for x in (-w/2,-singles/2,singles/2,w/2):m.box('roadline',(x,0,z+.022),(.05,l,.025))
    for y in (-l/2,l/2):m.box('roadline',(0,y,z+.022),(w,.06,.025))
    for y in (-service,service):m.box('roadline',(0,y,z+.022),(singles,.05,.025))
    m.box('roadline',(0,0,z+.022),(.05,service*2,.025))
    # Thin bounded mesh depiction, no cloth/ball physics or tennis gameplay.
    net_half=w/2+.914
    for x in (-net_half,net_half):m.tube('steel',(x,0,z),(x,0,z+1.07),.045,n=4)
    m.tube('roadline',(-net_half,0,z+1.07),(0,0,z+.914),.022,n=4)
    m.tube('roadline',(0,0,z+.914),(net_half,0,z+1.07),.022,n=4)
    for i in range(25):
        x=-net_half+i*net_half*2/24;top=.914+abs(x)/net_half*.156
        m.tube('steel',(x,0,z+.08),(x,0,z+top),.007,n=4)


def _bowl(m,spec):
    # Continuous representative seat bands avoid 10,000 individual chair meshes.
    rows=int(_v(spec,'upperSeatRowSamples'));n=64
    for j in range(rows):
        r0=34+j*.78;r1=r0+.73;z=14+j*.38
        a,b=_circle(r0,z,n),_circle(r1,z,n)
        for i in range(n):
            q=(i+1)%n
            if i%8==0:
                m.face('concrete',[a[i],b[i],b[q],a[q]])
                continue
            m.face('civicred',[a[i],b[i],b[q],a[q]])
            m.face('civicred',[(a[q][0],a[q][1],z-.32),(a[i][0],a[i][1],z-.32),a[i],a[q]])
    _annulus(m,'concrete',_circle(30,13.6,n),_circle(34,13.6,n))
    _shell(m,'concrete',[_circle(52.8,14,n),_circle(52.8,24,n)],cap=False)
    # Lower grey movable seating is represented as four short stepped blocks.
    for side in (-1,1):
        for j in range(8):
            y=side*(20+j*.82);m.box('concrete',(0,y,.48+j*.35),(16,.78,.32))
            x=side*(12.2+j*.82);m.box('concrete',(x,0,.48+j*.35),(.78,24,.32))
    # Upper bowl supports and a dark circular opening reveal the actual arena.
    _shell(m,'roof',[_circle(54.0,24,n),_circle(54.0,35.7,n)],cap=False)
    _annulus(m,'concrete',_circle(_v(spec,'openingRadiusM'),35.6,n),_circle(_v(spec,'openingRadiusM')+.6,35.6,n))


def build(b,lm,spec,scale=.6):
    if not math.isfinite(scale) or scale<=0:raise ValueError('scale must be positive and finite')
    ring,offset,geo=_context(lm,spec);previous=b.frame;b.frame=(lm['x'],lm['z'],0)
    m=_Mesh(b,scale,offset,lm.get('y',0));phase=math.atan2(ring[0][1],ring[0][0])
    try:
        _base(m,ring,spec);_court(m,spec);_bowl(m,spec);_fixed_petals(m,ring,spec)
        opening=_upper_petals(m,spec,phase+math.radians(_v(spec,'upperPetalPhaseDegrees')))
    finally:b.frame=previous
    if m.triangles>spec['budget']['maxTriangles'] or len(m.materials)>spec['budget']['maxMaterials']:
        raise ValueError(f'Little Lotus candidate exceeds budget: {m.triangles} triangles')
    return {'id':'little-lotus','scope':spec['scope'],'fixedPetalCount':24,'upperPetalCount':8,
            'roofState':'open-static','roofAnimationImplemented':False,'mechanicalAxesVerified':False,
            'upperPetalMinimumPlanRadiusM':opening,'candidateHeightM':_v(spec,'candidateHeightM'),
            'generatedFaces':m.faces,'triangleCountBeforeExport':m.triangles,'materials':sorted(m.materials),
            'newLights':0,'geographyCityId':'hangzhou','projectionOriginWGS84':geo['originWGS84'],
            'sourceSpec':'docs/hangzhou/research/core/little-lotus-round2/spec.json',
            'collisionStatus':'pending; mapped conservative envelope only, portals not traversability acceptance'}


def ground_footprints(lm,spec,scale=.6):
    ring,offset,_=_context(lm,spec)
    return [[[lm['x']+(x+offset[0])*scale,lm['z']+(y+offset[1])*scale] for x,y in ring]]
