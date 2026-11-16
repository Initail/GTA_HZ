"""Alibaba C independent body floors and source-owned overhead link adjustment."""
from pathlib import Path
import importlib.util,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2]
def _load(spec):
 if spec.get('id')!='alibaba-c' or spec.get('cityId')!='hangzhou':raise ValueError('Alibaba C source-owned floor specification required')
 for p,h in spec['frozenInputs'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozen source drift '+p)
 ms=importlib.util.spec_from_file_location('_original_ali_c_floor_v2',ROOT/spec['originalModule']);m=importlib.util.module_from_spec(ms);ms.loader.exec_module(m);return m,json.loads((ROOT/spec['originalSpec']).read_text())
def build(b,lm,spec,scale=.6):
 m,source=_load(spec)
 if scale!=.6 or any(abs(lm[k]-spec['placementGame'][k])>1e-9 for k in ['x','z','y']):raise ValueError('Single canonical game-unit placement required')
 ctx=m._context(lm,source);links={'exchange-'+a+'-'+c:(a,c,p,q) for a,c,p,q,r in m.bridge_segments(ctx,source)};floors={k:v['baseYGame'] for k,v in spec['components'].items()};Original=m._Mesh
 class ComponentMesh(Original):
  def point(self,p):
   x,z,y=super().point(p);part=self.part;label=part.removesuffix('-facade-and-roof')
   if part in links:
    a,c,pa,pb=links[part];dx,dz=pb[0]-pa[0],pb[1]-pa[1];t=max(0,min(1,((p[0]-pa[0])*dx+(p[1]-pa[1])*dz)/(dx*dx+dz*dz)));delta=floors[a]*(1-t)+floors[c]*t
   elif part=='visitor-estimated-arrival-accent':delta=floors['访客中心']
   else:delta=floors[label]
   return x,z,y+delta
  def face(self,material,ps):
   if hasattr(self.b,'source_part'):self.b.source_part=self.part
   return super().face(material,ps)
 m._Mesh=ComponentMesh;report=m.build(b,lm,source,scale);report.update({'floorAdaptation':'independent rigid office/visitor bases; original exchange decks linearly match own endpoint floors, unchanged width/thickness; Media Roof isolated rigid datum','floorComponents':floors,'exchangeEndpointRule':'original source strip longitudinal projection t; add(1-t)*leftBase+t*rightBase to every vertex, preserve slab thickness and rail height','sourceModuleSha256':spec['frozenInputs'][spec['originalModule']],'noNewDoorway':True,'browserVerified':False});return report

def ground_footprints(lm,spec,scale=.6):
 m,source=_load(spec);return m.ground_footprints(lm,source,scale)
