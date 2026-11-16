"""Source-primitive bridge integration candidate; no Blender or shared writes.

Road asphalt/deck/underside ownership is explicitly delegated to the source-road
renderer. Preserve all identifiable original trusses/arches/pylons/cables/piers,
rails/railway bed, guardrails and materials. Fuxing gets the reviewed rigid axis
correction, never material-based deletion of a merged GLB.
"""
from pathlib import Path
import json,hashlib,importlib.util,math,copy,sys
ROOT=Path(__file__).resolve().parents[2]

def _load(spec):
 if spec.get('id')!='qiantang-bridges-integration-v2' or spec.get('cityId')!='hangzhou':raise ValueError('Explicit Hangzhou bridge v2 spec required')
 for name,digest in spec['frozenInputs'].items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed frozen bridge input: '+name)
 source=ROOT/spec['originalModule'];loader=importlib.util.spec_from_file_location('_qiantang_v2_private_original',source);m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m)
 return m,json.loads((ROOT/spec['originalSpec']).read_text())

def build(b,lm,spec,scale=.6,capture_collision=False):
 m,full=_load(spec);full=copy.deepcopy(full)
 for bridge in full['bridges']:bridge['profile'].update(spec.get('heightOverridesPhysicalM',{}).get(bridge['id'],{}))
 adapter,_=_collision_source(spec) if capture_collision else (None,None)
 capturedSolids=[]
 if abs(scale-.6)>1e-12:raise ValueError('Original bridge physical dimensions require single canonical .60 scaling')
 if any(abs(float(lm[k])-spec['placementGame'][k])>1e-9 for k in ['x','z','y']):raise ValueError('Fixed source-bound integration placement required')
 city,g,origin,xy=m._context(full);active={'bridge':None};removed=[];railings=[];original_deck=m._deck;original_rails=m._rails
 def road_owner(mesh,pt,a,end,width,height,thick,top=False,mat='concrete'):
  bridge=active['bridge'];israil=bridge['id']=='qiantang-bridge' and top
  if israil:return original_deck(mesh,pt,a,end,width,height,thick,top,mat)
  pts=[pt(s,t,height) for s,t in [(a,-width/2),(end,-width/2),(end,width/2),(a,width/2)]]
  removed.append({'bridgeId':bridge['id'],'stationRangeM':[a,end],'widthM':width,'nominalHeightRelativeM':height,'thicknessM':thick,'topRequested':top,'reason':'source-road renderer sole owner; whole semantic road-deck primitive omitted before mesh generation','sourceLocalTop':pts})
 def edge_rails(mesh,pt,a,end,width,height):
  if active['bridge']['id']!='fuxing-bridge':return original_rails(mesh,pt,a,end,width,height)
  intervals=sorted((d['stationRangeM'][0],d['stationRangeM'][1],d['widthM']) for d in removed if d['bridgeId']=='fuxing-bridge' and abs(d['nominalHeightRelativeM']-height)<1e-9)
  merged=[]
  for start,finish,w in intervals:
   if merged and abs(merged[-1][1]-start)<1e-9 and merged[-1][2]==w:merged[-1]=(merged[-1][0],finish,w)
   else:merged.append((start,finish,w))
  intervals=merged
  before=mesh.faces;pieces=[]
  def tube(start,finish,r,kind):
   mesh._captured=[];mesh._kindOverride=kind;mesh.tube('silver',start,finish,r,4,False);faces=mesh._captured;mesh._captured=None;mesh._kindOverride=None
   if not faces:return
   vertices=[f[0] for f in faces[:4]]+[f[3] for f in faces[:4]];pieces.append({'kind':kind,'verticesGameENU':vertices})
  for side in [-1,1]:
   posts=set()
   for i,(start,finish,w) in enumerate(intervals):
    lateral=side*w/2
    for lift,r in [(1.1,.045),(.45,.03)]:
     tube(pt(start,lateral,height+lift),pt(finish,lateral,height+lift),r,'guardrail-bar')
     if i and abs(intervals[i-1][2]-w)>1e-9:tube(pt(start,side*intervals[i-1][2]/2,height+lift),pt(start,lateral,height+lift),r,'guardrail-bar')
    count=max(1,math.ceil((finish-start)/20))
    for j in range(count+1):posts.add((start+(finish-start)*j/count,lateral))
   for station,lateral in sorted(posts):tube(pt(station,lateral,height),pt(station,lateral,height+1.1),.035,'guardrail-post')
  railings.append({'bridgeId':'fuxing-bridge','nominalHeightRelativeM':height,'faceStartInBridge':before,'faceEndInBridge':mesh.faces,'sourceReportedWidthsM':[26.4,32],'intervalsM':intervals,'pieces':pieces,'reason':'original deck widths varied but old full-length railings were fixed26.4m, crossing widened deck interior; follow actual source-deck boundary without closing road ends'})
 m._rails=edge_rails
 m._deck=road_owner;oldframe=b.frame;parts=[];allfaces=0;triangles=0
 try:
  b.frame=(lm['x'],lm['z'],0)
  for bridge in full['bridges']:
   active['bridge']=bridge;fix=spec['bridges'][bridge['id']];oldcenter=xy(bridge['centerWGS84']);newcenter=xy(fix['centerWGS84']);angle=fix['axisRadiansEastCCW']-bridge['axisRadiansEastCCW'];c,s=math.cos(angle),math.sin(angle)
   class RigidMesh(m._Mesh):
    def tube(self,mat,a,end,r,n=4,cap=True):
     if not capture_collision:return super().tube(mat,a,end,r,n,cap)
     before=self.faces;self._tubeFaces=[];owner=sys._getframe(1).f_code.co_name;super().tube(mat,a,end,r,n,cap);faces=self._tubeFaces;self._tubeFaces=None
     if not faces:return
     ring1=[f[0] for f in faces[:n]];ring2=[f[3] for f in faces[:n]];c1=[sum(v[k] for v in ring1)/n for k in range(3)];c2=[sum(v[k] for v in ring2)/n for k in range(3)];horizontal=math.hypot(c2[0]-c1[0],c2[1]-c1[1]);rise=abs(c2[2]-c1[2]);parts=max(1,math.ceil(max(horizontal/4,rise/1.2))) if horizontal>1e-7 and rise>1e-7 else 1;kind=getattr(self,'_kindOverride',None) or adapter._kind(owner,mat,a,end,bridge)
     for j in range(parts):
      vertices=[[(1-f)*u[k]+f*v[k] for k in range(3)] for f in [j/parts,(j+1)/parts] for u,v in zip(ring1,ring2)];ident=f"v2:{bridge['id']}:member:{len(capturedSolids)}";record=adapter._volume(vertices,ident,bridge['id'],kind,mat,(before,self.faces),[j,parts]);record['sourceFaceRangeInBridge']=record.pop('sourceFaceRange');record['originalSourceFaceRange']=None;record['blocksRoad']=True;capturedSolids.append(record)
    def face(self,material,points):
     transformed=[]
     for px,pz,py in points:
      u,v=px-oldcenter[0],pz-oldcenter[1];transformed.append((newcenter[0]+u*c-v*s,newcenter[1]+u*s+v*c,py))
     points=[((x+self.offset[0])*self.scale,(z+self.offset[1])*self.scale,y*self.scale+self.water) for x,z,y in transformed]
     a0,a1,a2=points[:3];v=[a1[i]-a0[i] for i in range(3)];w=[a2[i]-a0[i] for i in range(3)];normal=[v[1]*w[2]-v[2]*w[1],v[2]*w[0]-v[0]*w[2],v[0]*w[1]-v[1]*w[0]];drop=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=drop]
     # Periodic texture phase is retained, while each bridge uses small UVs.
     world=[[p[0]+lm['x'],p[1]+lm['z'],p[2]] for p in points];uvorigin=[newcenter[0]*scale+lm['x'],newcenter[1]*scale+lm['z'],lm['y']];uv=[tuple(p[i]/8-math.floor(uvorigin[i]/8) for i in axes) for p in world]
     if getattr(self,'_captured',None) is not None:self._captured.append(world)
     if getattr(self,'_tubeFaces',None) is not None:self._tubeFaces.append(world)
     caller=sys._getframe(1)
     if capture_collision and caller.f_code.co_name=='_zhijiang' and material=='civicred' and caller.f_locals.get('i')==0:
      raw=caller.f_locals['r1']+caller.f_locals['r2'];vv=[]
      for px,pz,py in raw:
       u,v=px-oldcenter[0],pz-oldcenter[1];xx,zz=newcenter[0]+u*c-v*s,newcenter[1]+u*s+v*c;vv.append([lm['x']+xx*scale,lm['z']+zz*scale,py*scale+lm['y']])
      record=adapter._volume(vv,f"v2:{bridge['id']}:portal:{len(capturedSolids)}",bridge['id'],'pylon-section',material,(self.faces,self.faces+4));record['sourceFaceRangeInBridge']=record.pop('sourceFaceRange');record['originalSourceFaceRange']=None;record['blocksRoad']=True;capturedSolids.append(record)
     self.b.face(material,points,uv);self.faces+=1;self.triangles+=len(points)-2;self.materials.add(material)
   mesh=RigidMesh(b,scale,(0,0),lm['y']);method={'qiantang-bridge':m._qiantang,'fuxing-bridge':m._fuxing,'zhijiang-bridge':m._zhijiang}[bridge['id']];info=method(mesh,bridge,xy);info.update({'id':bridge['id'],'triangles':mesh.triangles,'faces':mesh.faces,'materials':sorted(mesh.materials)});parts.append(info);triangles+=mesh.triangles;allfaces+=mesh.faces
 finally:b.frame=oldframe
 return {'id':spec['id'],'bridges':parts,'triangles':triangles,'faces':allfaces,'removedRoadDeckPrimitives':removed,'updatedRailings':railings,'capturedCollisionPrimitives':capturedSolids,'roadDeckOwner':'source-road renderer, including road top/underside/sides; explicit full-width support domains in companion contract','railDeckOwner':'this independent object: qiantang railway only','candidateRoadTopPlanes':0,'candidateWaterPlanes':0,'lightCount':0,'nightPolicy':'existing material identities preserved; original bridge-specific luminaire/emissive evidence was pending, no invented new night hardware','estimatedHeightPolicy':'legacy reference-informed rigid core values; independent source-node ramp proposal required simultaneously; no DSM deformation of arches','navigationAccepted':False}

