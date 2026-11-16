"""Source-bound Hangzhou Civic Center finite core candidate, no scene effects.

Mapped A-F arc towers and four L podiums, high annular connection, a lower
curved canopy with open roof garden and two mapped roof pavilion plans.
Garden, floor sections, bridge datum and entry/ground geometry are estimates.
Photographs are references only; no image textures, imported meshes or lights.
"""
from __future__ import annotations
import math

try:
    from city_config import load_city,project
except ImportError:
    from scripts.city_config import load_city,project


def _v(spec,key):return spec['estimates'][key]['value']


def _context(lm,spec):
    if spec.get('id')!='civic-center' or spec.get('cityId')!='hangzhou':raise ValueError('Civic Center needs Hangzhou spec')
    city=load_city('hangzhou');g=city['geography'];a=spec['anchor'];ax,ay=project(a['lon'],a['lat'],city)
    def ring(raw):
        if raw[0]!=raw[-1]:raise ValueError('Source ring must be closed')
        return [((x-ax)/g['scale'],(y-ay)/g['scale']) for x,y in [project(*p,city) for p in raw[:-1]]]
    parts=[dict(c,ring=ring(c['footprintWGS84'])) for c in spec['components']]
    if sum(c['role']=='tower' for c in parts)!=6 or sum(c['role']=='podium' for c in parts)!=4:raise ValueError('Need six mapped towers and four mapped podiums')
    rings=[ring(r) for r in spec['ringFootprintsWGS84']]
    lx,ly=project(lm.get('lon',a['lon']),lm.get('lat',a['lat']),city)
    return parts,rings,((ax-lx)/g['scale'],(ay-ly)/g['scale']),g


class _Mesh:
    def __init__(self,b,scale,offset,base):self.b=b;self.scale=scale;self.offset=offset;self.base=base;self.faces=0;self.triangles=0;self.materials=set()
    def point(self,p):return ((p[0]+self.offset[0])*self.scale,(p[1]+self.offset[1])*self.scale,self.base+p[2]*self.scale)
    def face(self,mat,pts):self.b.face(mat,[self.point(p) for p in pts]);self.faces+=1;self.triangles+=len(pts)-2;self.materials.add(mat)
    def box(self,mat,p,size):
        x,y,z=p;a,b,c=[v/2 for v in size];v=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        for ids in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):self.face(mat,[v[i] for i in ids])
    def tube(self,mat,a,b,r,n=4):
        d=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(v*v for v in d))
        if length<1e-8:raise ValueError('Zero-length member')
        d=[v/length for v in d];q=(0,0,1) if abs(d[2])<.9 else (1,0,0)
        u=(d[1]*q[2]-d[2]*q[1],d[2]*q[0]-d[0]*q[2],d[0]*q[1]-d[1]*q[0]);ul=math.sqrt(sum(v*v for v in u));u=[v/ul for v in u]
        v=(d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0])
        rows=[[(p[0]+r*(math.cos(i*math.tau/n)*u[0]+math.sin(i*math.tau/n)*v[0]),p[1]+r*(math.cos(i*math.tau/n)*u[1]+math.sin(i*math.tau/n)*v[1]),p[2]+r*(math.cos(i*math.tau/n)*u[2]+math.sin(i*math.tau/n)*v[2])) for i in range(n)] for p in (a,b)]
        for i in range(n):j=(i+1)%n;self.face(mat,[rows[0][i],rows[0][j],rows[1][j],rows[1][i]])
        self.face(mat,list(reversed(rows[0])));self.face(mat,rows[1])


def _cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _triangulate(raw):
    """Ear clipping for exact simple mapped plans; no fill across central holes."""
    p=list(raw)
    if sum(x*v-u*y for (x,y),(u,v) in zip(p,p[1:]+p[:1]))<0:p.reverse()
    todo=list(range(len(p)));out=[]
    while len(todo)>3:
        for j,b in enumerate(todo):
            a,c=todo[j-1],todo[(j+1)%len(todo)]
            if _cross(p[a],p[b],p[c])<=1e-8:continue
            if any(all(_cross(u,v,p[k])>=-1e-8 for u,v in ((p[a],p[b]),(p[b],p[c]),(p[c],p[a]))) for k in todo if k not in (a,b,c)):continue
            out.append([p[a],p[b],p[c]]);todo.pop(j);break
        else:raise ValueError('Unable to triangulate source plan; refuse invented cap')
    out.append([p[i] for i in todo]);return out


def _cap(m,mat,ring,z):
    for tri in _triangulate(ring):m.face(mat,[(x,y,z(x,y) if callable(z) else z) for x,y in tri])


