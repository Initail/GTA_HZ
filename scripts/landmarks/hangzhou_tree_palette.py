"""Original solid-crown Hangzhou tree archetypes, pure shared B mesh API.

Local metres become game-unit prototypes with one0.60 factor. Runtime instances
then apply only their variation scale/yaw/terrain translation. No scene imports,
alpha cards, source photos, georeferenced inventory or seasonal gameplay system.
"""
from __future__ import annotations
import math
import random
try:
    from city_config import load_city
except ImportError:
    from scripts.city_config import load_city

IDS=('camphor','willow','osmanthus','ginkgo','plane','peach','sweetgum','masson-pine')
DEFAULT_MATERIALS={'bark':'bark','bark_light':'pavement','foliage':'leaf','foliage_light':'leaflight',
                   'flowers':'pavement','autumn_yellow':'leaflight','autumn_red':'leaflight'}


def material_definitions():
    """Optional parent registration; no material creation or scene mutation here.

    Register once before all exports, then pass these keys through materialMap.
    Uniform material identities preserve batching and stable day/night lighting.
    """
    colors={'bark':(.22,.18,.13),'bark_light':(.50,.49,.41),'foliage':(.14,.27,.12),
            'foliage_light':(.23,.37,.16),'flowers':(.82,.42,.48),'autumn_yellow':(.70,.55,.12),'autumn_red':(.48,.21,.10)}
    return {slot:{'name':'hz_canopy_'+slot,'color':list(rgb),'roughness':.94,'metallic':0,'alpha':1,
                  'use':'authored flat PBR colors; no source texture or emission'} for slot,rgb in colors.items()}


def _dot(p,q):return sum(a*b for a,b in zip(p,q))
def _norm(p):
    l=math.sqrt(_dot(p,p));return tuple(v/l for v in p)
def _cross(p,q):return p[1]*q[2]-p[2]*q[1],p[2]*q[0]-p[0]*q[2],p[0]*q[1]-p[1]*q[0]
def _mix(p,q,t):return tuple(a+(b-a)*t for a,b in zip(p,q))


class _Tree:
    def __init__(self,lod,seed):
        self.lod,self.rng=lod,random.Random(seed);self.faces=[];self.parts={};self.part='unassigned'

    def face(self,slot,ps):
        if not all(all(math.isfinite(v) for v in p) for p in ps):raise ValueError('Nonfinite tree geometry')
        self.faces.append((slot,ps,self.part));self.parts[self.part]=self.parts.get(self.part,0)+len(ps)-2

    def tube(self,a,b,ra,rb,sides=None,slot='bark'):
        sides=sides or (8,6,4)[self.lod];axis=_norm(tuple(y-x for x,y in zip(a,b)))
        u=_norm(_cross(axis,(0,0,1) if abs(axis[2])<.90 else (1,0,0)));v=_cross(axis,u)
        rings=[]
        for center,radius in [(a,ra),(b,rb)]:
            rings.append([tuple(center[k]+radius*(u[k]*math.cos(i*math.tau/sides)+v[k]*math.sin(i*math.tau/sides)) for k in range(3)) for i in range(sides)])
        self.face(slot,list(reversed(rings[0])));self.face(slot,rings[1])
        for i in range(sides):
            mat=slot
            if slot=='bark' and self.part=='plane-bark' and self.lod<2 and i%3==0:mat='bark_light'
            self.face(mat,[rings[0][i],rings[0][(i+1)%sides],rings[1][(i+1)%sides],rings[1][i]])

    def curved_limb(self,points,radius):
        for i,(a,b) in enumerate(zip(points,points[1:])):
            t=i/(len(points)-1);self.tube(a,b,radius*(1-t*.74),radius*(1-(t+1/(len(points)-1))*.74))

    def blob(self,center,radii,slot='foliage',index=0):
        lat,lon=(6,10) if self.lod==0 else (4,8) if self.lod==1 else (3,6)
        cx,cy,cz=center;rx,ry,rz=radii;ph=index*.73+.23
        rings=[]
        for i in range(1,lat):
            theta=math.pi*i/lat;row=[]
            for j in range(lon):
                phi=j*math.tau/lon
                noise=1+.07*math.sin(3*phi+ph)*math.sin(theta)**2+.035*math.cos(5*phi-ph)*math.sin(theta)
                row.append((cx+rx*math.sin(theta)*math.cos(phi)*noise,cy+ry*math.sin(theta)*math.sin(phi)*noise,cz+rz*math.cos(theta)))
            rings.append(row)
        north=(cx,cy,cz+rz);south=(cx,cy,cz-rz)
        for j in range(lon):
            mat='foliage_light' if slot=='foliage' and self.lod<2 and j%4==0 else slot
            self.face(mat,[north,rings[0][j],rings[0][(j+1)%lon]])
            self.face(mat,[rings[-1][j],south,rings[-1][(j+1)%lon]])
            for upper,lower in zip(rings,rings[1:]):self.face(mat,[upper[j],lower[j],lower[(j+1)%lon],upper[(j+1)%lon]])


