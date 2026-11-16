"""Read-only local placement audit. Proximity is not a claimed mesh collision."""
from pathlib import Path
import json,hashlib,sys
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1]
output=Path(sys.argv[1]);assert not output.exists()
addition=ROOT/'artifacts/cities/hangzhou/lingyin-entry-v1/entry-ground-v1/path-surface-v1/site-surfaces-candidate.json'
sources=[]
def read(p):
 b=p.read_bytes();sources.append({'file':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return json.loads(b)
surface=read(addition);area=unary_union([Polygon([[v[0],v[1]] for v in t]) for f in surface['walkFloors'] for t in f['triangles']]);lo=area.bounds
def local(x,z,r=15):return lo[0]-r<=x<=lo[2]+r and lo[1]-r<=z<=lo[3]+r
def selected(rows,kind):
 result=[]
 for i,row in enumerate(rows):
  x,z=row[:2]
  if not local(x,z):continue
  d=Point(x,z).distance(area)
  if d<=15:result.append({'index':i,'placement':row,'distanceToPavingGame':d,'kind':kind,'rootWithinPaving':area.covers(Point(x,z))})
 return result
v15=ROOT/'artifacts/cities/hangzhou/city-leisure-v15/public/cities/hangzhou';fallback=ROOT/'artifacts/cities/hangzhou/demo-v10/dist/cities/hangzhou'
canopy=read(v15/'landscape/canopy-trees.json');base=read(fallback/'landscape/planting.json')
life=read(fallback/'life-sites.json');street=read(fallback/'street/manifest.json');config=read(ROOT/'config/cities/hangzhou.json')
props=[]
for s in life['sites']:
 if not local(s['x'],s['z']):continue
 import math
 corners=[]
 for u,v in [(-6.1,-2.4),(6.1,-2.4),(6.1,3.3),(-6.1,3.3)]:
  c=math.cos(s['heading']);t=math.sin(s['heading']);corners.append([s['x']+u*c+v*t,s['z']-u*t+v*c])
 poly=Polygon(corners);props.append({'id':s['id'],'distanceGame':poly.distance(area),'pavingIntersects':poly.intersects(area)})
benches=[s for s in street['placements'] if local(s['x'],s['z']) and Point(s['x'],s['z']).distance(area)<15]
result={'schemaVersion':1,'kind':'local source-placement proximity audit, not geometry or browser acceptance','sources':sources,'pavingAreaGame2':area.area,'pavingBounds':lo,
 'canopyCandidates':selected(canopy['trees'],'canopy'),'baseTreeCandidates':selected(base['trees'],'base-tree'),'detailCandidates':selected(base['details'],'low-plant'),'streetCandidates':benches,'lifeHubCollisionCandidates':props,
 'remaining':['Actual tree trunk/crown and bench geometry for nearby placements','Bamboo cafe exact footprint if its configured anchor is nearby','Runtime supplemental roadside plants and moving actors','Camera clearance and real player walking'], 'runtimeInstalled':False}
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:len(result[k]) for k in ['canopyCandidates','baseTreeCandidates','detailCandidates','streetCandidates','lifeHubCollisionCandidates']}));print(json.dumps({'canopyRootsOnPaving':[r['index'] for r in result['canopyCandidates'] if r['rootWithinPaving']],'baseRootsOnPaving':[r['index'] for r in result['baseTreeCandidates'] if r['rootWithinPaving']]}))
