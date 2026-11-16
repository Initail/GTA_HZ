"""Big Lotus main-stadium candidate, independent source-bound B mesh module.

The caller owns Blender, materials, export and shared-world integration.
Source rings/relative metre dimensions scale once; lm x/z/y are game units.
This is a reference-informed shell and bowl, not a surveyed site/platform.
"""
from __future__ import annotations
import math


def _cross2(a,b):return a[0]*b[1]-a[1]*b[0]


def radial_boundary_metres(ring,theta):
    """Intersect the source footprint with a radial ray, preserving map lobes."""
    d=(math.cos(theta),math.sin(theta));hits=[]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        edge=(b[0]-a[0],b[1]-a[1]);den=_cross2(d,edge)
        if abs(den)<1e-10:continue
        r=_cross2(a,edge)/den;t=_cross2(a,d)/den
        if r>0 and -1e-9<=t<=1+1e-9:hits.append(r)
    if not hits:raise ValueError('Source ring does not surround stadium anchor')
    return max(hits)


def _lerp(a,b,t):return a+(b-a)*t


def _smooth_samples(stations,u,column):
    """Monotone cubic interpolation keeps reported max height unexceeded."""
    slopes=[(b[column]-a[column])/(b[0]-a[0]) for a,b in zip(stations,stations[1:])]
    tangents=[slopes[0]]
    for a,b in zip(slopes,slopes[1:]):tangents.append(0 if a*b<=0 else 2*a*b/(a+b))
    tangents.append(slopes[-1])
    for i,(a,b) in enumerate(zip(stations,stations[1:])):
        if a[0]<=u<=b[0]:
            h=b[0]-a[0];t=(u-a[0])/h
            return ((2*t**3-3*t*t+1)*a[column]+(t**3-2*t*t+t)*h*tangents[i]
                    +(-2*t**3+3*t*t)*b[column]+(t**3-t*t)*h*tangents[i+1])
    raise ValueError('curve parameter outside [0,1]')


def _profile(u):
    # radius interpolation fraction from outer shell to source inner opening.
    stations=[(0,.22,2.5),(.16,.07,18),(.38,0,42),(.62,.13,55),
              (.73,.45,59.4),(.88,.80,55),(1,1,46.5)]
    return _smooth_samples(stations,u,1),_smooth_samples(stations,u,2)


def petal_point_metres(spec,theta,u,v,small=False):
    """Estimated curved thin petal, constrained to fixed outer/inner rings."""
    pitch=2*math.pi/spec['largePetalCount']
    width=spec['estimates']['petalWidth']['value']
    maximum=width['smallMaxHalfPitch' if small else 'largeMaxHalfPitch']
    if small:
        half=pitch*(.027+(maximum-.027)*math.sin(math.pi*u)**.72)
    else:
        # Broad inner canopy ends join the mapped roof rim; only the outer wall
        # tips taper to the ground. Avoid fictitious huge gaps over the bowl.
        widths=width['largeHalfPitchProfile']
        half=pitch*_smooth_samples(widths,u,1)
    angle=theta+half*v
    ro=radial_boundary_metres(spec['outerUVMetres'],angle)
    ri=radial_boundary_metres(spec['innerUVMetres'],angle)
    f,z=_profile(u);r=ro+(ri-ro)*f
    # Mild transverse curvature; cladding section/cantilever remain estimated.
    z-=2.3*v*v*math.sin(math.pi*u)
    if small:z*=width['smallHeightFactor']
    return (r*math.cos(angle),r*math.sin(angle),z)


def _normal(spec,theta,u,v,small):
    a=petal_point_metres(spec,theta,max(0,u-.001),v,small)
    b=petal_point_metres(spec,theta,min(1,u+.001),v,small)
    x,y,z=petal_point_metres(spec,theta,u,v,small);r=math.hypot(x,y)
    dr=(b[0]-a[0])*x/r+(b[1]-a[1])*y/r;dz=b[2]-a[2]
    norm=math.hypot(dr,dz)
    return (dz*x/r/norm,dz*y/r/norm,-dr/norm)


def _offset(p,n,amount):return tuple(p[i]+n[i]*amount for i in range(3))