def _crown_points(sid,lod):
    """Normalized clump habits. Detailed and distant tiers share major lobes."""
    if sid in ('camphor','plane','osmanthus','peach'):
        ring_count=7 if sid!='peach' else 5
        radius=.58 if sid!='osmanthus' else .48
        z=.66 if sid!='peach' else .70
        points=[((math.cos(i*math.tau/ring_count+.24)*radius,math.sin(i*math.tau/ring_count+.24)*radius,z+.035*math.sin(i*2.1)),(.43,.40,.23)) for i in range(ring_count)]
        points += [((.12,-.05,.81),(.52,.47,.19))]
        if lod==0:points += [((math.cos(i*2.2)*.27,math.sin(i*2.2)*.27,.81),(.37,.34,.16)) for i in range(3)]
        if lod==1:points=points[:ring_count:2]+points[ring_count:]
        if lod==2:points=[((math.cos(i*math.tau/3)*.40,math.sin(i*math.tau/3)*.40,.70),(.63,.63,.27)) for i in range(3)]
        return points
    if sid=='ginkgo':
        points=[((0,0,.53),(.72,.69,.18)),((-.09,.03,.73),(.60,.58,.19)),((.05,-.03,.88),(.34,.33,.12))]
        if lod==0:points += [((math.cos(i*2.1)*.41,math.sin(i*2.1)*.40,.62+i*.065),(.36,.30,.20)) for i in range(4)]
        return points
    if sid=='sweetgum':
        points=[((-.19,.04,.58),(.64,.61,.22)),((.17,-.04,.75),(.58,.52,.20)),((-.05,.03,.89),(.31,.30,.11))]
        if lod==0:points += [((math.cos(i*2.1)*.44,math.sin(i*2.1)*.42,.67+i*.055),(.36,.31,.19)) for i in range(4)]
        return points
    if sid=='masson-pine':
        # Mature open umbrella tiers, not a single evergreen cone.
        points=[((-.31,.03,.60),(.65,.61,.09)),((.28,-.02,.77),(.64,.61,.11)),((0,.10,.92),(.43,.40,.08))]
        if lod==0:points += [((math.cos(i*2.0)*.46,math.sin(i*2.0)*.41,.66+i*.09),(.40,.37,.065)) for i in range(3)]
        return points
    if sid=='willow':
        points=[((-.28,.02,.79),(.61,.59,.19)),((.32,-.04,.78),(.58,.60,.19))]
        # Long narrow opaque leaf cascades preserve pendent habit without alpha.
        count=10 if lod==0 else 6 if lod==1 else 5
        for i in range(count):
            angle=i*math.tau/count+.16
            points.append(((math.cos(angle)*.68,math.sin(angle)*.65,.50+.05*math.sin(i*1.7)),(.24,.22,.30)))
        return points
    raise ValueError('Unknown local tree species')


