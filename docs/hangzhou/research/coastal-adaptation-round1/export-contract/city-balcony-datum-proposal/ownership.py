from pathlib import Path
import json,math,hashlib
from shapely.geometry import Polygon,LineString,Point
ROOT=Path.cwd();OUT=Path(__file__).parent
spec=json.loads((ROOT/'docs/hangzhou/research/core/city-balcony-round2/spec.json').read_text());d=json.loads((ROOT/'artifacts/cities/hangzhou/landmarks/city-balcony-v1/model-delivery.json').read_text());p=json.loads((ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/proposals.json').read_text());prop=next(x for x in p['proposals'] if x['id']=='qianjiang-city-balcony');line=LineString(prop['geometryGame']['coordinates']);ax,az=d['anchorGame'];ca,sa=math.cos(spec['axisRadiansEastCCW']),math.sin(spec['axisRadiansEastCCW'])
def xy(ring):return [(ax+(u*ca-v*sa)*.6,az+(u*sa+v*ca)*.6) for u,v in ring]
regions={'upperPublic':Polygon(xy(spec['upperOuterUVMetres']),[xy(r) for r in spec['glazedFootprintsUVMetres']]),'lowerPublic':Polygon(xy(spec['lowerOuterUVMetres']),[xy(r) for r in spec['glazedFootprintsUVMetres']])}
for i,r in enumerate(spec['glazedFootprintsUVMetres']):regions['glazedSourcePart'+str(i)]=Polygon(xy(r))
def lines(g):
 if g.geom_type=='LineString':return [g]
 if hasattr(g,'geoms'):return [q for part in g.geoms for q in lines(part)]
 return []
rows=[]
for name,poly in regions.items():
 hits=lines(line.intersection(poly));rows.append({'region':name,'intervals':[{'fromStationGame':line.project(Point(g.coords[0])),'toStationGame':line.project(Point(g.coords[-1])),'lengthGame':g.length,'geometryGame':list(g.coords)} for g in hits],'totalLengthGame':sum(g.length for g in hits)})
(OUT/'source-floor-shore-intervals.json').write_text(json.dumps({'shoreId':prop['id'],'shoreLineSourceWaterId':prop['waterSourceId'],'basis':'source plan intersection only; not preapproved deletion or hidden-geometry mask','regions':rows,'forIntegration':'Resolve only these exact source-owned intervals plus corresponding actual wall/pier contacts after datum/profile frozen; preserve rest of 600g shore. Public lower volume remains open. No blanket fill and no deletion of all shoreline.'},indent=2)+'\n')
print(json.dumps(rows,indent=2))