def _collision_source(spec):
 _load(spec);path=ROOT/'scripts/landmarks/qiantang_bridge_collision.py';loader=importlib.util.spec_from_file_location('_qiantang_v2_private_collision',path);m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m);return m,json.loads((ROOT/spec['originalSpec']).read_text())

def _point_transform(spec,full):
 m,_=_load(spec);city=m.load_city('hangzhou');old=next(b for b in full['bridges'] if b['id']=='fuxing-bridge');new=spec['bridges']['fuxing-bridge'];a=m.project(*old['centerWGS84'],city);b=m.project(*new['centerWGS84'],city);angle=new['axisRadiansEastCCW']-old['axisRadiansEastCCW'];c,s=math.cos(angle),math.sin(angle)
 def point(p,bridge_id):
  if bridge_id!='fuxing-bridge':return list(p)
  x,z=p[0]-a[0],p[1]-a[1];return [b[0]+x*c-z*s,b[1]+x*s+z*c]+list(p[2:])
 return point

def ground_footprints(lm,spec,scale=.6):
 """Original retained member envelopes only; road decks have separate owner."""
 class Sink:
  frame=(0,0,0)
  def face(self,*args):pass
 return build(Sink(),lm,spec,scale,capture_collision=True)['capturedCollisionPrimitives']

