"""Three source-bound Qiantang bridge structural candidates; CPU/scene free.

Physical metres enter B exactly once. No road top plane, water, traffic actor,
export or construction-state Xixing/underground Boao geometry is created.
Vertical profiles are explicitly estimated and opt-in; true datum/interchange
profiles remain blocked. A source way and transport mode select stacked levels.
"""
from __future__ import annotations
import math
try:
    from city_config import load_city,project
except ImportError:
    from scripts.city_config import load_city,project


def _context(spec):
    if spec.get('id')!='qiantang-bridges' or spec.get('cityId')!='hangzhou':raise ValueError('Expected Hangzhou bridge collection spec')
    city=load_city('hangzhou');g=city['geography'];a=spec['anchor'];origin=project(a['lon'],a['lat'],city)
    def xy(p):
        q=project(*p,city);return ((q[0]-origin[0])/g['scale'],(q[1]-origin[1])/g['scale'])
    return city,g,origin,xy


def _bridge_frame(bridge,xy):
    x,y=xy(bridge['centerWGS84']);a=bridge['axisRadiansEastCCW'];u=(math.cos(a),math.sin(a));n=(-u[1],u[0])
    def pt(s,t,h):return (x+s*u[0]+t*n[0],y+s*u[1]+t*n[1],h)
    return pt


def _nominal_height(bridge,deck):return bridge['profile'][deck+'WaterRelativeM']


def source_road_profiles(spec,water_height_game,endpoint_heights_game=None,scale=.6,allow_estimated=False,include_outer_continuations=True):
    """Return source-way/node decks plus ≤20m interpolation samples in game units.

    water_height_game and supplied source-node endpoint heights are ALREADY game
    units. Nodes are preserved in source order; samples are not new junctions.
    The optional map uses exact source node strings (roads only). Required opt-in
    protects callers from treating photograph-estimated heights as a survey.
    A projected crossing does not imply connectivity; node3351280499 on rail is
    separate from the source-road surface, and rail is excluded from this API.
    """
    if not allow_estimated:raise ValueError('Measured deck/datum profiles unavailable; explicitly allow_estimated=True for candidate only')
    if not math.isfinite(water_height_game) or not math.isfinite(scale) or scale<=0:raise ValueError('Finite game datum and positive scale required')
    city,g,origin,xy=_context(spec);overrides={str(k):float(v) for k,v in (endpoint_heights_game or {}).items()}
    if not all(math.isfinite(v) for v in overrides.values()):raise ValueError('Invalid supplied source-node height')
    result=[]
    for bridge in spec['bridges']:
        paths=bridge['roads']+(bridge.get('outsideOldBoundsContinuations',[]) if include_outer_continuations else [])
        for path in paths:
            q=path['coordinatesWGS84'];p=[xy(v) for v in q];refs=path['nodeIds'];lengths=[0.0]
            for a,b in zip(p,p[1:]):lengths.append(lengths[-1]+math.dist(a,b))
            nominal=water_height_game+_nominal_height(bridge,path['deck'])*scale;values=[nominal]*len(p)
            # Caller-supplied world endpoints taper by SOURCE arc distance. This
            # is an interpolation proposal, never an observed physical grade.
            changes=[];transition=bridge['profile']['transitionM']
            for i in [0,len(p)-1]:
                if refs[i] in overrides:changes.append((lengths[i],overrides[refs[i]]-nominal))
            for i,s in enumerate(lengths):
                weights=[max(0,1-abs(s-t)/transition) for t,d in changes]
                total=sum(weights)
                if total:values[i]+=sum(w*d for w,(t,d) in zip(weights,changes))/max(1,total)
                if refs[i] in overrides:values[i]=overrides[refs[i]]
            points=[[origin[0]+v[0]*scale,origin[1]+v[1]*scale] for v in p];samples=[]
            for j,(a,b) in enumerate(zip(q,q[1:])):
                count=max(1,math.ceil((lengths[j+1]-lengths[j])/20))
                for k in range(count):
                    f=k/count;lon=a[0]+(b[0]-a[0])*f;lat=a[1]+(b[1]-a[1])*f;en=xy([lon,lat])
                    samples.append({'sourceSegmentIndex':j,'fraction':f,'coordinateWGS84':[lon,lat],
                      'point':[origin[0]+en[0]*scale,origin[1]+en[1]*scale],'height':values[j]+(values[j+1]-values[j])*f})
            samples.append({'sourceSegmentIndex':len(q)-2,'fraction':1.0,'coordinateWGS84':q[-1],'point':points[-1],'height':values[-1]})
            slopes=[abs(b-a)/max(1e-9,math.dist(p1,p2)) for a,b,p1,p2 in zip(values,values[1:],points,points[1:])]
            maximum=max(slopes,default=0);reported=bridge['profile']['maxReportedGradient'];blockers=['absolute bridge/deck/water datum unknown; photo-derived height estimate','complex endpoint/approach/collision and stacked actor selection not accepted']
            if reported is not None and maximum>reported+1e-8:blockers.append('supplied endpoint proposal exceeds reported maximum longitudinal grade')
            result.append({'id':path['id'],'bridgeId':bridge['id'],'mode':'road','deck':path['deck'],'nodeIds':refs,
              'coordinatesWGS84':q,'points':points,'heights':values,'profileSamples':samples,'sourceLengthM':lengths[-1],
              'heightBasis':'estimated reference-informed water-relative height + explicitly supplied source-node world-height interpolation',
              'units':'game metres; scale once','scale':scale,'maxGradient':maximum,'reportedMaxGradient':reported,
              'sourceNodeEndpointOverrides':[n for n in refs if n in overrides],'structuralNominalDeckHeightGame':nominal,
              'endpointOverridesRequireStructureAndNeighborRoadReview':bool(changes),'sourceLayer':path['tags'].get('layer','0'),
              'sourceRoadTags':path['tags'],'status':'candidate-estimated','navigationAccepted':False,
              'actorPermission':'unknown lower-level general-car permission' if path['deck']=='lower' else 'source highway class; runtime/access constraints pending',
              'blockers':blockers})
    return result


