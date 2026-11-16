"""Source-primitive bridge integration candidate; no Blender or shared writes.

Road asphalt/deck/underside ownership is explicitly delegated to the source-road
renderer. Preserve all identifiable original trusses/arches/pylons/cables/piers,
rails/railway bed, guardrails and materials. Fuxing gets the reviewed rigid axis
correction, never material-based deletion of a merged GLB.
"""
from pathlib import Path
import json,hashlib,importlib.util,math
ROOT=Path(__file__).resolve().parents[2]

def _load(spec):
 if spec.get('id')!='qiantang-bridges-integration-v2' or spec.get('cityId')!='hangzhou':raise ValueError('Explicit Hangzhou bridge v2 spec required')
 for name,digest in spec['frozenInputs'].items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed frozen bridge input: '+name)
 source=ROOT/spec['originalModule'];loader=importlib.util.spec_from_file_location('_qiantang_v2_private_original',source);m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m)
 return m,json.loads((ROOT/spec['originalSpec']).read_text())

def build(b,lm,spec,scale=.6):
 m,full=_load(spec)
 if abs(scale-.6)>1e-12:raise ValueError('Original bridge physical dimensions require single canonical .60 scaling')
 if any(abs(float(lm[k])-spec['placementGame'][k])>1e-9 for k in ['x','z','y']):raise ValueError('Fixed source-bound integration placement required')
 city,g,origin,xy=m._context(full);active={'bridge':None};removed=[];original_deck=m._deck
 def road_owner(mesh,pt,a,end,width,height,thick,top=False,mat='concrete'):
  bridge=active['bridge'];israil=bridge['id']=='qiantang-bridge' and top
  if israil:return original_deck(mesh,pt,a,end,width,height,thick,top,mat)
  pts=[pt(s,t,height) for s,t in [(a,-width/2),(end,-width/2),(end,width/2),(a,width/2)]]
  removed.append({'bridgeId':bridge['id'],'stationRangeM':[a,end],'widthM':width,'nominalHeightRelativeM':height,'thicknessM':thick,'topRequested':top,'reason':'source-road renderer sole owner; whole semantic road-deck primitive omitted before mesh generation','sourceLocalTop':pts})
 m._deck=road_owner;oldframe=b.frame;parts=[];allfaces=0;triangles=0
 try:
  b.frame=(lm['x'],lm['z'],0)
  for bridge in full['bridges']:
   active['bridge']=bridge;fix=spec['bridges'][bridge['id']];oldcenter=xy(bridge['centerWGS84']);newcenter=xy(fix['centerWGS84']);angle=fix['axisRadiansEastCCW']-bridge['axisRadiansEastCCW'];c,s=math.cos(angle),math.sin(angle)
   class RigidMesh(m._Mesh):
    def face(self,material,points):
     transformed=[]
     for px,pz,py in points:
      u,v=px-oldcenter[0],pz-oldcenter[1];transformed.append((newcenter[0]+u*c-v*s,newcenter[1]+u*s+v*c,py))
     points=[((x+self.offset[0])*self.scale,(z+self.offset[1])*self.scale,y*self.scale+self.water) for x,z,y in transformed]
     a0,a1,a2=points[:3];v=[a1[i]-a0[i] for i in range(3)];w=[a2[i]-a0[i] for i in range(3)];normal=[v[1]*w[2]-v[2]*w[1],v[2]*w[0]-v[0]*w[2],v[0]*w[1]-v[1]*w[0]];drop=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=drop]
     # Periodic texture phase is retained, while each bridge uses small UVs.
     world=[[p[0]+lm['x'],p[1]+lm['z'],p[2]] for p in points];uvorigin=[newcenter[0]*scale+lm['x'],newcenter[1]*scale+lm['z'],lm['y']];uv=[tuple(p[i]/8-math.floor(uvorigin[i]/8) for i in axes) for p in world]
     self.b.face(material,points,uv);self.faces+=1;self.triangles+=len(points)-2;self.materials.add(material)
   mesh=RigidMesh(b,scale,(0,0),lm['y']);method={'qiantang-bridge':m._qiantang,'fuxing-bridge':m._fuxing,'zhijiang-bridge':m._zhijiang}[bridge['id']];info=method(mesh,bridge,xy);info.update({'id':bridge['id'],'triangles':mesh.triangles,'faces':mesh.faces,'materials':sorted(mesh.materials)});parts.append(info);triangles+=mesh.triangles;allfaces+=mesh.faces
 finally:b.frame=oldframe
 return {'id':spec['id'],'bridges':parts,'triangles':triangles,'faces':allfaces,'removedRoadDeckPrimitives':removed,'roadDeckOwner':'source-road renderer, including road top/underside/sides; explicit full-width support domains in companion contract','railDeckOwner':'this independent object: qiantang railway only','candidateRoadTopPlanes':0,'candidateWaterPlanes':0,'lightCount':0,'nightPolicy':'existing material identities preserved; original bridge-specific luminaire/emissive evidence was pending, no invented new night hardware','estimatedHeightPolicy':'legacy reference-informed rigid core values; independent source-node ramp proposal required simultaneously; no DSM deformation of arches','navigationAccepted':False}

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
 adapter,full=_collision_source(spec);rows=adapter.ground_footprints(lm,full,scale);point=_point_transform(spec,full)
 for r in rows:
  r['id']='v2:'+r['id'];r['polygonGame']=[point(p,r['bridgeId']) for p in r['polygonGame']];r['verticesGameENU']=[point(p,r['bridgeId']) for p in r['verticesGameENU']];r['originalSourceFaceRange']=r.pop('sourceFaceRange');r['blocksRoad']=True;r['status']='retained source primitive bound; actual actor review required'
 return rows

def deck_domains(lm,spec,scale=.6):
 """Full reported deck support domains for the ONE source-road renderer owner.

 The object emits no road deck face. The renderer must fill the reported-width
 support domains, not just disconnected per-carriageway thin strips. Rail is
 explicitly separate and continues to be rendered by this object.
 """
 adapter,full=_collision_source(spec);point=_point_transform(spec,full);result=[]
 for mode in ['road','rail']:
  for r in adapter.walk_surfaces(lm,full,scale,mode=mode):
   r['id']='v2:'+r['id'];r['polygonGame']=[point(p,r['bridgeId']) for p in r['polygonGame']];r['originalSourceFaceRange']=r.pop('sourceFaceRange');r['geometryOwner']='source-road renderer' if mode=='road' else 'qiantang_bridges_v2 railway bed';r['roadAsphaltTopRule']='raw support Y + .1 game' if mode=='road' else None;r['sourceHeightMustMatch']='independent source-height-proposal.json; never silently keep DSM-derived deck while using this structure';r['renderedTopFace']=mode=='rail';result.append(r)
 return result
