"""Fixed-snapshot shoreline structure evidence; research outputs only, no asset edits."""
from pathlib import Path
import json,hashlib,osmium
from collections import Counter
from shapely.geometry import LineString,Point,Polygon,box,mapping
ROOT=Path(__file__).resolve().parents[6];OUT=Path(__file__).resolve().parent
PBF=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf';CITY=ROOT/'artifacts/cities/hangzhou/water-data-v3/city.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PBF)=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
c=json.loads(CITY.read_text());m=c['meta'];river=next(w for w in c['water'] if w['id']=='relation/8227206');water=Polygon(river['rings'][0],river['rings'][1:]);domain=box(*m['extent']);bank_band=water.boundary.buffer(1)
def project(p):return [(p[0]-m['originWGS84'][0])*m['eastMetresPerDegree']*.6,(p[1]-m['originWGS84'][1])*m['northMetresPerDegree']*.6]
def wanted(tags):return tags.get('man_made') in ['embankment','dyke','quay','pier','breakwater','groyne','seawall'] or tags.get('barrier') in ['retaining_wall','wall','city_wall'] or tags.get('natural') in ['cliff','coastline'] or tags.get('embankment') in ['yes','both','left','right'] or tags.get('waterway') in ['dam','weir']
old=json.loads((ROOT/'docs/hangzhou/research/coastal-adaptation-round1/source-bridge-context.json').read_text());members={x['ref'] for r in old['relations'] if r['id']=='relation/8227206' for x in r['members'] if x['type']=='w'}
class Read(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.structures=[];self.paths=[];self.members=[];self.relations=[];self.points=[]
 def way(self,w):
  tags=dict(w.tags);is_structure=wanted(tags);is_path=tags.get('highway') in ['footway','cycleway','path','pedestrian','steps'];is_member=w.id in members
  if not (is_structure or is_path or is_member) or len(w.nodes)<2 or not all(n.location.valid() for n in w.nodes):return
  coords=[[n.lon,n.lat] for n in w.nodes];game=list(map(project,coords));line=LineString(game)
  if not line.intersects(domain):return
  d=line.distance(water)
  if is_path and not is_structure and not is_member and d>180:return
  boundary_distance=line.distance(water.boundary)
  record={'type':'Feature','id':'way/'+str(w.id),'properties':{'version':w.version,'timestamp':str(w.timestamp),'tags':tags,'nodeIds':[str(n.ref) for n in w.nodes],'waterDistanceGame':d,'waterBoundaryDistanceGame':boundary_distance,'isRiverBoundaryMember':is_member,'lengthGame':line.length,'withinRiverBoundary1GameLength':line.intersection(bank_band).length,'waterInteriorLengthGame':line.intersection(water).length},'geometry':mapping(LineString(coords)),'geometryGame':mapping(line)}
  if is_structure:self.structures.append(record)
  if is_path and d<=180:self.paths.append(record)
  if is_member:self.members.append(record)
 def relation(self,r):
  if wanted(dict(r.tags)):self.relations.append({'id':'relation/'+str(r.id),'version':r.version,'timestamp':str(r.timestamp),'tags':dict(r.tags),'members':[{'type':m.type,'ref':m.ref,'role':m.role} for m in r.members]})
 def node(self,n):
  tags=dict(n.tags)
  if not wanted(tags) or not n.location.valid():return
  p=project([n.lon,n.lat])
  if domain.covers(Point(p)):self.points.append({'id':'node/'+str(n.id),'version':n.version,'timestamp':str(n.timestamp),'tags':tags,'pointWGS84':[n.lon,n.lat],'pointGame':p})
r=Read();r.apply_file(str(PBF),locations=True)
for name,features in [('structures.geojson',r.structures),('riverside-paths.geojson',r.paths),('river-boundary-members.geojson',r.members)]:
 (OUT/name).write_text(json.dumps({'type':'FeatureCollection','sourcePbfSha256':sha(PBF),'sourceSnapshot':'2026-10-11','sourceCrs':'EPSG:4326','gameFrame':'current Hangzhou .60 once','features':features},ensure_ascii=False,indent=2)+'\n')
(OUT/'relations-and-nodes.json').write_text(json.dumps({'relations':r.relations,'nodes':r.points},ensure_ascii=False,indent=2)+'\n')
near=[f for f in r.structures if f['properties']['waterBoundaryDistanceGame']<180]
summary={'pbfSha256':sha(PBF),'citySha256':sha(CITY),'structuresInCity':len(r.structures),'structuresWithin180GameOfQiantangBoundary':len(near),'pathsWithin180GameOfQiantangWater':len(r.paths),'riverBoundaryMembersInCity':len(r.members),'taggedStructureRelationsInProvince':len(r.relations),'structureNodesInCity':len(r.points),'nearbyStructureList':[{'id':f['id'],**f['properties']} for f in sorted(near,key=lambda f:f['properties']['waterBoundaryDistanceGame'])]}
(OUT/'extraction-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='nearbyStructureList'},ensure_ascii=False));print(json.dumps(summary['nearbyStructureList'],ensure_ascii=False,indent=2))
