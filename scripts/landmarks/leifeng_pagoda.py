"""Source-bound Leifeng exterior candidate; importing does not touch a scene.

Mapped octagonal base comes from fixed Hangzhou OSM; tower sections, roofs and
decoration are estimates documented in leifeng-round2/spec.json. This is not a
survey, GLB export, terrain reconstruction or full visual acceptance. No photos
are loaded or used as textures. The caller owns B.finish and export.
"""
from __future__ import annotations
import math

try:
    from city_config import load_city, project
except ImportError:
    from scripts.city_config import load_city, project


def _value(spec, key):
    return spec['estimates'][key]['value']


def _context(lm, spec):
    if spec.get('id') != 'leifeng-pagoda' or spec.get('cityId') != 'hangzhou':
        raise ValueError('Leifeng builder requires the Hangzhou specification')
    city = load_city('hangzhou')
    geo = city['geography']
    anchor = spec['anchor']
    ax, ay = project(anchor['lon'], anchor['lat'], city)
    source = spec['base']['footprintWGS84']
    if source[0] != source[-1] or len(source) != 9:
        raise ValueError('Leifeng mapped base must be a closed eight-corner ring')
    ring = [((x-ax)/geo['scale'], (y-ay)/geo['scale']) for x,y in [project(*p,city) for p in source[:-1]]]
    area = sum(x*v-u*y for (x,y),(u,v) in zip(ring,ring[1:]+ring[:1]))/2
    if abs(area) < 1:
        raise ValueError('Mapped base has no valid area')
    if area < 0:
        ring.reverse()
    lx, ly = project(lm.get('lon',anchor['lon']), lm.get('lat',anchor['lat']), city)
    offset = ((ax-lx)/geo['scale'], (ay-ly)/geo['scale'])
    return ring, offset, geo


class _Mesh:
    """Transform real metres once, leaving lm's game-unit base height alone."""
    def __init__(self,b,scale,offset,base_y):
        self.b,self.scale,self.offset,self.base_y = b,scale,offset,base_y
        self.faces = self.triangles = 0
        self.materials = set()

    def point(self,p):
        x,y,z = p
        return ((x+self.offset[0])*self.scale, (y+self.offset[1])*self.scale,
                z*self.scale+self.base_y)

    def face(self,mat,points):
        self.b.face(mat,[self.point(p) for p in points])
        self.faces += 1
        self.triangles += len(points)-2
        self.materials.add(mat)

    def box(self,mat,p,s):
        x,y,z=p
        a,b,c=[v/2 for v in s]
        q=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
           (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        for ids in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.face(mat,[q[i] for i in ids])

    def tube(self,mat,a,b,r,n=6,r2=None):
        d=[b[i]-a[i] for i in range(3)]
        length=math.sqrt(sum(v*v for v in d))
        if length < 1e-8:
            raise ValueError('Zero-length architectural member')
        d=[v/length for v in d]
        q=(0,0,1) if abs(d[2]) < .9 else (1,0,0)
        u=(d[1]*q[2]-d[2]*q[1], d[2]*q[0]-d[0]*q[2], d[0]*q[1]-d[1]*q[0])
        ul=math.sqrt(sum(v*v for v in u));u=[v/ul for v in u]
        v=(d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0])
        rows=[]
        for p,rr in ((a,r),(b,r if r2 is None else r2)):
            rows.append([tuple(p[k]+rr*(math.cos(i*math.tau/n)*u[k]+math.sin(i*math.tau/n)*v[k]) for k in range(3)) for i in range(n)])
        for i in range(n):
            j=(i+1)%n
            self.face(mat,[rows[0][i],rows[0][j],rows[1][j],rows[1][i]])
        self.face(mat,list(reversed(rows[0])));self.face(mat,rows[1])


def _octagon(radius,z,rotation):
    return [(radius*math.cos(rotation+i*math.tau/8),radius*math.sin(rotation+i*math.tau/8),z) for i in range(8)]


def _shell(m,mat,rows,cap=True):
    for low,high in zip(rows,rows[1:]):
        for i in range(len(low)):
            j=(i+1)%len(low)
            m.face(mat,[low[i],low[j],high[j],high[i]])
    if cap:
        m.face(mat,list(reversed(rows[0])));m.face(mat,rows[-1])


def _at(a,b,t):
    return tuple(x+(y-x)*t for x,y in zip(a,b))


def _rails(m,radius,z,rotation,mat='gold',subdivisions=4):
    ring=_octagon(radius,z,rotation)
    for i,a in enumerate(ring):
        b=ring[(i+1)%8]
        for lift in (.36,1.05):
            m.tube(mat,(a[0],a[1],z+lift),(b[0],b[1],z+lift),.075,n=4)
        for j in range(subdivisions):
            x,y,_=_at(a,b,j/subdivisions)
            m.tube(mat,(x,y,z),(x,y,z+1.18),.085,n=4)


