"""Isolated Blender export of intermediate Hangzhou base geometry.

Exports original runtime mesh conventions and shared authored materials.
No coastline/ocean assumptions, no landmark proxies and no public writes.
Road decks, terrain draping, near facades and all placement layers remain gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def up(triangle):
 a,b,c=triangle
 return triangle if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])>=0 else list(reversed(triangle))

def main(argv):
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
 a=p.parse_args(argv);source=(ROOT/a.input).resolve();output=(ROOT/a.output).resolve()
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh artifacts output required')
 manifest=json.loads((source/'manifest.json').read_text())
 if manifest['cityId']!='hangzhou':raise ValueError('Hangzhou source required')
 for name,sha in manifest['sha256'].items():
  if digest(source/name)!=sha:raise ValueError('Changed prepared source '+name)
 began=time.monotonic()
 import city_mesh as cm
 cm.O=output;output.mkdir(parents=True,exist_ok=True)
 def load(name):return json.loads((source/(name+'.json')).read_text())
 assets=[];ground=cm.B()
 for material,height in [('land',0),('park',.015),('water',.035)]:
  for triangle in load(material):ground.face(material,[(x,z,height) for x,z in up(triangle)])
 assets.append(cm.export('terrain',ground.finish('terrain')));del ground
 chunks={}
 for material,height in [('asphalt',.10),('pavement',.06)]:
  for triangle in load(material):
   key=tuple(math.floor(sum(p[axis] for p in triangle)/3/640) for axis in [0,1])
   builder=chunks.setdefault(key,cm.B())
   builder.face(material,[(x,z,height) for x,z in up(triangle)])
 roads=[]
 for key,builder in chunks.items():roads.extend(builder.finish(f'roads_{key[0]}_{key[1]}'))
 assets.append(cm.export('roads',roads));del chunks,roads
 chunks={}
 for building in load('buildings'):
  outer=building['rings'][0];key=tuple(math.floor(sum(p[axis] for p in outer)/len(outer)/640) for axis in [0,1])
  builder=chunks.setdefault(key,cm.B());height=building['height']
  for index,ring in enumerate(building['rings']):
   if ring[0]==ring[-1]:ring=ring[:-1]
   signed=sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(ring,ring[1:]+ring[:1]))
   if (index==0 and signed<0) or (index>0 and signed>0):ring=list(reversed(ring))
   for (x,z),(xx,zz) in zip(ring,ring[1:]+ring[:1]):
    width=math.hypot(xx-x,zz-z)
    builder.face(building['style'],[(x,z,0),(xx,zz,0),(xx,zz,height),(x,z,height)],[(0,0),(width/24,0),(width/24,height/24),(0,height/24)])
  for triangle in building['roofTriangles']:builder.face('roof',[(x,z,height) for x,z in up(triangle)])
 buildings=[]
 for key,builder in chunks.items():buildings.extend(builder.finish(f'block_{key[0]}_{key[1]}'))
 assets.append(cm.export('buildings',buildings));del chunks,buildings
 # Actual independently authored models only, with real source/hash contracts.
 exclusions=json.loads((source/'building-exclusions.json').read_text());details=[]
 for landmark in exclusions['landmarks']:
  path=ROOT/landmark['artifact']
  if digest(path)!=landmark['artifactSha256']:raise ValueError('Changed landmark artifact')
  before=set(cm.bpy.context.scene.objects);cm.bpy.ops.import_scene.gltf(filepath=str(path))
  details.extend(o for o in cm.bpy.context.scene.objects if o not in before and o.type=='MESH')
 if details:assets.append(cm.export('landmark-detail',details))
 result={'schemaVersion':1,'cityId':'hangzhou','source':str(source.relative_to(ROOT)),
  'sourceManifestSha256':digest(source/'manifest.json'),'sourceSnapshotSha256':manifest['sourceSha256'],
  'assets':[{**r,'sha256':digest(output/r['file'])} for r in assets],
  'excludedBaseBuildingIds':exclusions['baseBuildingIds'],'buildElapsedSeconds':time.monotonic()-began,
  'status':'intermediate-flat-base-export-not-runtime-accepted',
  'pending':manifest['pending'],'note':'No source object is presented as a completed landmark; no public asset changed.'}
 (output/'asset-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