def _geometry(sp,lod,season):
    sid=sp['id'];h,r=sp['prototypeHeightM'],sp['prototypeCrownRadiusM'];clear=sp['prototypeBranchClearanceM']
    t=_Tree(lod,sum(ord(c) for c in sid)*17)
    t.part='plane-bark' if sid=='plane' else 'trunk-and-branches'
    trunk_end=.76 if sid in ('ginkgo','sweetgum','masson-pine') else .49 if sid=='willow' else .40
    trunk=[(0,0,-.15),(.04*r,.015*r,h*trunk_end)]
    t.tube(trunk[0],trunk[1],sp['trunkRadiusM']*1.20,sp['trunkRadiusM']*.53)
    n=6 if lod==0 else 4 if lod==1 else 3
    for i in range(n):
        a=i*math.tau/n+.31;reach=.52 if sid not in ('ginkgo','sweetgum') else .40
        base=min(h*trunk_end*.94,clear+h*.13)
        e=(math.cos(a)*r*reach,math.sin(a)*r*reach,h*(.62+.07*(i%3)))
        t.tube((trunk[1][0],trunk[1][1],base),e,sp['trunkRadiusM']*.52,sp['trunkRadiusM']*.13)
        if lod==0:
            tip=(e[0]*1.40,e[1]*1.38,e[2]+h*.12)
            t.tube(e,tip,sp['trunkRadiusM']*.13,sp['trunkRadiusM']*.055,sides=5)
    if sid=='willow' and lod<2:
        t.part='willow-pendent-branches'
        for i in range(8 if lod==0 else 4):
            a=i*math.tau/(8 if lod==0 else 4)+.27
            points=[(.1*r*math.cos(a),.1*r*math.sin(a),h*.43),(.44*r*math.cos(a),.44*r*math.sin(a),h*.73),
                    (.78*r*math.cos(a),.76*r*math.sin(a),h*.58),(.83*r*math.cos(a),.80*r*math.sin(a),h*.26)]
            t.curved_limb(points,sp['trunkRadiusM']*.21)
    # Bare winter is an asset variant only. No timer or game-season logic added.
    bare=season=='winter' and sp['leafHabit']=='deciduous'
    if not bare:
        t.part='solid-crown';leaf='foliage'
        if season=='autumn' and sid=='ginkgo':leaf='autumn_yellow'
        if season=='autumn' and sid in ('sweetgum','plane'):leaf='autumn_red' if sid=='sweetgum' else 'autumn_yellow'
        points=_crown_points(sid,lod)
        for index,(center,rad) in enumerate(points):
            t.blob((center[0]*r,center[1]*r,center[2]*h),(rad[0]*r,rad[1]*r,rad[2]*h),leaf,index)
        if lod==0 and sid=='ginkgo':
            # A few original fan leaves at the canopy edge identify close views;
            # individual leaf sizes are enlarged authoreddetail, not survey.
            t.part='ginkgo-fan-leaf-detail'
            for i in range(12):
                a=i*math.tau/12;x,y=math.cos(a)*r*.91,math.sin(a)*r*.89;z=h*(.50+.32*(i%4)/3)
                leafsize=.19
                origin=(x,y,z)
                rim=[(x+math.cos(a+q)*leafsize,y+math.sin(a+q)*leafsize,z+.04*math.sin(q)) for q in [-.95,-.6,-.2,.2,.6,.95]]
                # A 4mm authored thickness is for a stable opaque game mesh,
                # not a measured botanical leaf thickness. Reversed duplicate
                # zero-thickness triangles disappear in B.finish's vertex weld.
                # Separate upper/lower skins and a closed rim retain both sides.
                half_thickness=.002
                upper=[(px,py,pz+half_thickness) for px,py,pz in [origin]+rim]
                lower=[(px,py,pz-half_thickness) for px,py,pz in [origin]+rim]
                for j in range(1,len(upper)-1):
                    t.face(leaf,[upper[0],upper[j],upper[j+1]])
                    t.face(leaf,[lower[0],lower[j+1],lower[j]])
                for j in range(len(upper)):
                    k=(j+1)%len(upper)
                    t.face(leaf,[lower[j],lower[k],upper[k],upper[j]])
        if (sid=='peach' and season=='spring') or (sid=='osmanthus' and season=='autumn'):
            t.part='seasonal-flower-suggestion'
            if lod<2:
                # Sparse opaque authored clusters: no fabricatedpetal census.
                for i in range(7 if lod==0 else 3):
                    a=i*2.4;rad=.10 if sid=='osmanthus' else .17
                    slot='autumn_yellow' if sid=='osmanthus' else 'flowers'
                    t.blob((math.cos(a)*r*.62,math.sin(a)*r*.62,h*(.72+.10*math.sin(i))),(.24*r,.20*r,rad*h),slot,i+50)
    # A single declared envelope contains every tier, for parentclearance proofs.
    # Normalizing allgeometry retains its relative branch/crown proportions and
    # prevents a distant tier from becoming wider or taller than nearbytiers.
    ps=[p for _,face,_ in t.faces for p in face];radius=max(math.hypot(p[0],p[1]) for p in ps);height=max(p[2] for p in ps)
    xy=r/radius;z=h/height
    return t,xy,z,bare