def _walls(m,mat,ring,lo,hi):
    area=sum(x*v-u*y for (x,y),(u,v) in zip(ring,ring[1:]+ring[:1]));p=ring if area>0 else list(reversed(ring))
    for a,b in zip(p,p[1:]+p[:1]):m.face(mat,[(*a,lo),(*b,lo),(*b,hi),(*a,hi)])


def _circle(r,z,n=72,center=(0,0)):
    return [(center[0]+r*math.cos(i*math.tau/n),center[1]+r*math.sin(i*math.tau/n),z) for i in range(n)]


def _annulus(m,mat,inner,outer):
    for i in range(len(inner)):j=(i+1)%len(inner);m.face(mat,[inner[i],outer[i],outer[j],inner[j]])


def _edge_grid(m,ring,z0,z1,pitch,width,mat='silver'):
    for a,b in zip(ring,ring[1:]+ring[:1]):
        length=math.dist(a,b);count=max(1,math.ceil(length/pitch));dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
        for i in range(count):
            t=(i+.5)/count;x,y=a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
            # Outward tiny offset prevents equal-depth seam overlays.
            q=(x+.035*dy,y-.035*dx);half=width/2
            m.face(mat,[(q[0]-half*dx,q[1]-half*dy,z0),(q[0]+half*dx,q[1]+half*dy,z0),(q[0]+half*dx,q[1]+half*dy,z1),(q[0]-half*dx,q[1]-half*dy,z1)])


def _tower(m,part,spec):
    ring=part['ring'];body=_v(spec,'bodyHeightM');height=spec['reported']['towerArchitecturalHeightM'];floors=spec['reported']['towerFloorCount'];band=_v(spec,'spandrelBandM')
    for j in range(floors):
        lo,hi=j*body/floors,(j+1)*body/floors
        _walls(m,'silver',ring,lo,lo+band)
        _walls(m,'landmarkglass',ring,lo+band,hi-.12)
        _walls(m,'steel',ring,hi-.12,hi)
    _cap(m,'roof',ring,body)
    _edge_grid(m,ring,0,body,_v(spec,'mullionPitchM'),_v(spec,'mullionWidthM'))
    # Crown is an open metal lattice above occupied glassbody, not a block.
    for z in [body+.4,body+3.5,body+6.9,height-.12]:_walls(m,'silver',ring,z,z+.12)
    for a,b in zip(ring,ring[1:]+ring[:1]):
        count=max(1,math.ceil(math.dist(a,b)/4))
        for i in range(count):
            t=i/count;x,y=a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
            m.tube('steel',(x,y,body),(x,y,height),.085,n=4)


def _radial_ring(raw,n,z):
    p=sorted((math.atan2(y,x)%math.tau,math.hypot(x,y)) for x,y in raw);p.append((p[0][0]+math.tau,p[0][1]));out=[]
    for i in range(n):
        a=i*math.tau/n;q=a if a>=p[0][0] else a+math.tau
        lo,hi=next((u,v) for u,v in zip(p,p[1:]) if u[0]<=q<=v[0]);t=(q-lo[0])/(hi[0]-lo[0]);r=lo[1]+t*(hi[1]-lo[1]);out.append((r*math.cos(a),r*math.sin(a),z))
    return out


def _bridge(m,rings,spec):
    # Polar interpolation of mapped annular plan is estimated smooth curvature.
    lo,hi=_v(spec,'bridgeBottomM'),_v(spec,'bridgeTopM');n=96
    outer=_radial_ring(rings[0],n,lo);inner=_radial_ring(rings[1],n,lo)
    _annulus(m,'roof',list(reversed(inner)),list(reversed(outer)))
    _annulus(m,'roof',[(x,y,hi) for x,y,z in inner],[(x,y,hi) for x,y,z in outer])
    _walls(m,'landmarkglass',[(x,y) for x,y,z in outer],lo,hi)
    # Interior wall normal points toward courtyard.
    for i,a in enumerate(inner):b=inner[(i+1)%n];m.face('landmarkglass',[(a[0],a[1],lo),(a[0],a[1],hi),(b[0],b[1],hi),(b[0],b[1],lo)])
    for z in [lo,lo+.22,(lo+hi)/2,hi-.18]:
        _walls(m,'silver',[(x,y) for x,y,q in outer],z,z+.12)
        _walls(m,'silver',[(x,y) for x,y,q in inner],z,z+.12)
    _edge_grid(m,[(x,y) for x,y,z in outer],lo,hi,3,.10)
    _edge_grid(m,[(x,y) for x,y,z in inner],lo,hi,3,.10)


