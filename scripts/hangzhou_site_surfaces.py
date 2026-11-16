"""Pure ENU site triangles shared with city-site-surfaces.ts; no bpy import."""
import math
CONTACT_EPSILON_GAME=1e-10

class SiteSurfaces:
    def __init__(self,data):
        if data['cityId']!='hangzhou' or data['units']!='game east/north/up; scale applied once':raise ValueError('Invalid site surface units')
        self.cells={};self.road_groups={};self.slab_thickness={}
        for group in data.get('roadSurfaces',[]):
            for road_id in group['roadIds']:
                if road_id in self.road_groups:raise ValueError('Duplicate source road surface')
                self.road_groups[road_id]=group['id']
        for group in data.get('solidSlabs',[]):
            thickness=group['thicknessGame']
            if not math.isfinite(thickness) or thickness<=0:raise ValueError('Invalid solid slab thickness')
            self.slab_thickness[group['id']]=thickness
        for kind in ['terrainCuts','walkFloors','terrainPatches','roadSurfaces','solidSlabs']:
            cells={};self.cells[kind]=cells;ids=set();count=0
            for group in data.get(kind,[]):
                if not group['id'] or group['id'] in ids:raise ValueError('Duplicate site surface identity')
                ids.add(group['id'])
                edges=group.get('openEdges')
                if edges is not None and (len(edges)!=len(group['triangles']) or any(len(e)!=3 or any(type(v) is not bool for v in e) for e in edges)):raise ValueError('Invalid site boundary ownership')
                for index,triangle in enumerate(group['triangles']):
                    count+=1
                    if count>200000 or len(triangle)!=3 or any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in triangle):raise ValueError('Invalid site surface geometry')
                    a,b,c=triangle;det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                    if det<=0:raise ValueError('Site surface must face upward')
                    xs=[p[0] for p in triangle];zs=[p[1] for p in triangle]
                    for x in range(math.floor(min(xs)/32),math.floor(max(xs)/32)+1):
                        for z in range(math.floor(min(zs)/32),math.floor(max(zs)/32)+1):cells.setdefault((x,z),[]).append((group['id'],triangle,det,edges[index] if edges is not None else None))
    def at(self,kind,x,z):
        if not math.isfinite(x+z):raise ValueError('Invalid site surface query')
        result=[]
        for identifier,(a,b,c),det,edges in self.cells[kind].get((math.floor(x/32),math.floor(z/32)),[]):
            ps=[a,b,c];distances=[]
            for i,p in enumerate(ps):
                q=ps[(i+1)%3];distances.append(((q[0]-p[0])*(z-p[1])-(q[1]-p[1])*(x-p[0]))/math.hypot(q[0]-p[0],q[1]-p[1]))
            if any(d< -1e-9 for d in distances):continue
            if edges is not None and any(is_open and abs(distances[i])<=1e-9 for i,is_open in enumerate(edges)):continue
            dx,dz=x-a[0],z-a[1];u=(dx*(c[1]-a[1])-dz*(c[0]-a[0]))/det;v=((b[0]-a[0])*dz-(b[1]-a[1])*dx)/det
            height=a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])
            if u<0 or v<0 or u+v>1:
                distance=math.inf
                for i,p in enumerate(ps):
                    q=ps[(i+1)%3];ex,ez=q[0]-p[0],q[1]-p[1]
                    t=max(0,min(1,((x-p[0])*ex+(z-p[1])*ez)/(ex*ex+ez*ez)))
                    d=math.hypot(x-p[0]-ex*t,z-p[1]-ez*t)
                    if d<distance:distance=d;height=p[2]+t*(q[2]-p[2])
                if distance>1e-9:continue
            result.append({'id':identifier,'height':height})
        return result
    def ground_at(self,x,z,uncut):
        if not math.isfinite(uncut):raise ValueError('Invalid uncut ground')
        patches=self.at('terrainPatches',x,z);self.assert_continuous(patches)
        return min([patches[0]['height'] if patches else uncut]+[p['height'] for p in self.at('terrainCuts',x,z)])
    def assert_continuous(self,matches):
        if matches and max(p['height'] for p in matches)-min(p['height'] for p in matches)>.0001:raise ValueError('Overlapping source TIN heights disagree')
    def road_at(self,road_id,x,z):
        group=self.road_groups.get(road_id)
        if group is None:return None
        matches=[p for p in self.at('roadSurfaces',x,z) if p['id']==group];self.assert_continuous(matches)
        return matches[0]['height'] if matches else None
    def blocked(self,x,z,feet,body_height=1.6):
        if not math.isfinite(feet+body_height) or body_height<=0:raise ValueError('Invalid actor height')
        return any(feet<p['height']-CONTACT_EPSILON_GAME and feet+body_height>p['height']-self.slab_thickness[p['id']]+CONTACT_EPSILON_GAME for p in self.at('solidSlabs',x,z))
    def walk_at(self,x,z,ground,previous=None):
        previous=ground if previous is None else previous
        height=previous['height'] if isinstance(previous,dict) else previous;identifier=previous.get('id') if isinstance(previous,dict) else None
        if not math.isfinite(ground+height):raise ValueError('Invalid walking surface height')
        available=[p for p in self.at('walkFloors',x,z) if p['height']>=ground-.001]
        same=[p for p in available if p['id']==identifier] if identifier else []
        floors=same if same else [p for p in available if abs(p['height']-height)<.48]
        floors.sort(key=lambda p:(abs(p['height']-height),-p['height'],p['id']))
        return floors[0] if floors else {'id':None,'height':ground}
