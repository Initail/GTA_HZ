"""Source-bound City Balcony exterior candidate, pure B API.

All spec dimensions are unscaled metres. lm x/z/y are already game units.
The caller owns Blender, export, terrain, water, routes and final materials.
"""
from __future__ import annotations
import math


def _cross(a,b):return a[0]*b[1]-a[1]*b[0]
def _inside(u,v,ring):
    hit=False
    for (a,b),(c,d) in zip(ring,ring[1:]+ring[:1]):
        if (b>v)!=(d>v) and u<(c-a)*(v-b)/(d-b)+a:hit=not hit
    return hit
def _public(u,v,spec,level):
    ring=spec['upperOuterUVMetres'] if level=='upper' else spec['lowerOuterUVMetres']
    return _inside(u,v,ring) and not any(_inside(u,v,h) for h in spec['glazedFootprintsUVMetres'])


def deck_height_metres(u,v,spec,level='upper'):
    """Neutral relative floor height, or None outside that public floor.

    Explicit level selection prevents upper park/lower frontage confusion.
    This is candidate geometry, not a surveyed elevation or validated route.
    """
    if level not in ('upper','lower'):raise ValueError('choose explicit upper/lower public level')
    return spec['estimates']['levels']['value'][level+'M'] if _public(u,v,spec,level) else None


def _to_game(u,v,lm,spec,scale):
    a=spec['axisRadiansEastCCW'];ca,sa=math.cos(a),math.sin(a)
    return [float(lm['x'])+(u*ca-v*sa)*scale,float(lm['z'])+(u*sa+v*ca)*scale]
def deck_height_game(x,z,lm,spec,scale=.6,level='upper'):
    """World game east/north inputs, world game up output; .60 exactly once."""
    _validate(spec,scale);a=spec['axisRadiansEastCCW'];ca,sa=math.cos(a),math.sin(a)
    dx,dz=(x-float(lm['x']))/scale,(z-float(lm['z']))/scale
    h=deck_height_metres(dx*ca+dz*sa,-dx*sa+dz*ca,spec,level)
    return None if h is None else float(lm.get('y',0))+h*scale


def _segments(ring,pitch):
    for a,b in zip(ring,ring[1:]+ring[:1]):
        length=math.dist(a,b);count=max(1,math.ceil(length/pitch))
        for i in range(count):
            yield tuple(a[j]+(b[j]-a[j])*i/count for j in [0,1]),tuple(a[j]+(b[j]-a[j])*(i+1)/count for j in [0,1])


def _piers(spec):
    ring=spec['lowerOuterUVMetres'];p=spec['estimates']['structure']['value']['pierPitchM']
    lo,hi=min(x[0] for x in ring),max(x[0] for x in ring);bot,top=min(x[1] for x in ring),max(x[1] for x in ring)
    u=math.ceil(lo/p)*p
    while u<hi:
        v=math.ceil(bot/p)*p
        while v<top:
            if _public(u,v,spec,'lower') and _public(u+1,v+1,spec,'lower') and _public(u-1,v-1,spec,'lower'):yield u,v
            v+=p
        u+=p
    # Separate source-registered approach bridges retain clear lower ground.
    for ent in spec['shoreApproachEdges']:
        u,v=ent['outerUVMetres']
        for f in [.35,.65]:yield u,v*f


def ground_footprints(lm,spec,scale=.6):
    """Explicit solid strips/piers in world game units, with vertical bounds.

    The whole park deck is not a ground obstacle. floor surfaces use the deck
    functions separately. Interior operation and safe entry remain pending.
    """
    _validate(spec,scale);levels=spec['estimates']['levels']['value'];w=spec['estimates']['structure']['value']['pierWidthM']
    result=[]
    def add(kind,ring,low,high,source):
        result.append({'kind':kind,'polygonGame':[_to_game(u,v,lm,spec,scale) for u,v in ring],
          'minYGame':float(lm.get('y',0))+low*scale,'maxYGame':float(lm.get('y',0))+high*scale,
          'basis':'estimated structure registered to fixed OSM footprint; not surveyed collision',
          'sourceFeatureIds':source})
    for u,v in _piers(spec):add('representative-pier',[(u-w/2,v-w/2),(u+w/2,v-w/2),(u+w/2,v+w/2),(u-w/2,v+w/2)],
      -levels['foundationDepthM'],levels['upperM']-levels['slabThicknessM'],['relation/8718551'])
    for a,b in zip(spec['lowerOuterUVMetres'][:7],spec['lowerOuterUVMetres'][1:8]):
        d=math.dist(a,b);du,dv=(b[0]-a[0])/d,(b[1]-a[1])/d;t=.14
        add('lower-front-glass-strip',[(a[0]-dv*t,a[1]+du*t),(a[0]+dv*t,a[1]-du*t),
          (b[0]+dv*t,b[1]-du*t),(b[0]-dv*t,b[1]+du*t)],levels['lowerM'],
          levels['upperM']-levels['slabThicknessM'],['relation/8718551'])
    for ring,ident in zip(spec['glazedFootprintsUVMetres'],spec['sourceFeatureIds'][1:]):
        for a,b in zip(ring,ring[1:]+ring[:1]):
            d=math.dist(a,b);du,dv=(b[0]-a[0])/d,(b[1]-a[1])/d;t=.14
            add('glazed-wall-strip',[(a[0]-dv*t,a[1]+du*t),(a[0]+dv*t,a[1]-du*t),
              (b[0]+dv*t,b[1]-du*t),(b[0]-dv*t,b[1]+du*t)],levels['lowerM'],
              levels['upperM']+spec['estimates']['glazedHeads']['value']['roofRiseM'],[ident])
    return result