def road_height_at(way_id,lon,lat,spec,water_height_game,endpoint_heights_game=None,scale=.6,allow_estimated=False):
    """Select ONE source way; no XY-only choice between overlapping decks."""
    ident=str(way_id);ident=ident if ident.startswith('way/') else 'way/'+ident
    city,g,origin,xy=_context(spec);p=xy([lon,lat]);best=None
    for r in source_road_profiles(spec,water_height_game,endpoint_heights_game,scale,allow_estimated,True):
        if r['id']!=ident:continue
        for i,(a,b) in enumerate(zip(r['coordinatesWGS84'],r['coordinatesWGS84'][1:])):
            a,b=xy(a),xy(b);d=(b[0]-a[0],b[1]-a[1]);n=d[0]**2+d[1]**2;f=max(0,min(1,((p[0]-a[0])*d[0]+(p[1]-a[1])*d[1])/n));q=(a[0]+f*d[0],a[1]+f*d[1]);dist=math.dist(p,q)
            if best is None or dist<best[0]:best=(dist,r['heights'][i]+f*(r['heights'][i+1]-r['heights'][i]))
    return best[1] if best is not None and best[0]<=25 else None


def source_rail_profiles(spec,water_height_game,scale=.6,allow_estimated=False):
    """Appearance-only lower railway; never add these to source_road_profiles."""
    if not allow_estimated:raise ValueError('Rail vertical datum pending; allow_estimated required')
    city,g,origin,xy=_context(spec);rows=[]
    for bridge in spec['bridges']:
        for path in bridge['railways']:
            rows.append({'id':path['id'],'bridgeId':bridge['id'],'mode':'rail','deck':path['deck'],'nodeIds':path['nodeIds'],
             'coordinatesWGS84':path['coordinatesWGS84'],'points':[[origin[0]+xy(p)[0]*scale,origin[1]+xy(p)[1]*scale] for p in path['coordinatesWGS84']],
             'heights':[water_height_game+_nominal_height(bridge,path['deck'])*scale]*len(path['nodeIds']),
             'navigationAccepted':False,'status':'candidate-estimated','scale':scale})
    return rows


