"""Small fixed-PBF bridge/rail/outer-boundary subset, with exact source refs."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode=True
import osmium
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
TARGET={4348186,826790145,29169666,29170042,154135283,154135290,
        336983476,340648409,589429905,306360721,306360739,589558021,
        546241781,607103735}
ENDS={3112466937,3112466958}
PBF=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'
class Ways(osmium.SimpleHandler):
    def __init__(self):super().__init__();self.rows=[];self.refs=set()
    def way(self,w):
        refs=[n.ref for n in w.nodes];tags=dict(w.tags)
        if w.id not in TARGET and not (ENDS.intersection(refs) and ('highway' in tags or 'railway' in tags)) and not ('railway' in tags and tags.get('bridge','no')!='no'):return
        self.refs.update(refs);self.rows.append({'id':f'way/{w.id}','nodeIds':[str(n) for n in refs],'tags':tags})
class Nodes(osmium.SimpleHandler):
    def __init__(self,refs):super().__init__();self.refs=refs;self.rows={}
    def node(self,n):
        if n.id in self.refs:self.rows[str(n.id)]=[n.location.lon,n.location.lat]
def main():
    ways=Ways();ways.apply_file(str(PBF));nodes=Nodes(ways.refs);nodes.apply_file(str(PBF))
    features=[]
    for w in ways.rows:
        coords=[nodes.rows[n] for n in w['nodeIds']]
        if int(w['id'][4:]) not in TARGET and not ENDS.intersection(map(int,w['nodeIds'])):
            if not any(120.130<x<120.139 and 30.188<y<30.203 for x,y in coords):continue
        features.append({'type':'Feature','id':w['id'],'properties':{'nodeIds':w['nodeIds'],'tags':w['tags'],'source':'fixed Geofabrik PBF','crs':'EPSG:4326','license':'ODbL-1.0'},'geometry':{'type':'LineString','coordinates':coords}})
    result={'type':'FeatureCollection','sourcePbfSha256':hashlib.sha256(PBF.read_bytes()).hexdigest(),'sourceSnapshot':'2026-10-11T20:21:06Z','features':features}
    (HERE/'fixed-bridge-features.geojson').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'features':len(features),'nodes':len(nodes.rows),'ids':[f['id'] for f in features]}))
if __name__=='__main__':main()