def _podium(m,part,spec):
    ring=part['ring'];height=_v(spec,'podiumHeightM');floors=int(_v(spec,'podiumFloorSamples'))
    for j in range(floors):
        lo,hi=j*height/floors,(j+1)*height/floors
        _walls(m,'darkglass',ring,lo+.25,hi-.18);_walls(m,'silver',ring,lo,lo+.25);_walls(m,'steel',ring,hi-.18,hi)
    _edge_grid(m,ring,.25,height,3.2,.1);_cap(m,'roof',ring,height)
    cx,cy=sum(x for x,y in ring)/len(ring),sum(y for x,y in ring)/len(ring)
    inset=[(cx+(x-cx)*.90,cy+(y-cy)*.90) for x,y in ring];_cap(m,'leaf',inset,height+.035)
    # Representative green roof, no scene terrain or implied stair access.


def _pavilion(m,part,spec):
    ring=part['ring'];cx,cy=sum(x for x,y in ring)/len(ring),sum(y for x,y in ring)/len(ring);deck=_v(spec,'centralDeckM')
    if part['name']=='G-roof-pavilion':
        lo=deck+.05;hi=deck+_v(spec,'domeBaseAboveDeckM');_walls(m,'darkglass',ring,lo,hi)
        # Source plan has a true round roofpart; own shallow radial dome profile.
        radii=[math.hypot(x-cx,y-cy) for x,y in ring];r=sum(radii)/len(radii);rise=_v(spec,'domeRiseM');rows=[]
        n=40
        for j in range(6):
            t=j/6;rr=r*(1-t);z=hi+rise*(1-(1-t)**2);rows.append(_circle(rr,z,n,(cx,cy)))
        for a,b in zip(rows,rows[1:]):_annulus(m,'landmarkglass',b,a)
        for i,p in enumerate(rows[-1]):m.face('landmarkglass',[p,rows[-1][(i+1)%n],(cx,cy,hi+rise)])
        for i in range(0,n,2):
            for a,b in zip(rows,rows[1:]):m.tube('silver',a[i],b[i],.05,n=4)
        _edge_grid(m,ring,lo,hi,2.6,.09)
    else:
        hi=deck+_v(spec,'ovalHeightAboveDeckM');_walls(m,'darkglass',ring,deck,hi);_edge_grid(m,ring,deck,hi,2.8,.11)
        _cap(m,'roof',ring,lambda x,y:hi+.06*(x-cx))


def _ribbon(m,points,width,z,mat='pavement'):
    for a,b in zip(points,points[1:]):
        length=math.dist(a,b);dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length;w=width/2
        m.face(mat,[(a[0]-w*dy,a[1]+w*dx,z),(a[0]+w*dy,a[1]-w*dx,z),(b[0]+w*dy,b[1]-w*dx,z),(b[0]-w*dy,b[1]+w*dx,z)])


def _tree(m,x,y,z,height):
    m.tube('bark',(x,y,z),(x,y,z+height*.64),.18,n=5);n=6;r=height*.30
    a=_circle(r*.52,z+height*.40,n,(x,y));b=_circle(r,z+height*.72,n,(x,y))
    for i in range(n):j=(i+1)%n;m.face('leaf',[a[i],a[j],b[j],b[i]]);m.face('leaf',[b[i],b[j],(x,y,z+height)])