def build(b,lm,spec,scale=.6):
    if spec.get('cityId')!='hangzhou' or spec.get('speciesId') not in IDS:raise ValueError('Frozen Hangzhou tree prototype required')
    if spec.get('lod') not in (0,1,2):raise ValueError('LOD must be0,1,2')
    g=load_city('hangzhou')['geography']
    if not math.isclose(scale,g['scale'],abs_tol=1e-12):raise ValueError('Prototype realmetres must receive canonical scale once')
    sp=spec['prototype'];sid=spec['speciesId'];lod=spec['lod'];season=spec.get('season','summer')
    if sp['id']!=sid or season not in ('summer','spring','autumn','winter'):raise ValueError('Species/season mismatch')
    if sp['dimensionsBasis']!='estimated' or min(sp['prototypeHeightM'],sp['prototypeCrownRadiusM'],sp['trunkRadiusM'])<=0:raise ValueError('Positive estimatedprototype dimensions required')
    t,xy,z,bare=_geometry(sp,lod,season);mats=dict(DEFAULT_MATERIALS);mats.update(spec.get('materialMap',{}))
    old=b.frame;b.frame=(float(lm.get('x',0)),float(lm.get('z',0)),0);base=float(lm.get('y',0));triangles=0;used=set();points=[]
    try:
        for slot,ps,_ in t.faces:
            q=[(x*xy*scale,y*xy*scale,v*z*scale+base) for x,y,v in ps]
            b.face(mats[slot],q);triangles+=len(q)-2;used.add(mats[slot]);points.extend(q)
    finally:b.frame=old
    budget=spec['budget']
    if triangles>budget['maxTriangles'] or len(used)>budget['maxMaterials']:raise ValueError('Tree prototype exceeds frozenLOD budget')
    return {'id':spec['id'],'species':sid,'lod':lod,'seasonAssetVariant':season,'triangles':triangles,'faces':len(t.faces),'materials':sorted(used),
        'partTriangles':t.parts,'heightGame':max(p[2]-base for p in points),'crownRadiusGame':max(math.hypot(p[0],p[1]) for p in points),
        'minZGame':min(p[2]-base for p in points),'sourceHeightMetres':sp['prototypeHeightM'],'sourceCrownRadiusMetres':sp['prototypeCrownRadiusM'],
        'singleGeographicScale':scale,'instanceScalePolicy':'variation scale only; no second0.60','prototypeSpace':'local east/north/up, rootground at0, lm.y alreadygameunits',
        'bareWinterAssetVariant':bare,'newTextures':0,'newLights':0,'alphaCards':0,'geographicInventoryGenerated':False,
        'defaultMaterialsApproximate':not bool(spec.get('materialMap')),'dimensionBasis':'estimated procedural mature/maintained archetype, not measuredtree',
        'pendingSubscopes':spec['pendingSubscopes']}