class _Mesh:
    def __init__(self,b,scale,offset,water):self.b=b;self.scale=scale;self.offset=offset;self.water=water;self.faces=self.triangles=0;self.materials=set()
    def face(self,mat,p):
        self.b.face(mat,[((x+self.offset[0])*self.scale,(y+self.offset[1])*self.scale,z*self.scale+self.water) for x,y,z in p]);self.faces+=1;self.triangles+=len(p)-2;self.materials.add(mat)
    def tube(self,mat,a,b,r,n=4,cap=True):
        d=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(x*x for x in d))
        if length<1e-8:return
        d=[x/length for x in d];q=(0,0,1) if abs(d[2])<.9 else (1,0,0);u=(d[1]*q[2]-d[2]*q[1],d[2]*q[0]-d[0]*q[2],d[0]*q[1]-d[1]*q[0]);l=math.sqrt(sum(x*x for x in u));u=[x/l for x in u];v=(d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0])
        rows=[[(p[0]+r*(math.cos(i*math.tau/n)*u[0]+math.sin(i*math.tau/n)*v[0]),p[1]+r*(math.cos(i*math.tau/n)*u[1]+math.sin(i*math.tau/n)*v[1]),p[2]+r*(math.cos(i*math.tau/n)*u[2]+math.sin(i*math.tau/n)*v[2])) for i in range(n)] for p in [a,b]]
        for i in range(n):j=(i+1)%n;self.face(mat,[rows[0][i],rows[0][j],rows[1][j],rows[1][i]])
        if cap:self.face(mat,list(reversed(rows[0])));self.face(mat,rows[1])


def _deck(m,pt,a,b,width,height,thick,top=False,mat='concrete'):
    v=[pt(s,t,h) for h in [height-thick,height] for s,t in [(a,-width/2),(b,-width/2),(b,width/2),(a,width/2)]]
    ids=[(0,3,2,1),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)]
    if top:ids.append((4,5,6,7))
    for q in ids:m.face(mat,[v[i] for i in q])


def _rails(m,pt,a,b,w,h):
    for side in [-1,1]:
        count=max(1,math.ceil((b-a)/20))
        m.tube('silver',pt(a,side*w/2,h+1.1),pt(b,side*w/2,h+1.1),.045,4,False)
        m.tube('silver',pt(a,side*w/2,h+.45),pt(b,side*w/2,h+.45),.03,4,False)
        for j in range(count):
            s=a+(b-a)*j/count
            m.tube('silver',pt(s,side*w/2,h),pt(s,side*w/2,h+1.1),.035,4,False)


def _qiantang(m,b,xy):
    pt=_bridge_frame(b,xy);p=b['reported'];a=-p['mainLengthM']/2;upper=b['profile']['upperWaterRelativeM'];lower=b['profile']['lowerWaterRelativeM'];count=p['trussCount'];pitch=p['pierPitchM'];width=b['widthM'];members=b['estimates']['members']['value']
    _deck(m,pt,a,-a,width,upper,b['profile']['upperThicknessM']);_deck(m,pt,a,-a,5.1,lower,.7,True);_rails(m,pt,a,-a,width,upper)
    for j in range(count):
        s=a+j*pitch;t=s+pitch
        for side in [-1,1]:
            transverse=side*p['trussCenterWidthM']/2
            for h in [lower,upper]:m.tube('steel',pt(s,transverse,h),pt(t,transverse,h),members['chordRadiusM'])
            for k in range(8):
                u=s+pitch*k/8;v=s+pitch*(k+1)/8;z0,z1=(lower,upper) if k%2==0 else (upper,lower)
                m.tube('steel',pt(u,transverse,z0),pt(v,transverse,z1),members['diagonalRadiusM'])
                if k%2==0:m.tube('steel',pt(u,transverse,lower),pt(u,transverse,upper),members['verticalRadiusM'])
        for k in range(5):
            u=s+pitch*k/4;m.tube('steel',pt(u,-3.05,lower),pt(u,3.05,lower),.14)
        if j>0:m.tube('concrete',pt(s,0,-1.5),pt(s,0,lower-.7),members['pierRadiusM'],8)
    # One standard-gauge track, appearance only. No train or road junction.
    for t in [-p['railGaugeM']/2,p['railGaugeM']/2]:m.tube('steel',pt(a,t,lower+.13),pt(-a,t,lower+.13),.055)
    return {'trussSpans':count,'riverPiers':15,'railTracks':1,'mainLengthM':p['mainLengthM'],'detailedSleepersAndCatenary':'pending'}