def _garden(m,parts,spec):
    deck=_v(spec,'centralDeckM');r=_v(spec,'centralRadiusM');n=96;opening=_v(spec,'canopyInnerMeanRadiusM');waves=_v(spec,'canopyInnerWavesM');samples=_v(spec,'gardenSamples')
    outer=_circle(r,deck,n);_walls(m,'darkglass',[(x,y) for x,y,z in outer],0,deck)
    _cap(m,'leaf',[(x,y) for x,y,z in outer],deck)
    rows=[]
    for j in range(4):
        t=j/3;pts=[]
        for i in range(n):
            a=i*math.tau/n;ri=opening+waves[0]*math.sin(3*a+.5)+waves[1]*math.sin(7*a);rr=ri+(r-ri)*t
            z=deck+_v(spec,'canopyInnerHeightAboveDeckM')+(_v(spec,'canopyOuterHeightAboveDeckM')-_v(spec,'canopyInnerHeightAboveDeckM'))*math.sin(t*math.pi/2)
            pts.append((rr*math.cos(a),rr*math.sin(a),z))
        rows.append(pts)
    for a,b in zip(rows,rows[1:]):_annulus(m,'steel',a,b)
    thick=_v(spec,'canopyThicknessM')
    for edge in [rows[0],rows[-1]]:
        for i,p in enumerate(edge):q=edge[(i+1)%n];m.face('roof',[p,(p[0],p[1],p[2]-thick),(q[0],q[1],q[2]-thick),q])
    for i in range(n):
        angle=i*math.tau/n;dx,dy=-math.sin(angle)*.06,math.cos(angle)*.06
        # Combined shallow seam ribbons keep the photographed rib rhythm
        # without six capped cylinders for every strip of the low canopy.
        for a,b in zip(rows,rows[1:]):
            p,q=a[i],b[i]
            m.face('silver',[(p[0]-dx,p[1]-dy,p[2]+.06),(q[0]-dx,q[1]-dy,q[2]+.06),
                             (q[0]+dx,q[1]+dy,q[2]+.06),(p[0]+dx,p[1]+dy,p[2]+.06)])
    # Original bounded water edge and walk samples; not copied image contours.
    wr=samples['waterRadiusM'];wave=samples['waterWaveM'];water=[]
    for i in range(32):
        a=i*math.tau/32;rr=wr+wave*math.sin(3*a)+1.5*math.sin(5*a);water.append((rr*math.cos(a),rr*.70*math.sin(a)))
    _cap(m,'water',water,deck+.06);_ribbon(m,water+[water[0]],.65,deck+.095,'concrete')
    path=[]
    for i in range(45):
        a=.45+i*math.tau/44;rr=38+3*math.sin(4*a);path.append((rr*math.cos(a),rr*math.sin(a)))
    _ribbon(m,path,samples['pathWidthM'],deck+.11)
    oval=next(p for p in parts if p['name']=='roof-oval');c=(sum(x for x,y in oval['ring'])/len(oval['ring']),sum(y for x,y in oval['ring'])/len(oval['ring']))
    _ribbon(m,[(0,0),(-12,-8),(c[0],c[1])],2.0,deck+.14)
    for i in range(int(samples['treeCount'])):
        a=i*math.tau/samples['treeCount']+.3;rr=44+3*math.sin(5*a);_tree(m,rr*math.cos(a),rr*math.sin(a),deck+.04,4.0+(i%3)*.55)
    for i in range(6):
        a=.2+i*math.tau/6;x,y=31*math.cos(a),31*math.sin(a);m.box('concrete',(x,y,deck+.45),(2.4,.75,.5))
    for i in range(5):m.box('concrete',(-19+i*.85,-18,deck+.12+i*.13),(.82,4,.24))


def build(b,lm,spec,scale=.6):
    if not math.isfinite(scale) or scale<=0:raise ValueError('scale must be finite and positive')
    parts,rings,offset,g=_context(lm,spec);old=b.frame;b.frame=(lm['x'],lm['z'],0);m=_Mesh(b,scale,offset,lm.get('y',0))
    try:
        for c in parts:
            if c['role']=='tower':_tower(m,c,spec)
            elif c['role']=='podium':_podium(m,c,spec)
        _bridge(m,rings,spec);_garden(m,parts,spec)
        for c in parts:
            if c['role']=='roof-pavilion':_pavilion(m,c,spec)
    finally:b.frame=old
    if m.triangles>spec['budget']['maxTriangles'] or len(m.materials)>spec['budget']['maxMaterials']:raise ValueError('Civic Center CPU candidate exceeds budget')
    return {'id':'civic-center','scope':spec['scope'],'towerCount':6,'podiumCount':4,'roofPavilionCount':2,
        'reportedTowerHeightM':spec['reported']['towerArchitecturalHeightM'],'annularSkybridge':True,'centralGardenOpen':True,
        'generatedFaces':m.faces,'triangleCountBeforeExport':m.triangles,'materials':sorted(m.materials),'newLights':0,
        'geographyCityId':'hangzhou','projectionOriginWGS84':g['originWGS84'],'sourceSpec':'docs/hangzhou/research/core/civic-center-round2/spec.json',
        'collisionStatus':'pending; conservative ground footprints only, roofgarden/entries not verified traversable'}


def ground_footprints(lm,spec,scale=.6):
    parts,rings,offset,g=_context(lm,spec)
    plans=[c['ring'] for c in parts if c['role'] in ('tower','podium')]
    plans.append([(x,y) for x,y,z in _circle(_v(spec,'centralRadiusM'),0)])
    return [[[lm['x']+(x+offset[0])*scale,lm['z']+(y+offset[1])*scale] for x,y in ring] for ring in plans]
