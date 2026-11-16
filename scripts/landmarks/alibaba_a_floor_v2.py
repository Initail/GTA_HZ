"""Alibaba A component floors; preserve frozen original adjacent-body geometry."""
from pathlib import Path
import importlib.util,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2]
def _load(spec):
 if spec.get('id')!='alibaba-a' or spec.get('cityId')!='hangzhou':raise ValueError('Alibaba A source-owned floor specification required')
 for p,h in spec['frozenInputs'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozen source drift '+p)
 ms=importlib.util.spec_from_file_location('_original_ali_a_floor_v2',ROOT/spec['originalModule']);m=importlib.util.module_from_spec(ms);ms.loader.exec_module(m);return m,json.loads((ROOT/spec['originalSpec']).read_text())
def build(b,lm,spec,scale=.6):
 m,source=_load(spec)
 if scale!=.6 or any(abs(lm[k]-spec['placementGame'][k])>1e-9 for k in ['x','z','y']):raise ValueError('Single canonical game-unit placement required')
 Original=m._Mesh
 class ComponentMesh(Original):
  def point(self,p):
   x,z,y=super().point(p);return x,z,y+spec['components'][self.part]['baseYGame']
  def face(self,material,ps):
   if hasattr(self.b,'source_part'):self.b.source_part=self.part
   return super().face(material,ps)
 m._Mesh=ComponentMesh
 report=m.build(b,lm,source,scale);report.update({'floorAdaptation':'rigid source-contact component groups; no whole-campus lift or link warp','floorComponents':{k:v['baseYGame'] for k,v in spec['components'].items()},'contactGroups':spec['contactGroups'],'sourceModuleSha256':spec['frozenInputs'][spec['originalModule']],'noNewDoorway':True,'browserVerified':False});return report

def ground_footprints(lm,spec,scale=.6):
 m,source=_load(spec);return m.ground_footprints(lm,source,scale)
