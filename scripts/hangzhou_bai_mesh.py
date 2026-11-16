"""Local Bai route reprojection of preserved source landmark mesh generators.

Pure Python: never imports city_mesh/bpy. Old generators remain byte-identical.
The adapter captures faces and rail solids before applying one shared datum.
"""
import bisect, math
from landmarks import west_lake_causeways as causeway, broken_bridge as broken

class Collector:
    def __init__(self): self.frame=(0,0,0); self.faces=[]; self.part=''; self.rail=None; self.serial=0
    def face(self, material, points, uv=None):
        x,z,a=self.frame; c,s=math.cos(a),math.sin(a)
        self.faces.append({'material':material,'part':self.part,'rail':self.rail,
            'points':[(p[0]*c-p[1]*s+x,p[0]*s+p[1]*c+z,p[2]) for p in points]})

def capture(module, spec, lm):
    collector=Collector(); original=module._Mesh
    class TaggedMesh(original):
        def face(self, material, points):
            collector.part=getattr(self,'part','broken-bridge')
            return super().face(material,points)
        def beam(self,*args,**kwargs):
            prev=collector.rail
            if module is broken or getattr(self,'part','').startswith('bridge-'):
                collector.serial+=1;collector.rail=f'{getattr(self,"part","broken-bridge")}:rail:{collector.serial}'
            try:return super().beam(*args,**kwargs)
            finally:collector.rail=prev
        def box(self,*args,**kwargs):
            prev=collector.rail;collector.serial+=1;collector.rail=f'broken-bridge:rail:{collector.serial}'
            try:return super().box(*args,**kwargs)
            finally:collector.rail=prev
    module._Mesh=TaggedMesh
    try: report=module.build(collector,lm,spec,.6)
    finally: module._Mesh=original
    return collector.faces,report

class Datum:
    def __init__(self, data):
        self.stations=data['stations'];self.distances=[p[0] for p in self.stations];self.segments=[];d=0
        for path in data['paths']:
            for a,b in zip(path['points'],path['points'][1:]):
                length=math.dist(a,b);self.segments.append((a,b,length,d));d+=length
    def __call__(self,x,z):
        best=(math.inf,0)
        for a,b,length,start in self.segments:
            dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(length*length)))
            distance=math.hypot(x-a[0]-t*dx,z-a[1]-t*dz)
            if distance<best[0]:best=(distance,start+t*length)
        s=best[1];i=max(0,min(len(self.stations)-2,bisect.bisect_right(self.distances,s)-1))
        a,b=self.stations[i:i+2];t=(s-a[0])/(b[0]-a[0]);return a[3]+(b[3]-a[3])*t

def triangulate(points):
    # All faces produced by the preserved B modules are convex triangles/quads.
    for i in range(1,len(points)-1):yield [points[0],points[i],points[i+1]]

def subdivide(triangle, datum, tolerance=.01, depth=0):
    edges=[math.dist(triangle[i][:2],triangle[(i+1)%3][:2]) for i in range(3)]
    values=[datum(*p[:2]) for p in triangle]
    residual=0
    for i,length in enumerate(edges):
        a,b=triangle[i],triangle[(i+1)%3];n=max(2,math.ceil(length/3))
        for j in range(1,n):
            t=j/n;x,z=[a[k]+(b[k]-a[k])*t for k in range(2)]
            residual=max(residual,abs(datum(x,z)-(values[i]+(values[(i+1)%3]-values[i])*t)))
    center=[sum(p[k] for p in triangle)/3 for k in range(2)]
    residual=max(residual,abs(datum(*center)-sum(values)/3))
    if residual<=tolerance or max(edges)<.05:yield triangle;return
    if depth>=20:raise ValueError('Bai datum subdivision did not converge')
    i=edges.index(max(edges));a,b,c=triangle[i],triangle[(i+1)%3],triangle[(i+2)%3]
    mid=tuple((u+v)/2 for u,v in zip(a,b))
    yield from subdivide([a,mid,c],datum,tolerance,depth+1)
    yield from subdivide([mid,b,c],datum,tolerance,depth+1)

def make_faces(data, specs, anchors):
    datum=Datum(data); all_faces=[]; reports={}
    bai_parts={f'{"bridge" if p.get("bridge") else "path"}-{p["wayId"]}' for p in specs['causeway']['paths'] if p['causeway']=='bai'}
    bai_parts.update('bank-'+i.replace('/','-') for i in data['bankSourceIds'])
    for name,module in [('causeway',causeway),('broken',broken)]:
        faces, reports[name]=capture(module,specs[name],anchors[name])
        for f in faces:
            selected=name=='broken' or f['part'] in bai_parts
            for t in triangulate(f['points']):
                # Resample only the affected surface; preserve other causeways.
                for tri in subdivide(t,datum) if selected else [t]:
                    lifted=[(x,z,y+datum(x,z)) for x,z,y in tri] if selected else tri
                    all_faces.append({**f,'points':lifted,'changed':selected,'object':name})
    # A source node connects two finite ribbons. Their differently oriented
    # end cross-sections leave triangular notches, and separately exported
    # float32 endpoints can leave a microscopic water gap. Author the actual
    # paving joint, bounded by the two widths and 5 cm of longitudinal overlap.
    def hull(points):
        ps=sorted(set(points));cross=lambda a,b,c:(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        def half(seq):
            out=[]
            for p in seq:
                while len(out)>1 and cross(out[-2],out[-1],p)<=0:out.pop()
                out.append(p)
            return out
        return half(ps)[:-1]+half(reversed(ps))[:-1]
    by_id={p['sourceId']:p for p in specs['causeway']['paths']}
    def deck_offset(path,x,z):
        a,b=path['points'][0],path['points'][-1];length=math.dist(a,b)
        t=max(0,min(1,((x-a[0])*(b[0]-a[0])+(z-a[1])*(b[1]-a[1]))/(length*length)))
        if path['sourceId']=='way/28538289':return broken.deck_height_metres((t-.5)*specs['broken']['bridgeLengthM'],specs['broken'])*.6
        spec=by_id[path['sourceId']]
        return causeway.bridge_height_metres(t*spec['sourceLengthM'],spec)*.6 if spec['bridge'] else 0
    for before,after in zip(data['paths'],data['paths'][1:]):
        center=before['points'][-1];corners=[]
        for path,endpoint,neighbor in [(before,-1,-2),(after,0,1)]:
            p,q=path['points'][endpoint],path['points'][neighbor];length=math.dist(p,q);dx,dz=(q[0]-p[0])/length,(q[1]-p[1])/length
            for along in [-.05,.05]:
                for side in [-1,1]:corners.append((p[0]+dx*along-dz*path['widthGame']/2*side,p[1]+dz*along+dx*path['widthGame']/2*side))
        ring=hull(corners);points=[(x,z,datum(x,z)+max(deck_offset(before,x,z),deck_offset(after,x,z))) for x,z in ring]
        for t in triangulate(points):all_faces.append({'material':'asphalt','part':'source-node-joint-'+str(before['sourceNodeIds'][-1]),'rail':None,'points':t,'changed':True,'object':'causeway'})
    return all_faces,reports
