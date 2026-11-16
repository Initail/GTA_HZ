"""Independent Leifeng mapped hill/site candidate; frozen tower stays untouched.

Height is GLO30-v3 ground ESTIMATE, not measured architectural finished levels.
No water, invented source junction, scene setup, exports or moving escalator.
lm.y denotes GAME ordinate of EGM2008 zero; source real heights scale once.
"""
from __future__ import annotations
import math
try:
    from city_config import load_city,project
except ImportError:
    from scripts.city_config import load_city,project


def _context(lm,spec):
    if spec.get('id')!='leifeng-site' or spec.get('cityId')!='hangzhou':raise ValueError('Expected Hangzhou leifeng-site spec')
    city=load_city('hangzhou');g=city['geography'];a=spec['anchor'];x,z=project(a['lon'],a['lat'],city);lx,lz=project(lm.get('lon',a['lon']),lm.get('lat',a['lat']),city)
    return city,g,((x-lx)/g['scale'],(z-lz)/g['scale'])


def _game(p,lm,offset,scale):return (lm['x']+(p[0]+offset[0])*scale,lm['z']+(p[1]+offset[1])*scale,float(lm.get('y',0))+p[2]*scale)


def tower_placement(lm,spec,scale=.6):
    """Return candidate game base for original tower, never re-scale its lm.y."""
    city,g,offset=_context(lm,spec);h=spec['towerPlacement']['groundEstimateEgm2008M'];p=_game((0,0,h),lm,offset,scale);a=spec['anchor']
    return {'id':'leifeng-pagoda','lon':a['lon'],'lat':a['lat'],'x':p[0],'z':p[1],'y':p[2],
       'status':'estimated-placement-not-finishedfloor','sourceHeightEgm2008M':h,'errorGame':12*scale,'entranceAccepted':False}


def ground_footprints(lm,spec,scale=.6):
    """Hill/pavement are height surfaces, not a whole solid building blocker."""
    _context(lm,spec);return []


def walk_surfaces(lm,spec,scale=.6,allow_estimated=False,include_terrain=False):
    """Original source-bound candidate triangle surfaces; NOT actor acceptance."""
    if not allow_estimated:raise ValueError('Leifeng ground/steps/entrance still blocked; explicitly allow_estimated for preview surfaces')
    city,g,offset=_context(lm,spec);rows=[]
    for patch in spec['terrainPatches']:
        if patch['part']=='ground-estimate' and not include_terrain:continue
        rows.append({'sourcePart':patch['part'],'verticesGameENU':[_game(p,lm,offset,scale) for p in patch['verticesMetresENU']],
          'status':'candidate-estimated','heightErrorGame':12*scale,'traversalAccepted':False,'safeArrivalAccepted':False})
    return rows


def walk_surface(lon,lat,lm,spec,scale=.6,allow_estimated=False,source_way_id=None):
    """Candidate game-height at dry source surface, else None. Explicit opt-in.

    Never synthesizes the14m missing edge to the frozen tower. When a sourceway
    is supplied only its footprint is queried; a terrain crossing is no junction.
    """
    if not allow_estimated:raise ValueError('Measured ground/entry unavailable; allow_estimated=True is preview only')
    city,g,offset=_context(lm,spec);a=spec['anchor'];q=project(lon,lat,city);origin=project(a['lon'],a['lat'],city);p=((q[0]-origin[0])/g['scale'],(q[1]-origin[1])/g['scale'])
    parts=spec['terrainPatches'];parts=sorted(parts,key=lambda t:0 if t['part'].startswith('path-') else 1 if t['part']=='base-apron-estimate' else 2)
    if source_way_id is not None:
        ident=str(source_way_id).removeprefix('way/');parts=[t for t in parts if t['part']=='path-'+ident]
    for t in parts:
        aa,bb,cc=t['verticesMetresENU'];den=(bb[1]-cc[1])*(aa[0]-cc[0])+(cc[0]-bb[0])*(aa[1]-cc[1])
        if abs(den)<1e-12:continue
        u=((bb[1]-cc[1])*(p[0]-cc[0])+(cc[0]-bb[0])*(p[1]-cc[1]))/den;v=((cc[1]-aa[1])*(p[0]-cc[0])+(aa[0]-cc[0])*(p[1]-cc[1]))/den;w=1-u-v
        if min(u,v,w)>=-1e-8:
            h=u*aa[2]+v*bb[2]+w*cc[2]
            return {'heightGame':float(lm.get('y',0))+h*scale,'sourcePart':t['part'],'status':'candidate-estimated','traversalAccepted':False,'heightErrorGame':12*scale}
    return None