def _roof(m,outer,inner,z,top,rotation,lift,thickness=.18):
    """Closed, concave octagonal roof, with local upsweep at eight corners."""
    radii=(outer,outer*.92,(outer+inner)/2,inner)
    heights=(z,z+.32,z+(top-z)*.38,top)
    rows=[]
    # Four subdivisions per side preserve curved edge/corner silhouette.
    for row_index,(radius,height) in enumerate(zip(radii,heights)):
        vertices=_octagon(radius,height,rotation)
        row=[]
        for i,a in enumerate(vertices):
            b=vertices[(i+1)%8]
            for j in range(4):
                t=j/4
                x,y,_=_at(a,b,t)
                corner=(2*abs(t-.5))**4
                up=lift*corner if row_index==0 else 0
                row.append((x,y,height+up))
        rows.append(row)
    under=[[(x,y,h-thickness) for x,y,h in row] for row in rows]
    for high,low in ((rows,under),):
        for a,b,c,d in zip(high,high[1:],low,low[1:]):
            for i in range(len(a)):
                j=(i+1)%len(a)
                m.face('roof',[a[i],a[j],b[j],b[i]])
                m.face('steel',[c[j],c[i],d[i],d[j]])
        for a,b in ((high[0],low[0]),(high[-1],low[-1])):
            for i in range(len(a)):
                j=(i+1)%len(a)
                m.face('steel',[a[i],b[i],b[j],a[j]])
    # Corner ridges are source-visible forms, not an engineering tile schedule.
    for i in range(8):
        for a,b in zip(rows,rows[1:]):
            m.tube('steel',a[i*4],b[i*4],.11,n=4)


def _storey(m,row,rotation,spec,next_row=None):
    floor,body_r,column_r,eave,roof_top,roof_r=row
    top=eave-.6
    core=_octagon(body_r,floor,rotation)
    _shell(m,'concrete',[core,_octagon(body_r,top,rotation)])
    columns=_octagon(column_r,floor,rotation)
    _shell(m,'steel',[_octagon(column_r+.35,floor-.22,rotation),_octagon(column_r+.35,floor+.12,rotation)])
    _rails(m,column_r+.25,floor+.12,rotation)
    for i,a in enumerate(columns):
        b=columns[(i+1)%8]
        for t in (0,1/3,2/3):
            x,y,_=_at(a,b,t)
            m.tube('steel',(x,y,floor+.15),(x,y,top),.20,n=6)
            # A short cross head suggests the reviewed bracket rhythm.
            dx,dy=b[0]-a[0],b[1]-a[1]
            length=math.hypot(dx,dy)
            m.tube('gold',(x-dx/length*.4,y-dy/length*.4,top-.15),
                   (x+dx/length*.4,y+dy/length*.4,top-.15),.15,n=4)
        # Three bounded dark panels per face, recessed visually behind gallery.
        ca,cb=core[i],core[(i+1)%8]
        nx,ny=(ca[0]+cb[0])/2,(ca[1]+cb[1])/2
        nl=math.hypot(nx,ny);nx,ny=nx/nl*.025,ny/nl*.025
        for j in range(3):
            p,q=_at(ca,cb,(j+.12)/3),_at(ca,cb,(j+.88)/3)
            z0,z1=floor+1.15,top-.5
            m.face('darkglass',[(p[0]+nx,p[1]+ny,z0),(q[0]+nx,q[1]+ny,z0),
                               (q[0]+nx,q[1]+ny,z1),(p[0]+nx,p[1]+ny,z1)])
            m.tube('steel',(p[0]+nx,p[1]+ny,z0),(p[0]+nx,p[1]+ny,z1),.065,n=4)
    if next_row is not None:
        # Keep the central envelope continuous behind the sloping roof, rather
        # than suspending the next gallery above a gap in the estimated body.
        _shell(m,'concrete',[_octagon(body_r,top,rotation),
                             _octagon(next_row[1],next_row[0],rotation)])
    inner=1.9 if next_row is None else body_r+.4
    # For all non-crown storeys, roof closes against the continuing central body.
    _roof(m,roof_r,inner,eave,roof_top,rotation,_value(spec,'eaveCornerLiftM'))