def deck_domains(lm,spec,scale=.6):
 """Full reported deck support domains for the ONE source-road renderer owner.

 The object emits no road deck face. The renderer must fill the reported-width
 support domains, not just disconnected per-carriageway thin strips. Rail is
 explicitly separate and continues to be rendered by this object.
 """
 adapter,full=_collision_source(spec);point=_point_transform(spec,full);result=[]
 for mode in ['road','rail']:
  for r in adapter.walk_surfaces(lm,full,scale,mode=mode):
   r['id']='v2:'+r['id'];old=next(b for b in full['bridges'] if b['id']==r['bridgeId']);key=r['deck']+'WaterRelativeM';delta=(spec.get('heightOverridesPhysicalM',{}).get(r['bridgeId'],{}).get(key,old['profile'][key])-old['profile'][key])*scale;r['heightGame']+=delta;r['undersideYGame']+=delta;r['polygonGame']=[point(p,r['bridgeId']) for p in r['polygonGame']];r['originalSourceFaceRange']=r.pop('sourceFaceRange');r['geometryOwner']='source-road renderer' if mode=='road' else 'qiantang_bridges_v2 railway bed';r['roadAsphaltTopRule']='raw support Y + .1 game' if mode=='road' else None;r['sourceHeightMustMatch']='independent source-height-proposal.json; never silently keep DSM-derived deck while using this structure';r['renderedTopFace']=mode=='rail';result.append(r)
 return result