def _fuxing(m,b,xy):
    pt=_bridge_frame(b,xy);upper=b['profile']['upperWaterRelativeM'];lower=b['profile']['lowerWaterRelativeM'];seq=b['reported']['archSequenceCalculationM'];a=-688;station=a+91.5;cuts=[a];spans=[]
    for i,length in enumerate(seq):spans.append((station,station+length,length));cuts.extend([station,station+length]);station+=length+(4.8 if i<len(seq)-1 else 0)
    cuts.append(688)
    def width(s):return 32 if any(a-12<=s<=c+12 and n==190 for a,c,n in spans) else 26.4
    for s,t in zip(sorted(set(cuts)),sorted(set(cuts))[1:]):
        w=width((s+t)/2);_deck(m,pt,s,t,w,upper,1.25);_deck(m,pt,s,t,w,lower,1.15)
    _rails(m,pt,-688,688,26.4,upper);_rails(m,pt,-688,688,26.4,lower)
    members=b['estimates']['members']['value'];rise=b['estimates']['archRiseM']['value']
    for i,(start,end,length) in enumerate(spans):
        large=length==190;h=rise['large' if large else 'small'];n=24 if large else 16;ribhalf=members['largeRibCentersM' if large else 'smallRibCentersM']/2
        def arch(s):f=(s-start)/length;return lower+4*h*f*(1-f)
        halfw,halfh=[v/2-.475 for v in members['largeRibSectionM']]
        chord_offsets=[(-halfw,-halfh),(-halfw,halfh),(halfw,-halfh),(halfw,halfh)] if large else [(0,0)]
        for side in [-1,1]:
            for k in range(n):
                s=start+length*k/n;t=start+length*(k+1)/n
                for dx,dh in chord_offsets:m.tube('carpaint',pt(s,side*ribhalf+dx,arch(s)+dh),pt(t,side*ribhalf+dx,arch(t)+dh),.475 if large else .85,4,False)
                if large and k%2==0:
                    m.tube('carpaint',pt(s,side*ribhalf-halfw,arch(s)-halfh),pt(t,side*ribhalf+halfw,arch(t)+halfh),.15,4,False)
                if k>0:
                    h0=arch(s);m.tube('silver',pt(s,side*ribhalf,lower+1),pt(s,side*ribhalf,h0),.07,4,False)
                    if abs(h0-upper)>1:m.tube('carpaint',pt(s,side*ribhalf,upper-1),pt(s,side*ribhalf,h0),.12 if h0<upper else .065,4,False)
        for k in [n//4,n//2,3*n//4]:
            s=start+length*k/n;m.tube('carpaint',pt(s,-ribhalf,arch(s)),pt(s,ribhalf,arch(s)),.3,4,False)
            if large:
                t=min(end,s+length/n);m.tube('carpaint',pt(s,-ribhalf,arch(s)),pt(t,ribhalf,arch(t)),.16,4,False)
        # Open gap between two pier legs reproduces river-facing silhouette;
        # pier section, footing and chamber dimensions remain estimates.
        for t in [-6,6]:m.tube('concrete',pt(start,t,-1.5),pt(start,t,lower-1.15),2.1,6)
        m.tube('concrete',pt(start,-10,lower-2.1),pt(start,10,lower-2.1),1.7)
    return {'largeArches':2,'smallArches':9,'archCalculationLengthM':sum(seq),'mainLengthM':1376,'currentRailwayTracksDrawn':0}


def _zhijiang(m,b,xy):
    pt=_bridge_frame(b,xy);deck=b['profile']['singleWaterRelativeM'];p=b['reported'];a=-239;w=p['steelBoxTotalWidthIncludingNoseM'];height=p['ellipseMajorSemiAxisM'];semi=p['ellipseMinorSemiAxisM'];radius=p['pylonTransverseSectionM']/2
    _deck(m,pt,a,-a,w,deck,p['steelBoxHeightM']);_rails(m,pt,a,-a,w,deck)
    for station in [-123,123]:
        # One transverse U/elliptical portal at each longitudinal tower station.
        base=deck-(p['steelPylonHeightM']-height)
        rows=[]
        def row(t,z,nt,nz):
            z_fraction=max(0,min(1,(z-base)/p['steelPylonHeightM']))
            half_long=(p['pylonLongitudinalSectionBottomM']+(p['pylonLongitudinalSectionTopM']-p['pylonLongitudinalSectionBottomM'])*z_fraction)/2
            return [pt(station+s*half_long,t+q*radius*nt,z+q*radius*nz) for s,q in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        rows.append(row(semi,base,1,0))
        for i in range(41):
            t=math.pi*i/40;nt=height*math.cos(t);nz=semi*math.sin(t);length=math.hypot(nt,nz)
            rows.append(row(semi*math.cos(t),deck+height*math.sin(t),nt/length,nz/length))
        rows.append(row(-semi,base,-1,0))
        for r1,r2 in zip(rows,rows[1:]):
            for i in range(4):j=(i+1)%4;m.face('civicred',[r1[i],r1[j],r2[j],r2[i]])
        m.face('civicred',list(reversed(rows[0])));m.face('civicred',rows[-1])
        for side in [-1,1]:
            m.tube('concrete',pt(station,side*semi,-1.5),pt(station,side*semi,base),3.1,6)
        for direction in [-1,1]:
            reach=116 if (station==-123 and direction==-1) or (station==123 and direction==1) else 123
            for side in [-1,1]:
                for j in range(1,15):
                    f=j/14;h=height*(.35+.57*f);t=side*semi*math.sqrt(max(0,1-(h/height)**2));s=station+direction*reach*f
                    m.tube('silver',pt(station,t,deck+h),pt(s,side*(w/2-.9),deck+.3),b['estimates']['cableLayout']['value']['radiusM'],3,False)
    return {'archPylons':2,'staticRepresentativeStayCables':112,'mainSpanM':246,'sideSpansM':[116,116],'pylonDatumConventionPending':True}


def build(b,lm,spec,scale=.6):
    if not math.isfinite(scale) or scale<=0:raise ValueError('Positive finite scale required')
    city,g,origin,xy=_context(spec);a=spec['anchor'];lm_projection=project(lm.get('lon',a['lon']),lm.get('lat',a['lat']),city);offset=((origin[0]-lm_projection[0])/g['scale'],(origin[1]-lm_projection[1])/g['scale'])
    before=b.frame;m=_Mesh(b,scale,offset,float(lm.get('y',0)));parts=[]
    try:
        b.frame=(float(lm['x']),float(lm['z']),0)
        for bridge in spec['bridges']:
            begin=m.triangles
            method={'qiantang-bridge':_qiantang,'fuxing-bridge':_fuxing,'zhijiang-bridge':_zhijiang}[bridge['id']]
            info=method(m,bridge,xy);info.update(id=bridge['id'],triangles=m.triangles-begin);parts.append(info)
    finally:b.frame=before
    return {'id':spec['id'],'bridgeCount':len(parts),'bridges':parts,'triangleCountBeforeExport':m.triangles,'faceCountBeforeExport':m.faces,
       'materials':sorted(m.materials),'lightCount':0,'candidateWaterPlanes':0,'candidateRoadTopPlanes':0,'baseBuildingIdsToExclude':[],
       'railModeSeparate':True,'xixingAndBoaoRendered':False,'roadProfileAPI':'source_road_profiles / road_height_at; explicitly estimated opt-in',
       'verticalDatum':'lm.y is supplied game river-display surface, not measured deck/ground/EGM2008 datum',
       'accuracyClaim':'finite reference-informed structural exterior + exact source way/node plan contract; absolute deck/ramps/navigation still blocked'}