def _finial(m,spec,rotation):
    bottom=_value(spec,'finialBaseM');tip=spec['heightM']
    _shell(m,'gold',[_octagon(1.9,bottom,rotation),_octagon(1.3,bottom+1.9,rotation),
                     _octagon(.8,bottom+2.35,rotation)])
    m.tube('gold',(0,0,bottom+2),(0,0,tip),.20,n=8,r2=.025)
    for i in range(9):
        z=bottom+2.5+i*.83
        r=1.22-i*.058
        _shell(m,'gold',[_octagon(r*.88,z-.16,rotation),_octagon(r,z,rotation),_octagon(r*.85,z+.17,rotation)])
    # Open circular ornament is visible in the designer's south-front photo.
    z=bottom+11.25;r=.9
    points=[(r*math.cos(i*math.tau/20),0,z+r*math.sin(i*math.tau/20)) for i in range(20)]
    for a,b in zip(points,points[1:]+points[:1]):
        m.tube('gold',a,b,.08,n=4)
    for height,radius in ((bottom+12.9,.24),(bottom+14.2,.17)):
        _shell(m,'gold',[_octagon(radius*.55,height-.22,rotation),_octagon(radius,height,rotation),
                         _octagon(radius*.55,height+.22,rotation)])
    # Eight slender stays; positions are an estimate, attachment details pending.
    corners=_octagon(spec['levels'][-1][5]-.15,spec['levels'][-1][3]+.65,rotation)
    for p in corners:
        m.tube('steel',(0,0,bottom+3.8),p,.035,n=4)


def _base(m,ring,spec,rotation):
    height=spec['base']['heritageCoverHeightM']
    # The source octagon is kept exactly at the base, with estimated taper.
    taper=_value(spec,'coverTopPlanFactor')
    _shell(m,'concrete',[[(x,y,0) for x,y in ring],[(x*taper,y*taper,height) for x,y in ring]])
    _shell(m,'concrete',[[(x,y,height-.25) for x,y in ring],[(x,y,height+.05) for x,y in ring]])
    # Source photos show a white terrace rail. Its spacing is representative.
    for i,(x,y) in enumerate(ring):
        xx,yy=ring[(i+1)%len(ring)]
        a,b=(x,y,height+.05),(xx,yy,height+.05)
        for lift in (.4,1.08):
            m.tube('concrete',(x,y,height+lift),(xx,yy,height+lift),.10,n=4)
        for j in range(6):
            u,v,_=_at(a,b,j/6)
            m.tube('concrete',(u,v,height+.05),(u,v,height+1.22),.10,n=4)
    # South central dark inset is a visual marker only, not a traversable door.
    south=min(zip(ring,ring[1:]+ring[:1]),key=lambda edge:(edge[0][1]+edge[1][1])/2)
    a,b=south
    p,q=_at((*a,0),(*b,0),.35),_at((*a,0),(*b,0),.65)
    m.face('darkglass',[(p[0],p[1]-.025,.8),(q[0],q[1]-.025,.8),
                       (q[0],q[1]-.025,3.3),(p[0],p[1]-.025,3.3)])


def build(b,lm,spec,scale=.6):
    """Append geometry to shared B. lm coordinates/base are already game units."""
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('scale must be finite and positive')
    if not all(math.isfinite(lm[k]) for k in ('x','z')):
        raise ValueError('lm.x/lm.z must be finite game coordinates')
    ring,offset,geo=_context(lm,spec)
    rotation=math.radians(_value(spec,'octagonVertexAngleDegrees'))
    previous=b.frame
    b.frame=(lm['x'],lm['z'],0)
    m=_Mesh(b,scale,offset,lm.get('y',0))
    try:
        _base(m,ring,spec,rotation)
        for i,row in enumerate(spec['levels']):
            next_row=spec['levels'][i+1] if i+1<len(spec['levels']) else None
            _storey(m,row,rotation,spec,next_row)
            if i:
                # Four waist roofs below the upper galleries, distinct from
                # the five large storey roofs; no invented extra storeys.
                _roof(m,row[2]+.7,row[1]+.3,row[0]-.85,row[0]-.25,
                      rotation,_value(spec,'waistCornerLiftM'),thickness=.14)
        _finial(m,spec,rotation)
    finally:
        b.frame=previous
    if m.triangles > spec['budget']['maxTriangles'] or len(m.materials) > spec['budget']['maxMaterials']:
        raise ValueError(f'Leifeng candidate exceeds budget: {m.triangles} triangles, {len(m.materials)} materials')
    return {'id':'leifeng-pagoda','scope':spec['scope'],'storeyCount':5,'majorRoofCount':5,'waistRoofCount':4,
            'maxHeight':spec['heightM']*scale,'generatedFaces':m.faces,
            'triangleCountBeforeExport':m.triangles,'materials':sorted(m.materials),'newLights':0,
            'geographyCityId':'hangzhou','projectionOriginWGS84':geo['originWGS84'],
            'sourceSpec':'docs/hangzhou/research/core/leifeng-round2/spec.json',
            'collisionStatus':'pending; source outer base envelope is not a traversable entrance model'}


def ground_footprints(lm,spec,scale=.6):
    """Conservative outer base envelope; terraces and entrance collision pending."""
    ring,offset,_=_context(lm,spec)
    return [[[lm['x']+(x+offset[0])*scale,lm['z']+(y+offset[1])*scale] for x,y in ring]]