class _Mesh:
    def __init__(self,b,scale,offset,datum):self.b=b;self.scale=scale;self.offset=offset;self.datum=datum;self.triangles=self.faces=0;self.materials=set()
    def face(self,mat,p):
        self.b.face(mat,[((x+self.offset[0])*self.scale,(y+self.offset[1])*self.scale,self.datum+z*self.scale) for x,y,z in p]);self.triangles+=len(p)-2;self.faces+=1;self.materials.add(mat)
    def strip(self,mat,pt,s0,s1,t0,t1,h0,h1):self.face(mat,[pt(s0,t0,h0),pt(s1,t0,h1),pt(s1,t1,h1),pt(s0,t1,h0)])
    def rail(self,pt,a,b,t,h0,h1,mat='silver',half=.035):
        # Narrow rectangular members, originalgeometry; not copied textures.
        v=[pt(s,q,h) for h in [h0,h0+half*2] for s,q in [(a,t-half),(b,t-half),(b,t+half),(a,t+half)]]
        # Allow slope by lifting the second longitudinal end independently.
        for i in [1,2,5,6]:v[i]=(v[i][0],v[i][1],v[i][2]+h1-h0)
        for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)]:self.face(mat,[v[i] for i in ids])


def _static_approach(m,spec):
    path=next(p for p in spec['sourcePaths'] if p['id']=='way/340652169');ps=sorted(path['profile'],key=lambda p:p['coordinateWGS84'][1]);a,b=ps[0],ps[-1];x,y=a['pointLocalMetresEN'];dx=b['pointLocalMetresEN'][0]-x;dy=b['pointLocalMetresEN'][1]-y;length=math.hypot(dx,dy);u=(dx/length,dy/length);n=(-u[1],u[0]);lo=a['heightEstimatedEgm2008M']+.06;hi=b['heightEstimatedEgm2008M']+.06
    def pt(s,t,h):return (x+s*u[0]+t*n[0],y+s*u[1]+t*n[1],h)
    # Two STATIC inclined belts and glass balustrades; no roof/gate guessed.
    for center in [-.9,.9]:
        m.strip('steel',pt,0,length,center-.8,center+.8,lo-.25,hi-.25)
        m.strip('rubber',pt,0,length,center-.7,center+.7,lo+.035,hi+.035)
        for t in [center-.78,center+.78]:
            m.face('landmarkglass',[pt(0,t,lo),pt(length,t,hi),pt(length,t,hi+1.1),pt(0,t,lo+1.1)])
            m.rail(pt,0,length,t,lo+1.1,hi+1.1,'steel',.04)
    count=max(1,round(abs(hi-lo)/.18))
    for left,right in [(-6,-2),(2,6)]:
        for i in range(count):
            s=length*i/count;t=length*(i+1)/count;h=lo+(hi-lo)*(i+1)/count;prev=lo+(hi-lo)*i/count
            m.strip('pavement',pt,s,t,left,right,h,h)
            m.face('concrete',[pt(s,left,prev),pt(s,right,prev),pt(s,right,h),pt(s,left,h)])
        m.rail(pt,0,length,(left+right)/2,lo+1.1,hi+1.1)
    return {'sourceWayId':path['id'],'planLengthM':length,'staticBeltCount':2,'flankingFlights':2,'treadCountPerFlightEstimate':count,
       'heightDifferenceEstimatedM':hi-lo,'animationImplemented':False,'actualEscalatorSlopeAndTreadCount':'pending'}


def build(b,lm,spec,scale=.6):
    if not math.isfinite(scale) or scale<=0:raise ValueError('Positive finite scale required')
    city,g,offset=_context(lm,spec);old=b.frame;m=_Mesh(b,scale,offset,float(lm.get('y',0)))
    try:
        b.frame=(float(lm['x']),float(lm['z']),0)
        for patch in spec['terrainPatches']:
            if patch['part']=='ground-estimate' and not spec['renderTerrain']:continue
            m.face('land' if patch['part']=='ground-estimate' else 'pavement',patch['verticesMetresENU'])
        approach=_static_approach(m,spec)
    finally:b.frame=old
    if m.triangles>spec['budget']['maxTriangles'] or len(m.materials)>spec['budget']['maxMaterials']:raise ValueError('Site budget exceeded')
    return {'id':'leifeng-site','triangleCountBeforeExport':m.triangles,'faceCountBeforeExport':m.faces,'materials':sorted(m.materials),
      'candidateWaterPlanes':0,'lightCount':0,'baseBuildingIdsToExclude':[],'staticApproach':approach,'towerPlacement':tower_placement(lm,spec,scale),
      'sourcePathCount':len(spec['sourcePaths']),'sourceEntranceGapM':spec['sourceEntranceGap']['distanceToMappedTowerM'],'groundFootprints':[],
      'terrainStatus':'estimated GLO30-v3 park/shore-clipped original triangles, no source-resolution improvement','collisionAndSafeArrivalAccepted':False,
      'pending':spec['blockers'],'accuracyClaim':'finite estimated hill/site/externalapproach candidate; full plaza/gate/door/interior and actual arrival remain blocked'}
