"""Source-bound West Lake context candidates, never a shared-city writer.

Prepare uses fixed 261011 footprints and the demo-v8 physical surface. Geometry
uses real metres locally and applies 0.60 once. build() accepts the existing B
face API with an identity frame, emitting absolute Blender east/north/up game
coordinates. No bpy/city_mesh import or scene mutation occurs on import.

Only seven photograph-supported footprints receive candidate meshes. The other
65 source objects remain explicit unknown/pending records, without invented
heights and without exclusion requests. All model statuses remain candidates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/cities/hangzhou/west-lake-context-v1'
AUDIT = ROOT / 'docs/hangzhou/audit/west-lake-context-review-20261111/inventory.json'
RUNTIME = ROOT / 'artifacts/cities/hangzhou/demo-v8/public/cities/hangzhou'
SCALE = .60
PALETTE = {
    'wl-plaster': (.72, .70, .61), 'wl-white': (.80, .79, .72),
    'wl-brick': (.29, .31, .30), 'wl-stone': (.37, .39, .36),
    'wl-wood': (.23, .095, .055), 'wl-dark': (.075, .068, .051),
    'wl-tile': (.20, .22, .21), 'wl-tile-light': (.25, .27, .25),
    'wl-ochre': (.59, .36, .09), 'wl-ochre-light': (.69, .44, .13),
    'wl-green': (.13, .24, .18), 'wl-glass': (.12, .18, .19),
}
TARGETS = {
    'way/1466923702': dict(group='mingjian', role='villa', name='明鉴楼／逸云寄庐',
        angle=44.73486717217106, floorCount=3, floorBasis='reported', heightRange=[11.5, 15.5],
        sources=['mingjian-management', 'mingjian-release', 'mingjian-photographer'],
        binding='direct source-way name and institutional identity', model='mingjian'),
    'way/830131767': dict(group='baisu', role='middle-hall', name='白苏二公祠中厅（位置推断）',
        angle=46.058879752511906, floorCount=None, floorBasis='unknown', heightRange=[4.5, 6.8],
        sources=['baisu-management', 'baisu-designer'],
        binding='POI-inside plus aerial-layout match; not a surveyed building-number plan', model='hall'),
    'way/830131769': dict(group='baisu', role='rear-hall', name='白苏二公祠后厅（位置推断）',
        angle=46.058879752511906, floorCount=None, floorBasis='unknown', heightRange=[6.5, 9.5],
        sources=['baisu-management', 'baisu-designer'],
        binding='rear footprint along the same axis as POI hall; aerial-layout inference', model='rear-hall'),
    'way/830131766': dict(group='baisu', role='west-front-wing', name='白苏二公祠前院西侧厢房（位置推断）',
        angle=46.058879752511906, floorCount=None, floorBasis='unknown', heightRange=[3.5, 5.5],
        sources=['baisu-management', 'baisu-designer'],
        binding='paired front footprint consistent with overhead photo; exact boundary pending', model='wing'),
    'way/830131768': dict(group='baisu', role='east-front-wing', name='白苏二公祠前院东侧厢房（位置推断）',
        angle=46.058879752511906, floorCount=None, floorBasis='unknown', heightRange=[3.5, 5.5],
        sources=['baisu-management', 'baisu-designer'],
        binding='paired front footprint consistent with overhead photo; exact boundary pending', model='wing'),
    'way/706867392': dict(group='chiang', role='probable-main', name='蒋经国旧居南主楼（匹配推断）',
        angle=60.14328866343344, floorCount=2, floorBasis='reported-and-source-tags', heightRange=[7.5, 11],
        sources=['chiang-protection', 'chiang-historical-report'],
        binding='unnamed southern two-storey hipped footprint; inferred main-building binding', model='villa'),
    'way/706867393': dict(group='chiang', role='probable-annex', name='蒋经国旧居北副楼（匹配推断）',
        angle=60.14328866343344, floorCount=2, floorBasis='reported-and-source-tags', heightRange=[7, 10.5],
        sources=['chiang-protection', 'chiang-historical-report'],
        binding='named northern irregular footprint; inferred annex, not the entire historic site', model='annex'),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def prepare(out=OUT):
    """CPU-only fixed-source task preparation; imports no Blender module."""
    from shapely.geometry import LineString, MultiPoint, Point, shape
    from shapely.ops import transform, triangulate
    sys.path.insert(0, str(ROOT / 'scripts'))
    from hangzhou_surface import Surface
    inv = json.loads(AUDIT.read_text())
    assert len(inv['candidateBuildings']) == 55 and len(inv['omittedSourceBuildings']) == 17
    scope = inv['scope']
    assert scope['scale'] == SCALE and scope['gameOriginWGS84'] == [120.155, 30.274]
    # Fixed projection from this runtime; never substitute the Shenzhen AGENTS origin.
    city = json.loads((RUNTIME / 'city.json').read_text())
    projection = {key:city['meta'][key] for key in ('projection','eastMetresPerDegree','northMetresPerDegree')}
    east, north = projection['eastMetresPerDegree'], projection['northMetresPerDegree']
    surface = Surface(RUNTIME)
    rows = []
    for source in inv['candidateBuildings'] + inv['omittedSourceBuildings']:
        osm_id = source['id']
        geometry = source['sourceGeometryWGS84']
        planar = transform(lambda lon, lat: ((lon-120.155)*east, (lat-30.274)*north), shape(geometry))
        cx, cy = planar.centroid.coords[0]
        target = TARGETS.get(osm_id)
        row = {
            'id': osm_id, 'sourceTags': source['sourceTags'], 'sourceGeometryWGS84': geometry,
            'sourceFootprintSha256': hashlib.sha256(json.dumps(geometry, sort_keys=True).encode()).hexdigest(),
            'sourceAreaRealM2': planar.area, 'centerGame': [cx*SCALE, cy*SCALE],
            'wasPresentInDemoV8': 'candidateHeightGame' in source,
            'omissionReason': source.get('reproducedOmissionReason'),
            'priorHeightRealM': source.get('candidateHeightRealEquivalentM'),
            'priorHeightBasis': source.get('candidateHeightSource'),
            'trueHeightM': None, 'trueHeightStatus': 'unknown',
            'sourceHeightTags': {k: v for k, v in source['sourceTags'].items() if 'height' in k or 'levels' in k or 'roof' in k},
            'retention': 'preserve-source-identity; never blanket-delete',
            'renderCandidate': bool(target), 'runtimeApproved': False,
            'candidateHeightM': None, 'candidateRoofType': None,
            'unknowns': ['surveyed height', 'current facade condition', 'precise entrance and gate state'],
        }
        if not target:
            row.update(stage='pending-evidence', identity=source.get('sourceName') or source['sourceTags'].get('name') or 'unknown',
                       use=source.get('sourceUsage') or 'unknown', roofStatus='unknown',
                       action='retain record; request per-building evidence; do not generate random or alleged final low block')
            rows.append(row)
            continue
        row.update(target)
        angle = math.radians(target['angle'])
        u, v = (math.cos(angle), math.sin(angle)), (-math.sin(angle), math.cos(angle))
        local = transform(lambda x, y: ((x-cx)*u[0]+(y-cy)*u[1], (x-cx)*v[0]+(y-cy)*v[1]), planar)
        if len(local.geoms) != 1 or len(local.geoms[0].interiors):
            raise ValueError(f'Unsupported target topology: {osm_id}; never silently discard rings')
        poly = local.geoms[0]
        def rings(p):
            if p.geom_type == 'MultiPolygon':
                if len(p.geoms) != 1:
                    raise ValueError(f'Inset split footprint {osm_id}')
                p = p.geoms[0]
            return [list(c) for c in list(p.exterior.coords)[:-1]]
        def tris(p):
            return [[[x,y] for x,y in list(t.exterior.coords)[:3]] for t in triangulate(p) if p.covers(t.representative_point()) and p.intersection(t).area >= t.area-1e-8]
        ring = rings(poly)
        world_ring = [[(cx+x*u[0]+y*v[0])*SCALE, (cy+x*u[1]+y*v[1])*SCALE] for x,y in ring]
        grounds = [surface.ground(x,y) for x,y in world_ring]
        prior = source.get('baseFloorRecords') or []
        base = prior[0]['baseYGame'] if prior else max(grounds) + .12
        row.update(localRingRealM=ring, localTrianglesRealM=tris(poly), localBoundsRealM=list(poly.bounds),
                   sourceFootprintGame=[world_ring+[world_ring[0]]], axisU=list(u), axisV=list(v), baseYGame=base,
                   baseBasis='existing demo-v8 base floor' if prior else 'max fixed demo-v8 game-surface corner + 0.12 game; not measured foundation',
                   sampledGroundRangeGame=[min(grounds),max(grounds)],
                   sourceGroundDatum='game surface only; not surveyed building elevation',
                   stage='reference-informed-shape-candidate',
                   heightBasis='estimated from reported storeys and photographed proportions; no measured height',
                   footprintBasis='fixed OSM source polygon; not road-carved and not survey-grade',
                   orientationBasis='fixed source wall axes; facade-facing allocation remains estimated')
        inset = poly.buffer(-.8, join_style=2)
        if inset.is_empty:
            raise ValueError(f'Invalid occupied inset {osm_id}')
        row['insetRingRealM'], row['insetTrianglesRealM'] = rings(inset), tris(inset)
        xmin,ymin,xmax,ymax = poly.bounds
        samples=[]
        for i in range(8):
            x=xmin+.65+(xmax-xmin-1.3)*i/7
            intersection=poly.intersection(LineString([(x,ymin-1),(x,ymax+1)]))
            samples.append([x,intersection.bounds[1]+.35])
        row['frontColumnSamplesRealM']=samples
        # Mesh a hip roof on the real irregular annex footprint, preserving its open plan.
        roofpoly=poly.buffer(.45,join_style=2)
        points=list(roofpoly.exterior.coords)[:-1]
        for i in range(math.floor(xmin),math.ceil(xmax)+1,2):
            for j in range(math.floor(ymin),math.ceil(ymax)+1,2):
                if roofpoly.contains(Point(i,j)): points.append((i,j))
        rooftris=[t for t in triangulate(MultiPoint(points)) if roofpoly.covers(t.representative_point()) and roofpoly.intersection(t).area>=t.area-1e-8]
        depths=[Point(p).distance(roofpoly.boundary) for p in points]
        depth=max(depths) or 1
        row['irregularHipTriangles']=[[[x,y,min(1,Point(x,y).distance(roofpoly.boundary)/depth)] for x,y in list(t.exterior.coords)[:3]] for t in rooftris]
        rows.append(row)
    modelled = [r['id'] for r in rows if r['renderCandidate']]
    assert set(modelled) == set(TARGETS)
    spec={'id':'hangzhou-west-lake-context','version':1,'cityId':'hangzhou','scale':SCALE,
          'coordinateContract':'absolute Blender east/north/up in game units; exporter Y-up; no extra root rotation',
          'originWGS84':[120.155,30.274],'projection':projection,'inventoryPath':str(AUDIT.relative_to(ROOT)),
          'inventorySha256':digest(AUDIT),'evidenceSha256':digest(out/'evidence.json'),
          'surfaceManifestSha256':digest(RUNTIME/'geography/manifest.json'),'counts':{'source':72,'present':55,'omitted':17,'meshCandidates':7,'pendingEvidence':65},
          'materials':PALETTE,'objects':rows,
          'integration':{'proposedBaseBuildingIds':[r['id'] for r in rows if r['renderCandidate'] and r['wasPresentInDemoV8']],
                         'proposedRestoredSourceIds':[r['id'] for r in rows if r['renderCandidate'] and not r['wasPresentInDemoV8']],
                         'applyAutomatically':False,'physicalRoadDeletion':False,
                         'requiredSynchronizedChannels':['base-building','facade-tile','roof-props-and-roof-collision','signs','building-collision','foundation/AO'],
                         'unknownObjectExclusions':[]}}
    write(out/'context-spec.json',spec)
    write(out/'source-inventory.json',inv)
    for group in ('mingjian','baisu','chiang'):
        group_rows=[r for r in rows if r.get('group')==group]
        job={'id':group,'stage':'reference-informed-shape-candidate','sourceIds':[r['id'] for r in group_rows],
             'sourceModule':'scripts/landmarks/hangzhou_west_lake_context.py','fileOwnership':[str(out.relative_to(ROOT)),'scripts/landmarks/hangzhou_west_lake_context.py'],
             'sourceSnapshots':{'context-spec.json':digest(out/'context-spec.json'),'evidence.json':digest(out/'evidence.json')},
             'realHeightKnown':False,'estimatedHeightRangesM':{r['id']:r['heightRange'] for r in group_rows},
             'pendingSubscopes':['surveyed heights','exact roof joints and facade ornaments','gate/sign placement','current runtime appearance and performance']}
        write(out/'jobs'/group/'job.json',job)
        write(out/'jobs'/group/'validation.json',{'stage':'unverified','checks':{k:{'status':'pending','evidencePaths':[]} for k in ('scale','orientation','silhouette','context','collision','browser','performance','provenance')}})
    return spec


class Mesh:
    """B-compatible pure mesh sink; caller owns Blender scene and export."""
    def __init__(self):
        self.faces=[]
        self.object_id=''
        self.part=''

    def face(self, material, points, uv=None):
        self.faces.append({'objectId':self.object_id,'part':self.part,'material':material,'points':[list(p) for p in points]})


class Local:
    def __init__(self,b,row,scale=SCALE):
        self.b,self.r,self.scale=b,row,scale
        self.u,self.v=row['axisU'],row['axisV']

    def face(self,mat,pts):
        c=self.r['centerGame'];base=self.r['baseYGame'];s=self.scale
        self.b.face(mat,[(c[0]+(x*self.u[0]+y*self.v[0])*s,c[1]+(x*self.u[1]+y*self.v[1])*s,base+z*s) for x,y,z in pts])

    def box(self,mat,c,size):
        x,y,z=c;a,b,h=[v/2 for v in size]
        q=[(x-a,y-b,z-h),(x+a,y-b,z-h),(x+a,y+b,z-h),(x-a,y+b,z-h),(x-a,y-b,z+h),(x+a,y-b,z+h),(x+a,y+b,z+h),(x-a,y+b,z+h)]
        for ids in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.face(mat,[q[i] for i in ids])

    def tube(self,mat,a,b,r,n=8):
        d=[b[i]-a[i] for i in range(3)];ln=math.sqrt(sum(x*x for x in d));d=[x/ln for x in d]
        q=[0,0,1] if abs(d[2])<.9 else [1,0,0]
        def cross(u,v):return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        u=cross(d,q);l=math.sqrt(sum(x*x for x in u));u=[x/l for x in u];v=cross(d,u)
        rings=[[[p[k]+r*(u[k]*math.cos(i*math.tau/n)+v[k]*math.sin(i*math.tau/n)) for k in range(3)] for i in range(n)] for p in (a,b)]
        for i in range(n):self.face(mat,[rings[0][i],rings[0][(i+1)%n],rings[1][(i+1)%n],rings[1][i]])
        self.face(mat,list(reversed(rings[0])));self.face(mat,rings[1])

    def extrusion(self,ring,triangles,z0,z1,mat):
        signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))
        ring=ring if signed>0 else list(reversed(ring))
        for a,b in zip(ring,ring[1:]+ring[:1]):self.face(mat,[(a[0],a[1],z0),(b[0],b[1],z0),(b[0],b[1],z1),(a[0],a[1],z1)])
        for t in triangles:self.face(mat,[(x,y,z1) for x,y in t])


def roof(m,bounds,eave,rise,*,ochre=False,hip=False,upturn=.20,ridge=True):
    """Segmented curved pitched roof; all dimensions are reviewable estimates."""
    xmin,ymin,xmax,ymax=bounds;cx,cy=(xmin+xmax)/2,(ymin+ymax)/2;w,d=(xmax-xmin)/2,(ymax-ymin)/2
    mats=('wl-ochre','wl-ochre-light') if ochre else ('wl-tile','wl-tile-light')
    def point(x,y):
        depth=min(w-abs(x-cx),d-abs(y-cy)) if hip else d-abs(y-cy)
        q=max(0,min(1,depth/d));z=eave+rise*q**1.45+upturn*(abs(x-cx)/w)**8*(abs(y-cy)/d)**5
        return x,y,z
    nx=max(8,min(28,round((xmax-xmin)/.65)));ny=12
    for i in range(nx):
        a,b=xmin+(xmax-xmin)*i/nx,xmin+(xmax-xmin)*(i+1)/nx
        for j in range(ny):
            c,d0=ymin+(ymax-ymin)*j/ny,ymin+(ymax-ymin)*(j+1)/ny
            m.face(mats[i%2],[point(a,c),point(b,c),point(b,d0),point(a,d0)])
    for ya in (ymin,ymax):
        for i in range(nx):
            a,b=xmin+(xmax-xmin)*i/nx,xmin+(xmax-xmin)*(i+1)/nx
            m.tube(mats[0],point(a,ya),point(b,ya),.065,6)
    if not hip:
        for x in (xmin,xmax):
            for y0,y1 in ((ymin,cy),(cy,ymax)):
                m.face('wl-white',[(x,y0,eave-.10),(x,y1,eave-.10),point(x,y1),point(x,y0)])
    if ridge:
        a=xmin+d*.75 if hip else xmin+.2;b=xmax-d*.75 if hip else xmax-.2
        if a>b:a,b=cx-.2,cx+.2
        m.tube(mats[0],(a,cy,eave+rise+.08),(b,cy,eave+rise+.08),.12,8)


def lattice(m,x,y,z,w,h,*,side=False,white=False):
    mat='wl-white' if white else 'wl-wood'
    def p(a,b):return (x,y+a,z+b) if side else (x+a,y,z+b)
    corners=[p(-w/2,-h/2),p(w/2,-h/2),p(w/2,h/2),p(-w/2,h/2)]
    m.face('wl-glass',corners)
    for a,b in zip(corners,corners[1:]+corners[:1]):m.tube(mat,a,b,.055,4)
    for i in range(1,4):m.tube(mat,p(-w/2+w*i/4,-h/2),p(-w/2+w*i/4,h/2),.025,4)
    for j in range(1,4):m.tube(mat,p(-w/2,-h/2+h*j/4),p(w/2,-h/2+h*j/4),.025,4)


def wall_windows(m,ring,heights,*,white=False,width=1.25,height=1.9):
    """Bind each window to its real wall edge; never a bounding-box phantom facade."""
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))
    ring=ring if area>0 else list(reversed(ring))
    mat='wl-white' if white else 'wl-wood'
    for a,b in zip(ring,ring[1:]+ring[:1]):
        length=math.dist(a,b)
        if length<2.1:continue
        count=max(1,round(length/3.2));u=((b[0]-a[0])/length,(b[1]-a[1])/length);n=(u[1],-u[0])
        w=min(width,length/(count+1)*.78)
        for i in range(count):
            c=(a[0]+(b[0]-a[0])*(i+.5)/count+n[0]*.035,a[1]+(b[1]-a[1])*(i+.5)/count+n[1]*.035)
            for z in heights:
                def p(s,t):return c[0]+u[0]*s,c[1]+u[1]*s,z+t
                pts=[p(-w/2,-height/2),p(w/2,-height/2),p(w/2,height/2),p(-w/2,height/2)]
                m.face('wl-glass',pts)
                for q,r0 in zip(pts,pts[1:]+pts[:1]):m.tube(mat,q,r0,.05,4)
                for j in range(1,3):
                    m.tube(mat,p(-w/2+w*j/3,-height/2),p(-w/2+w*j/3,height/2),.025,4)
                    m.tube(mat,p(-w/2,-height/2+height*j/3),p(w/2,-height/2+height*j/3),.025,4)


def railing(m,a,b,z,*,green=False):
    mat='wl-green' if green else 'wl-white';span=math.dist(a,b);n=max(2,math.ceil(span/.72))
    m.tube(mat,(*a,z+.85),(*b,z+.85),.075,6)
    m.tube(mat,(*a,z+.18),(*b,z+.18),.055,6)
    for i in range(n+1):
        p=(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n)
        m.tube(mat,(*p,z+.16),(*p,z+.83),.055,6)


def foundation(m,r,top=.25):
    # A game-surface skirt prevents floating corners; it is not a surveyed plinth.
    low=(r['sampledGroundRangeGame'][0]-r['baseYGame'])/SCALE-.03
    m.extrusion(r['localRingRealM'],r['localTrianglesRealM'],min(0,low),top,'wl-stone')


def mingjian(m,r):
    ring,tris=r['localRingRealM'],r['localTrianglesRealM'];xmin,ymin,xmax,ymax=r['localBoundsRealM']
    foundation(m,r,.35)
    m.extrusion(r['insetRingRealM'],r['insetTrianglesRealM'],.35,7.35,'wl-plaster')
    # Eight paired/classical columns at the source-facing outline, not a solid arcade box.
    for x,y in r['frontColumnSamplesRealM']:
        m.box('wl-white',(x,y,.55),(.60,.60,.4));m.tube('wl-white',(x,y,.75),(x,y,3.48),.18,10)
        m.box('wl-white',(x,y,3.48),(.58,.54,.22))
        # Capital volutes are simplified geometric candidates, not exact Ionic carvings.
        for dx in (-.23,.23):m.tube('wl-white',(x+dx,y-.1,3.45),(x+dx,y+.1,3.45),.11,8)
        m.tube('wl-white',(x,y,4.25),(x,y,7.22),.13,8)
    for i in range(7):
        a,b=r['frontColumnSamplesRealM'][i:i+2];railing(m,a,b,.45);railing(m,a,b,4.1,green=True)
    # Roof registers, upper setback pavilion and roof terraces are reference informed.
    roof(m,(xmin-.45,ymin-.40,xmax+.45,ymax+.4),3.85,.65,ochre=True,hip=True,upturn=.55)
    roof(m,(xmin-.65,ymin-.55,xmax+.65,ymax+.55),7.55,1.55,ochre=True,hip=True,upturn=.75)
    m.box('wl-plaster',(0,.6,9.22),(8.3,6.1,3.74))
    roof(m,(-4.95,-3.1,4.95,4.3),11.10,1.60,ochre=True,hip=True,upturn=.50)
    wall_windows(m,r['insetRingRealM'],(1.9,5.5),width=1.3,height=2)
    for x in (-2.5,0,2.5):lattice(m,x,-2.47,9.0,1.3,1.7)
    # Exact upper terrace-to-roof joints are not solved by the available obliques.
    # Keep those unmodelled instead of floating a decorative balustrade over tiles.


def hall(m,r):
    xmin,ymin,xmax,ymax=r['localBoundsRealM'];w=xmax-xmin;rear=r['model']=='rear-hall';wing=r['model']=='wing'
    wall=3.15 if wing else 3.65
    foundation(m,r)
    m.extrusion(r['localRingRealM'],r['localTrianglesRealM'],.25,wall,'wl-white')
    wall_windows(m,r['localRingRealM'],(1.9,),width=1.8,height=2.25)
    # Dark wood door has no invented lettering or light.
    if wing:
        side=xmax+.055 if r['role']=='west-front-wing' else xmin-.055
        m.box('wl-dark',(side,(ymin+ymax)/2,1.5),(.08,1.55,2.6))
    else:
        m.box('wl-dark',((xmin+xmax)/2,ymin-.055,1.5),(1.55,.08,2.6))
    if rear:
        m.box('wl-white',((xmin+xmax)/2,(ymin+ymax)/2,4.85),(w-.15,ymax-ymin-2.05,2.4))
        roof(m,(xmin-.55,ymin-.7,xmax+.55,ymin+1.9),3.7,.9,upturn=.18)
        roof(m,(xmin-.45,ymin+.25,xmax+.45,ymax-.25),6.05,1.35,upturn=.22)
        for i in range(9):lattice(m,xmin+(i+.5)*w/9,ymin+.99,5.05,w/9-.08,1.0)
        ridge_z=7.4
    elif wing:
        class Swap:
            def face(self,mat,pts):m.face(mat,[(y,x,z) for x,y,z in reversed(pts)])
            def tube(self,mat,a,b,r,n):m.tube(mat,(a[1],a[0],a[2]),(b[1],b[0],b[2]),r,n)
        roof(Swap(),(ymin-.5,xmin-.5,ymax+.5,xmax+.5),wall+.12,1.0,upturn=.15)
        ridge_z=wall+1.12
    else:
        roof(m,(xmin-.5,ymin-.5,xmax+.5,ymax+.5),wall+.12,1.0 if wing else 1.35,upturn=.15)
        ridge_z=wall+.12+(1.0 if wing else 1.35)
    # Raised perforated ridge rail is directly visible in management/designer photos.
    if not wing:
        cy=(ymin+ymax)/2
        railing(m,(xmin+.15,cy),(xmax-.15,cy),ridge_z-.05)
    m.box('wl-wood',((xmin+xmax)/2,ymin-.09,wall-.30),(w+.08,.15,.20))


def villa(m,r):
    xmin,ymin,xmax,ymax=r['localBoundsRealM'];body=6.60
    foundation(m,r)
    m.extrusion(r['insetRingRealM'],r['insetTrianglesRealM'],.25,body,'wl-brick')
    # Irregular annex roof uses the full source outline; no bounding rectangle fills its notches.
    if r['model']=='annex':
        for tri in r['irregularHipTriangles']:m.face('wl-tile',[(x,y,body+1.45*q) for x,y,q in tri])
    else:roof(m,(xmin-.40,ymin-.40,xmax+.40,ymax+.40),body+.15,1.65,hip=True,upturn=.08)
    wall_windows(m,r['insetRingRealM'],(1.8,4.9),white=True,width=1.35,height=1.75)
    # A low open veranda and white parapet express photographed circulation, not a generic tower.
    if r['model']!='annex':
        a,b=(xmin+.5,ymin+.35),(xmax-.5,ymin+.35)
        for i in range(5):
            x=a[0]+(b[0]-a[0])*i/4
            m.box('wl-white',(x,a[1],4.85),(.14,.14,2.9))
        railing(m,a,b,3.4)
        m.box('wl-white',((xmin+xmax)/2,ymin+.8,6.48),(xmax-xmin,.90,.18))
    # Light horizontal trim; no current brand/tenant assertion.
    for z in (3.35,6.48):
        ring=r['insetRingRealM']
        for a,b in zip(ring,ring[1:]+ring[:1]):m.tube('wl-white',(*a,z),(*b,z),.065,4)


def build(b,spec,selected_ids=None):
    if spec['cityId']!='hangzhou' or spec['scale']!=SCALE:
        raise ValueError('Only fixed Hangzhou 0.60 context is supported')
    if getattr(b,'frame',(0,0,0))!=(0,0,0):
        raise ValueError('Use identity B.frame; source coordinates are already absolute game units')
    for row in spec['objects']:
        if not row['renderCandidate'] or selected_ids and row['id'] not in selected_ids:continue
        if isinstance(b,Mesh):b.object_id=row['id'];b.part=row['model']
        m=Local(b,row)
        {'mingjian':mingjian,'hall':hall,'rear-hall':hall,'wing':hall,'villa':villa,'annex':villa}[row['model']](m,row)


def cpu_validate(spec,out=OUT):
    mesh=Mesh();build(mesh,spec)
    objects=[]
    for row in spec['objects']:
        if not row['renderCandidate']:continue
        faces=[f for f in mesh.faces if f['objectId']==row['id']];pts=[p for f in faces for p in f['points']]
        if not all(math.isfinite(n) for p in pts for n in p):raise ValueError('Non-finite geometry')
        bounds=[[min(p[k] for p in pts),max(p[k] for p in pts)] for k in range(3)]
        top=(bounds[2][1]-row['baseYGame'])/SCALE
        if not row['heightRange'][0]<=top<=row['heightRange'][1]:
            raise ValueError(f'{row["id"]} actual {top} outside declared candidate range')
        objects.append({'id':row['id'],'triangles':sum(len(f['points'])-2 for f in faces),'faces':len(faces),
                        'boundsBlenderGame':bounds,'candidateMaximumRelativeHeightM':top,'heightEstimated':True,
                        'sourceOutlineRetained':True,'visualAccepted':False})
    tri=sum(x['triangles'] for x in objects)
    if tri>75000:raise ValueError('Exceeded independent-candidate triangle budget')
    result={'stage':'cpu-geometry-checked; not exported or visually accepted','sourceModuleSha256':digest(__file__),
            'specSha256':digest(out/'context-spec.json'),'evidenceSha256':digest(out/'evidence.json'),
            'objects':objects,'triangles':tri,'materials':len(PALETTE),'faces':len(mesh.faces),
            'checks':{'sourceRecords':len(spec['objects'])==72,'omittedRetained':sum(not r['wasPresentInDemoV8'] for r in spec['objects'])==17,
                      'noUnknownMeshes':len(objects)==7,'unknownHeightsRemainNull':all(r['trueHeightM'] is None for r in spec['objects']),
                      'finiteGeometry':True,'singleScale':True,'sharedAssetsWritten':False},
            'pending':['photo-to-candidate shape review','Blender GLB export','actual GLB verification','collision integration','browser/performance']}
    write(out/'mesh-candidate.json',{'coordinateContract':spec['coordinateContract'],'materials':PALETTE,'faces':mesh.faces})
    write(out/'cpu-validation.json',result)
    return mesh,result


def export_blender(spec,out=OUT):
    """Run only after parent grants the serial background-Blender window."""
    import bpy
    mesh,result=cpu_validate(spec,out)
    materials={}
    for name,rgb in PALETTE.items():
        m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1);m.use_nodes=True
        bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(*rgb,1);bsdf.inputs['Roughness'].default_value=.74
        materials[name]=m
    obs=[]
    for row in spec['objects']:
        if not row['renderCandidate']:continue
        for mat in PALETTE:
            fs=[f for f in mesh.faces if f['objectId']==row['id'] and f['material']==mat]
            if not fs:continue
            vertices=[];polys=[]
            for f in fs:
                n=len(vertices);vertices.extend(f['points']);polys.append(tuple(range(n,n+len(f['points']))))
            name='detail_west_lake_context_'+row['id'].replace('/','_')+'_'+mat
            data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],polys);data.update()
            ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);data.materials.append(materials[mat]);obs.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
    path=out/'west-lake-context.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,
                              export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    write(out/'model.json',{'stage':'modelled-candidate; visual/collision/runtime pending','artifactPath':str(path.relative_to(ROOT)),
                          'sha256':digest(path),'bytes':path.stat().st_size,'triangles':result['triangles'],
                          'sourceModuleSha256':digest(__file__),'specSha256':digest(out/'context-spec.json'),
                          'evidenceSha256':digest(out/'evidence.json'),'coordinateContract':spec['coordinateContract'],
                          'photoTexturesBundled':False,'buildCommand':' '.join(sys.argv),'meshes':len(obs)})


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true');parser.add_argument('--cpu-validate',action='store_true')
    parser.add_argument('--export-blender',action='store_true');parser.add_argument('--output',type=Path,default=OUT)
    a=parser.parse_args(args);out=a.output.resolve()
    if out!=OUT.resolve():raise ValueError('This task may only write its independent west-lake-context-v1 directory')
    if a.prepare:spec=prepare(out)
    else:spec=json.loads((out/'context-spec.json').read_text())
    if a.cpu_validate:
        _,report=cpu_validate(spec,out);print(json.dumps({k:v for k,v in report.items() if k not in ('objects','pending')},ensure_ascii=False))
    if a.export_blender:export_blender(spec,out)
    if not (a.prepare or a.cpu_validate or a.export_blender):parser.error('Choose an explicit action')


if __name__=='__main__':main()