class _Mesh:
    def __init__(self,b,base,scale):self.b=b;self.base=base;self.scale=scale;self.faces=0;self.materials=set()
    def face(self,mat,pts):
        self.b.face(mat,[(x*self.scale,y*self.scale,self.base+z*self.scale) for x,y,z in pts])
        self.faces+=1;self.materials.add(mat)
    def box(self,mat,center,size):
        x,y,z=center;a,b,c=(v/2 for v in size)
        p=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
           (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:self.face(mat,[p[i] for i in ids])
    def beam(self,mat,a,b,width):
        d=tuple(b[i]-a[i] for i in range(3));length=math.sqrt(sum(v*v for v in d))
        if length<1e-8:raise ValueError('zero length beam')
        d=tuple(v/length for v in d);h=math.hypot(d[0],d[1])
        side=(-d[1]/h,d[0]/h,0) if h>1e-8 else (1,0,0)
        normal=(d[1]*side[2]-d[2]*side[1],d[2]*side[0]-d[0]*side[2],d[0]*side[1]-d[1]*side[0])
        corners=[]
        for origin in [a,b]:
            corners.append([tuple(origin[i]+width*.5*(s*side[i]+t*normal[i]) for i in range(3))
                            for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]])
        self.face(mat,corners[0][::-1]);self.face(mat,corners[1])
        for i in range(4):self.face(mat,[corners[0][i],corners[0][(i+1)%4],corners[1][(i+1)%4],corners[1][i]])


def _petal(mesh,spec,theta,small):
    us=[0,.08,.16,.38,.50,.62,.73,.88,.94,1];vs=[-1,-.5,0,.5,1]
    thickness=spec['estimates']['petalCurve']['value']['thicknessM']
    material='darkglass' if small else 'silver'
    p=[[petal_point_metres(spec,theta,u,v,small) for v in vs] for u in us]
    back=[[_offset(p[i][j],_normal(spec,theta,u,v,small),-thickness)
           for j,v in enumerate(vs)] for i,u in enumerate(us)]
    for i in range(len(us)-1):
        for j in range(len(vs)-1):
            mesh.face(material,[p[i][j],p[i][j+1],p[i+1][j+1],p[i+1][j]])
            mesh.face('concrete' if not small else 'darkglass',
                      [back[i][j],back[i+1][j],back[i+1][j+1],back[i][j+1]])
    for i in range(len(us)-1):
        mesh.face('steel',[p[i][0],p[i+1][0],back[i+1][0],back[i][0]])
        mesh.face('steel',[p[i+1][-1],p[i][-1],back[i][-1],back[i+1][-1]])
    for j in range(len(vs)-1):
        mesh.face('steel',[p[0][j+1],p[0][j],back[0][j],back[0][j+1]])
        mesh.face('steel',[p[-1][j],p[-1][j+1],back[-1][j+1],back[-1][j]])
    # Long ribs conform to the shell rather than producing vertical box fins.
    for v in ([-.48,.48] if small else [-.65,0,.65]):
        for u,w in zip(us,us[1:]):
            q=[]
            for t,s in [(u,-1),(u,1),(w,1),(w,-1)]:
                a=petal_point_metres(spec,theta,t,v,small);r=math.hypot(a[0],a[1])
                epsilon=.10/max(r,1);angle=math.atan2(a[1],a[0])+s*epsilon
                n=_normal(spec,theta,t,v,small)
                q.append(_offset((r*math.cos(angle),r*math.sin(angle),a[2]),n,.04))
            mesh.face('steel',q)
    # Sparse panel/louver cadence, representative intervals explicitly estimated.
    for u in [.13,.25,.38,.50,.62,.73,.84,.94]:
        divisions=3 if small else 6
        for j in range(divisions):
            v=-1+2*j/divisions;w=-1+2*(j+1)/divisions
            q=[]
            for t,s in [(u-.0018,v),(u-.0018,w),(u+.0018,w),(u+.0018,v)]:
                a=petal_point_metres(spec,theta,t,s,small)
                q.append(_offset(a,_normal(spec,theta,t,s,small),.055))
            mesh.face('silver' if small else 'steel',q)
    if not small:
        # Simplified real truss character, not a reproduced engineering section.
        line=[_offset(petal_point_metres(spec,theta,u,0,False),_normal(spec,theta,u,0,False),-1.4)
              for u in [.16,.38,.62,.88,1]]
        for a,b in zip(line,line[1:]):mesh.beam('silver',a,b,.48)
        for u,w in [(.38,.62),(.62,.88)]:
            a=_offset(petal_point_metres(spec,theta,u,-.68,False),_normal(spec,theta,u,-.68,False),-1.4)
            b=_offset(petal_point_metres(spec,theta,w,.68,False),_normal(spec,theta,w,.68,False),-1.4)
            mesh.beam('silver',a,b,.32)