def _validate(spec,scale):
    if spec.get('id')!='city-balcony' or spec.get('cityId')!='hangzhou':raise ValueError('wrong city/object spec')
    if abs(scale-spec['coordinatePolicy']['scaleOnce'])>1e-12:raise ValueError('city dimensions must scale exactly once')


class _Mesh:
    def __init__(self,b,base,scale):self.b=b;self.base=base;self.scale=scale;self.faces=0;self.materials=set()
    def face(self,mat,pts):
        self.b.face(mat,[(u*self.scale,v*self.scale,self.base+h*self.scale) for u,v,h in pts])
        self.faces+=1;self.materials.add(mat)
    def beam(self,mat,a,b,width,caps=True):
        d=tuple(b[i]-a[i] for i in range(3));length=math.sqrt(sum(x*x for x in d))
        if length<1e-8:raise ValueError('zero-length beam')
        d=tuple(x/length for x in d);h=math.hypot(d[0],d[1]);side=(-d[1]/h,d[0]/h,0) if h>1e-8 else (1,0,0)
        normal=(d[1]*side[2]-d[2]*side[1],d[2]*side[0]-d[0]*side[2],d[0]*side[1]-d[1]*side[0])
        ends=[[tuple(p[i]+width*.5*(s*side[i]+t*normal[i]) for i in range(3)) for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]] for p in [a,b]]
        if caps:self.face(mat,ends[0][::-1]);self.face(mat,ends[1])
        for i in range(4):self.face(mat,[ends[0][i],ends[0][(i+1)%4],ends[1][(i+1)%4],ends[1][i]])
    def prism(self,mat,ring,lo,hi):
        self.face(mat,[(u,v,lo) for u,v in ring[::-1]]);self.face(mat,[(u,v,hi) for u,v in ring])
        for a,b in zip(ring,ring[1:]+ring[:1]):self.face(mat,[(a[0],a[1],lo),(b[0],b[1],lo),(b[0],b[1],hi),(a[0],a[1],hi)])


def _rail(mesh,ring,height,spec,open_edges=None):
    rails=spec['estimates']['rails']['value'];open_edges=open_edges or set()
    for index,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
        if index in open_edges:continue
        count=max(1,math.ceil(math.dist(a,b)/rails['panelPitchM']))
        for j in range(count):
            p=tuple(a[k]+(b[k]-a[k])*j/count for k in [0,1]);q=tuple(a[k]+(b[k]-a[k])*(j+1)/count for k in [0,1])
            mesh.face('landmarkglass',[(p[0],p[1],height+.1),(q[0],q[1],height+.1),(q[0],q[1],height+rails['heightM']),(p[0],p[1],height+rails['heightM'])])
            mesh.face('landmarkglass',[(p[0],p[1],height+rails['heightM']),(q[0],q[1],height+rails['heightM']),(q[0],q[1],height+.1),(p[0],p[1],height+.1)])
            mesh.beam('steel',(p[0],p[1],height),(p[0],p[1],height+rails['heightM']),rails['frameWidthM'])
            # Adjacent top-rail segments meet; hidden internal end caps need
            # no triangles. Source outline and visible cross-section stay.
            mesh.beam('steel',(p[0],p[1],height+rails['heightM']),(q[0],q[1],height+rails['heightM']),rails['frameWidthM'],caps=False)


