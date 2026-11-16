"""Inspect all raw ways/relations near three Cainiao parcels, no source edits."""
import hashlib,json,sys,time
from pathlib import Path
import osmium
from shapely.geometry import Point,LineString,Polygon,box,shape
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
BBOX=[119.9575,30.2630,119.9663,30.2677]

class Inspector(osmium.SimpleHandler):
    def __init__(self):
        super().__init__();self.bounds=box(*BBOX);self.nodes=[];self.ways=[];self.relations=[];self.ids=set();self.invalid=[]
    def node(self,n):
        if n.location.valid() and BBOX[0]<=n.lon<=BBOX[2] and BBOX[1]<=n.lat<=BBOX[3] and len(n.tags):
            self.nodes.append({'type':'node','id':n.id,'version':n.version,'timestamp':str(n.timestamp),'tags':dict(n.tags),'coordinates':[n.lon,n.lat]})
    def way(self,w):
        if any(not n.location.valid() for n in w.nodes):return
        coords=[[n.lon,n.lat] for n in w.nodes]
        if len(coords)<2:return
        lo,la=zip(*coords)
        if max(lo)<BBOX[0] or min(lo)>BBOX[2] or max(la)<BBOX[1] or min(la)>BBOX[3]:return
        if not LineString(coords).intersects(self.bounds):return
        closed=w.is_closed();poly=Polygon(coords) if closed and len(coords)>3 else None
        self.ids.add(w.id);self.ways.append({'type':'way','id':w.id,'version':w.version,'timestamp':str(w.timestamp),'tags':dict(w.tags),'closed':closed,
            'nodeIds':[str(n.ref) for n in w.nodes],'coordinates':coords,'simple':LineString(coords).is_simple,'polygonValid':poly.is_valid if poly else None})
    def relation(self,r):
        members=[{'type':m.type,'ref':m.ref,'role':m.role} for m in r.members]
        if any(m['type']=='w' and m['ref'] in self.ids for m in members):
            self.relations.append({'type':'relation','id':r.id,'version':r.version,'timestamp':str(r.timestamp),'tags':dict(r.tags),'members':members})

def main():
    path=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf';manifest=json.loads((path.parent/'source-manifest.json').read_text());h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    assert h.hexdigest()==manifest['sha256']=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
    inspector=Inspector();started=time.monotonic();inspector.apply_file(str(path),locations=True,idx='flex_mem');elapsed=time.monotonic()-started
    (HERE/'raw-osm-objects.json').write_text(json.dumps({'source':manifest,'bboxWGS84':BBOX,'sourceCrs':'EPSG:4326','license':'ODbL-1.0','attribution':'©OpenStreetMapcontributors',
        'selection':'All raw tagged/untagged waylines intersectingbbox, all tagged nodesinside, relations withlocalwaymembers. Way-line test doesnotcollect hugeenclosing polygons withno boundaryinsidebbox. No geometryfix orheight inference.',
        'nodes':inspector.nodes,'ways':inspector.ways,'relations':inspector.relations},ensure_ascii=False,indent=2)+'\n')
    buildings=[w for w in inspector.ways if 'building' in w['tags'] or 'building:part' in w['tags']]
    closedOther=[w for w in inspector.ways if w['closed'] and w not in buildings]
    report={'sourcePbfSha256':h.hexdigest(),'actualElapsedSeconds':round(elapsed,3),'counts':{'taggedNodes':len(inspector.nodes),'allRawWays':len(inspector.ways),'relationsWithLocalWays':len(inspector.relations),'buildingOrPartWays':len(buildings),'otherClosedWays':len(closedOther)},
        'buildingOrPartRecords':[{k:w[k] for k in ['type','id','version','timestamp','tags','closed','polygonValid']} for w in buildings],
        'nonbuildingClosedRecords':[{k:w[k] for k in ['type','id','version','timestamp','tags','closed','polygonValid']} for w in closedOther],
        'buildingOrPartRelations':[r for r in inspector.relations if 'building' in r['tags'] or 'building:part' in r['tags']],
        'relationCoordinateOutlineRoleUnknown':'Rawlocalmembercoordinates retained; no building identity assigned basedon untaggedclosedway alone'}
    (HERE/'raw-osm-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'counts':report['counts'],'elapsedSeconds':report['actualElapsedSeconds'],'buildingIds':[w['id'] for w in buildings]},ensure_ascii=False))
if __name__=='__main__':main()