def _ellipse(theta,major,minor):
    return 1/math.sqrt((math.cos(theta)/major)**2+(math.sin(theta)/minor)**2)


def _polar(theta,r,z):return(r*math.cos(theta),r*math.sin(theta),z)


def build(b,lm,spec,scale=.6):
    if spec.get('id')!='big-lotus' or spec.get('cityId')!='hangzhou':raise ValueError('wrong object/city spec')
    if abs(scale-spec['coordinatePolicy']['scaleOnce'])>1e-12:raise ValueError('city dimensions must be scaled exactly once')
    if (spec['largePetalCount'],spec['smallPetalCount'])!=(28,27):raise ValueError('reported28/27 petal contract changed')
    old=b.frame;mesh=_Mesh(b,float(lm.get('y',0)),scale)
    b.frame=(float(lm['x']),float(lm['z']),spec['axisRadiansEastCCW'])
    pitch=2*math.pi/28;roof_counts={'large':0,'small':0};segments=84
    try:
        for i in range(28):_petal(mesh,spec,i*pitch,False);roof_counts['large']+=1
        # The missing small-petal interval is an explicitly unverified phase near
        # the axis. Do not infer a real signed north gate from this representation.
        for i in range(27):_petal(mesh,spec,(i+.5)*pitch,True);roof_counts['small']+=1
        # Running oval and field stay below the roof opening; no top closure disk.
        track_a,track_b=[v/2 for v in spec['estimates']['bowl']['value']['trackMajorMinorM']]
        field_boundary=[]
        for i in range(segments):
            a,t=2*math.pi*i/segments,2*math.pi*(i+1)/segments
            ro0,ro1=_ellipse(a,track_a,track_b),_ellipse(t,track_a,track_b)
            ri0,ri1=_ellipse(a,track_a-8,track_b-8),_ellipse(t,track_a-8,track_b-8)
            mesh.face('asphalt',[_polar(a,ri0,.04),_polar(a,ro0,.04),_polar(t,ro1,.04),_polar(t,ri1,.04)])
            field_boundary.append(_polar(a,ri0,.045))
            for offset in [1,3,5,7]:
                r0,r1=_ellipse(a,track_a-offset,track_b-offset),_ellipse(t,track_a-offset,track_b-offset)
                mesh.face('roadline',[_polar(a,r0-.055,.052),_polar(a,r0+.055,.052),
                                       _polar(t,r1+.055,.052),_polar(t,r1-.055,.052)])
        mesh.face('park',field_boundary)
        length,width=spec['estimates']['bowl']['value']['pitchLengthWidthM'];ha,hb=length/2,width/2
        for u in [-ha,0,ha]:mesh.box('roadline',(u,0,.06),(.12,width,.025))
        for v in [-hb,hb]:mesh.box('roadline',(0,v,.06),(length,.12,.025))
        for end in [-1,1]:
            for y in [-20.16,20.16]:mesh.box('roadline',(end*(ha-8.25),y,.063),(16.5,.12,.025))
            mesh.box('roadline',(end*(ha-16.5),0,.063),(.12,40.32,.025))
            mesh.beam('silver',(end*ha,-3.66,.15),(end*ha,-3.66,2.44),.16)
            mesh.beam('silver',(end*ha,3.66,.15),(end*ha,3.66,2.44),.16)
            mesh.beam('silver',(end*ha,-3.66,2.44),(end*ha,3.66,2.44),.16)
        for i in range(36):
            a,t=2*math.pi*i/36,2*math.pi*(i+1)/36
            mesh.face('roadline',[_polar(a,9.10,.063),_polar(a,9.22,.063),_polar(t,9.22,.063),_polar(t,9.10,.063)])
        # Three terraced seating bands. Reduced rows represent a bowl, not80800
        # individual chairs or a verified current seat-color mosaic.
        for tier,(h0,h1) in enumerate(spec['estimates']['bowl']['value']['tierRangesM']):
            for row in range(5):
                for i in range(segments):
                    a,t=2*math.pi*i/segments,2*math.pi*(i+1)/segments
                    def radius(theta,f):
                        ri=radial_boundary_metres(spec['innerUVMetres'],theta)
                        ro=radial_boundary_metres(spec['outerUVMetres'],theta)
                        lo,hi=spec['estimates']['bowl']['value']['tierCanopyRadialFractions'][tier]
                        base=_ellipse(theta,track_a+4,track_b+4) if lo is None else ri+(ro-ri)*lo
                        return _lerp(base,ri+(ro-ri)*hi,f)
                    f,g=row/5,(row+1)/5;z0,z1=_lerp(h0,h1,f),_lerp(h0,h1,g)
                    r0,r1=radius(a,f),radius(t,f);s0,s1=radius(a,g),radius(t,g)
                    mat='landmarkglass' if (i//7+tier)%5==0 else 'civicred'
                    mesh.face(mat,[_polar(a,r0,z1),_polar(a,s0,z1),_polar(t,s1,z1),_polar(t,r1,z1)])
                    mesh.face('concrete',[_polar(a,r0,z0),_polar(a,r0,z1),_polar(t,r1,z1),_polar(t,r1,z0)])
            # A deep recess and beam at each next tier/annular concourse.
            for i in range(segments):
                a,t=2*math.pi*i/segments,2*math.pi*(i+1)/segments
                r0,r1=radial_boundary_metres(spec['innerUVMetres'],a),radial_boundary_metres(spec['innerUVMetres'],t)
                o0,o1=radial_boundary_metres(spec['outerUVMetres'],a),radial_boundary_metres(spec['outerUVMetres'],t)
                f=spec['estimates']['bowl']['value']['tierCanopyRadialFractions'][tier][1]
                r0+=f*(o0-r0);r1+=f*(o1-r1)
                mesh.face('roof',[_polar(a,r0,h1+1.2),_polar(t,r1,h1+1.2),_polar(t,r1,h1+2.5),_polar(a,r0,h1+2.5)])
        # Façade behind the petal-tip gaps: bounded floor bands, glass strips
        # above8m and real ground-level gaps between columns, no opaque disk.
        for i in range(segments):
            a,t=2*math.pi*i/segments,2*math.pi*(i+1)/segments
            ro0,ro1=radial_boundary_metres(spec['outerUVMetres'],a)*.91,radial_boundary_metres(spec['outerUVMetres'],t)*.91
            for z in [8,15,25,35]:
                mesh.face('concrete',[_polar(a,ro0,z-.6),_polar(t,ro1,z-.6),_polar(t,ro1,z),_polar(a,ro0,z)])
            for z,h in [(8,14.4),(15,24.4),(25,34.4)]:
                mesh.face('darkglass',[_polar(a,ro0,z),_polar(t,ro1,z),_polar(t,ro1,h),_polar(a,ro0,h)])
        for i in range(28):
            theta=(i+.5)*pitch;r=radial_boundary_metres(spec['outerUVMetres'],theta)*.91
            mesh.box('concrete',_polar(theta,r,4),(1.0,1.0,8))
        # Inner roof edge remains an annular lip; it never spans across the void.
        for i in range(segments):
            a,t=2*math.pi*i/segments,2*math.pi*(i+1)/segments
            r0,r1=radial_boundary_metres(spec['innerUVMetres'],a),radial_boundary_metres(spec['innerUVMetres'],t)
            p=[_polar(a,r0,45.4),_polar(t,r1,45.4),_polar(t,r1,46.8),_polar(a,r0,46.8)]
            mesh.face('silver',p)
            mesh.face('silver',[_polar(a,r0,46.8),_polar(t,r1,46.8),_polar(t,r1+1.2,46.8),_polar(a,r0+1.2,46.8)])
    finally:b.frame=old
    return {'scope':spec['scope'],'sourceFeatureIds':spec['sourceFeatureIds'],
      'faces':mesh.faces,'materials':sorted(mesh.materials),'petalCounts':roof_counts,
      'seatingTiers':3,'roofCenterClosureMeshes':0,'waterMeshes':0,'lights':0,
      'sourceAxisRadiansEastCCW':spec['axisRadiansEastCCW'],'maxNominalHeightM':spec['heightM'],
      'scaleOnce':scale,'baseHeightGame':float(lm.get('y',0)),
      'sourceOpeningMajorMinorM':spec['openingMajorMinorM'],
      'missingSmallPetalIntervalRadians':[27*pitch,28*pitch],
      'missingIntervalBasis':'estimated phase; no verified geographic gate identification',
      'integrationContract':spec['integrationContract'],'pending':spec['pendingSubscopes'],
      'accuracyClaim':'reference-informed isolated shell/bowl candidate; not field-surveyed or site-complete'}