def build(b,lm,spec,scale=.6):
    _validate(spec,scale);old=b.frame;mesh=_Mesh(b,float(lm.get('y',0)),scale)
    b.frame=(float(lm['x']),float(lm['z']),spec['axisRadiansEastCCW'])
    levels=spec['estimates']['levels']['value'];lower,upper=levels['lowerM'],levels['upperM'];thickness=levels['slabThicknessM']
    try:
        for name,h in [('lower',lower),('upper',upper)]:
            ring=spec[name+'OuterUVMetres'];ts=spec[name+'TrianglesUVMetres']
            for index,pts in enumerate(ts):
                # Sparse contrasting river-edge paving follows the actual
                # cantilever polygon. This is no invented park or water slab.
                material=spec['upperTriangleMaterials'][index] if name=='upper' else 'concrete'
                mesh.face(material,[(u,v,h) for u,v in pts]);mesh.face('concrete',[(u,v,h-thickness) for u,v in pts[::-1]])
            rings=[ring,*spec['glazedFootprintsUVMetres']]
            for ri,edge in enumerate(rings):
                signed=sum(_cross(a,t) for a,t in zip(edge,edge[1:]+edge[:1]))
                if (ri==0 and signed<0) or (ri>0 and signed>0):edge=list(reversed(edge))
                for a,t in zip(edge,edge[1:]+edge[:1]):mesh.face('concrete',[(a[0],a[1],h-thickness),(t[0],t[1],h-thickness),(t[0],t[1],h),(a[0],a[1],h)])
        # Exact upper outline keeps both rear bridge entry mouths open.
        _rail(mesh,spec['upperOuterUVMetres'],upper,spec,{9,13,14,15})
        _rail(mesh,spec['lowerOuterUVMetres'],lower,spec,{7,8,9,10})
        w=spec['estimates']['structure']['value']['pierWidthM'];piers=list(_piers(spec))
        for u,v in piers:
            ring=[(u-w/2,v-w/2),(u+w/2,v-w/2),(u+w/2,v+w/2),(u-w/2,v+w/2)]
            mesh.prism('concrete',ring,-levels['foundationDepthM'],upper-thickness)
        # Lower river frontage glass is repeated between structural posts;
        # shoreside remains open for an integrator-verified entrance route.
        for a,t in zip(spec['lowerOuterUVMetres'][:7],spec['lowerOuterUVMetres'][1:8]):
            for p,q in _segments([a,t],spec['estimates']['glazedHeads']['value']['mullionPitchM']):
                # This helper traverses both directions; source frontage emits
                # one outward panel and one inward panel, no thick opaque wall.
                mesh.face('darkglass',[(p[0],p[1],lower+.15),(q[0],q[1],lower+.15),(q[0],q[1],upper-thickness),(p[0],p[1],upper-thickness)])
        for ring in spec['glazedFootprintsUVMetres']:
            # Interior rings are normally clockwise in GeoJSON. Glass heads
            # need outward walls/upward roofs while retaining the source plan.
            if sum(_cross(a,t) for a,t in zip(ring,ring[1:]+ring[:1]))<0:ring=list(reversed(ring))
            top=upper+spec['estimates']['glazedHeads']['value']['roofRiseM']
            mesh.face('landmarkglass',[(u,v,top) for u,v in ring])
            for a,t in zip(ring,ring[1:]+ring[:1]):
                mesh.face('darkglass',[(a[0],a[1],lower),(t[0],t[1],lower),(t[0],t[1],top),(a[0],a[1],top)])
                count=max(1,math.ceil(math.dist(a,t)/spec['estimates']['glazedHeads']['value']['mullionPitchM']))
                for j in range(count):
                    u,v=[a[k]+(t[k]-a[k])*j/count for k in [0,1]]
                    mesh.beam('steel',(u,v,lower),(u,v,top),.11)
                mesh.beam('steel',(a[0],a[1],top),(t[0],t[1],top),.15)
            _rail(mesh,ring,upper,spec)
        # Source-registered shore bridge transverse beams, not a new ramp.
        for ent in spec['shoreApproachEdges']:
            i,j=ent['sourceEdgeVertexIndices'];a,t=spec['upperOuterUVMetres'][i],spec['upperOuterUVMetres'][j]
            for f in [.30,.55,.80]:
                p,q=(a[0],a[1]*f),(t[0],t[1]*f)
                mesh.beam('steel',(p[0],p[1],upper-thickness-.4),(q[0],q[1],upper-thickness-.4),.6)
        # Circle skylights have referenced shape, but this limited module does
        # not claim survey positions or cut the structural slabs without a
        # verified full-section drawing. Raised glass circles are explicit.
        for u,v in [(-128,-46),(-82,-48),(-32,-49),(17,-51),(66,-47),(112,-39)]:
            if not _public(u,v,spec,'upper'):continue
            radius=spec['estimates']['skylights']['value']['radiusM'];count=20
            ring=[(u+radius*math.cos(i*2*math.pi/count),v+radius*math.sin(i*2*math.pi/count)) for i in range(count)]
            mesh.face('landmarkglass',[(x,y,upper+.035) for x,y in ring])
            for a,t in zip(ring,ring[1:]+ring[:1]):mesh.beam('steel',(a[0],a[1],upper+.05),(t[0],t[1],upper+.05),.065)
        return {'id':'city-balcony','scope':spec['scope'],'faces':mesh.faces,'materials':sorted(mesh.materials),
          'publicLevelsMetres':{'upper':upper,'lower':lower},'mappedGlazedParts':3,'shoreApproachCount':2,
          'representativePierCount':len(piers),'waterMeshes':0,'lights':0,'stairsRampsLiftMeshes':0,
          'groundFootprintCount':len(ground_footprints(lm,spec,scale)),
          'limitations':'Neutral two-floor datum and glazed head section estimated. Six circles are surfaced skylight representations, not fully open surveyed shafts. Entry steps/ramps/lift/current terrain/navigation/runtime pending.'}
    finally:b.frame=old
