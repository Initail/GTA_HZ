"""Read-only, finite 55-pair source-vs-runtime geometry measurements."""
from pathlib import Path
import hashlib,json
from collections import Counter
import shapely
from shapely.geometry import Polygon,shape,box,mapping
from shapely.ops import transform
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[3]
CITY=PROJECT/'artifacts/cities/hangzhou/runtime-data-v4/city.json';WATER=PROJECT/'data/processed/hangzhou-261011-extended/water.geojson';AUDIT=PROJECT/'docs/hangzhou/audit/water-overlap-v4.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,o):(ROOT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
c=json.loads(CITY.read_text());a=json.loads(AUDIT.read_text());w=json.loads(WATER.read_text());meta=c['meta'];origin=meta['originWGS84'];east=meta['eastMetresPerDegree'];north=meta['northMetresPerDegree'];scale=meta['horizontalScale'];bounds=box(*meta['extent'])
assert sha(CITY)==a['citySha256']
def proj(x,y,z=None):return ((x-origin[0])*east*scale,(y-origin[1])*north*scale)
def inv(x,y,z=None):return (x/(east*scale)+origin[0],y/(north*scale)+origin[1])
def parts(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return [g]
 return [p for q in getattr(g,'geoms',[]) for p in parts(q)]
source={f['id']:f for f in w['features']};targetids={p[k] for p in a['worst'] for k in ['a','b']}
projected={fid:transform(proj,shape(source[fid]['geometry'])).intersection(bounds) for fid in targetids};bodies={}
for idx,b in enumerate(c['water']):
 if b['id'] not in targetids:continue
 p=Polygon(b['rings'][0],b['rings'][1:]);candidates=parts(projected[b['id']]);matching=max(candidates,key=lambda q:q.intersection(p).area);bbox=transform(inv,p).bounds
 bodies[idx]=dict(index=idx,id=b['id'],name=b['name'],tags=source[b['id']]['properties']['tags'],sourceGeometry=source[b['id']]['geometry'],sourcePolygonCount=len(candidates),matchedPartIndex=candidates.index(matching),runtimeHeightGame=b['height'],runtimeHeightRealMetres=b['height']/scale,heightBasis=b.get('heightBasis'),heightStatus=b.get('heightStatus'),heightDatum=b.get('heightDatum'),runtimeAreaGameSquared=p.area,matchedSourceAreaGameSquared=matching.area,bboxWGS84=bbox,runtimeMatchesIndependentlySimplifiedSource=p.equals_exact(matching.simplify(.3,preserve_topology=True),.0001),runtimeGeometry=mapping(p),matchedSourceGeometry=mapping(matching),sourceToRuntimeSymmetricDifferenceGameSquared=matching.symmetric_difference(p).area)
rows=[]
for no,pair in enumerate(a['worst'],1):
 ia,ib=pair['aIndex'],pair['bIndex'];ba,bb=bodies[ia],bodies[ib];pa=shape(ba['runtimeGeometry']);pb=shape(bb['runtimeGeometry']);sa=shape(ba['matchedSourceGeometry']);sb=shape(bb['matchedSourceGeometry']);i=pa.intersection(pb);si=sa.intersection(sb);boundary=sa.boundary.intersection(sb.boundary);rp=transform(inv,i.representative_point())
 same_layer=ba['tags'].get('layer','0')==bb['tags'].get('layer','0');lock=any(b['tags'].get('water')=='lock' for b in [ba,bb]);sourcearea=si.area
 if not same_layer:kind='different-explicit-source-layer-hold'
 elif lock:kind='explicit-lock-chamber-boundary-hold'
 elif sourcearea>1e-6:kind='source-area-overlap-needs-identity-decision'
 elif boundary.length>1e-6:kind='independent-simplification-overlap-source-shared-boundary'
 else:kind='independent-simplification-overlap-source-near-or-point-boundary'
 rows.append(dict(pair=no,**pair,aTags=ba['tags'],bTags=bb['tags'],sourceOverlapAreaGameSquared=sourcearea,sourceOverlapAreaRealMetresSquared=sourcearea/scale**2,runtimeOverlapAreaRecomputedGameSquared=i.area,runtimeOverlapAreaRealMetresSquared=i.area/scale**2,sharedSourceBoundaryLengthGame=boundary.length,sourceDistanceGame=sa.distance(sb),sourceIntersectionType=si.geom_type,runtimeIntersectionGeometryGame=mapping(i),sourceIntersectionGeometryGame=mapping(si),representativePointWGS84=[rp.x,rp.y],measuredHeightDifferenceRealMetres=abs(ba['runtimeHeightGame']-bb['runtimeHeightGame'])/scale,heightStatus='difference of provisional estimated DSM planes, not measured water levels',classification=kind,declaredLayerDifference=not same_layer,hasExplicitLockTag=lock))
dump('body-measurements.json',dict(sourceCrs='EPSG:4326',measurementCrs='projected game east/north; actual source coefficients and scale0.60 from frozen city metadata',bodies=list(bodies.values())))
dump('pair-measurements.json',dict(asOfDate='2026-10-16',inputs={'city':str(CITY.relative_to(PROJECT)),'citySha256':sha(CITY),'water':str(WATER.relative_to(PROJECT)),'waterSha256':sha(WATER),'parentAudit':str(AUDIT.relative_to(PROJECT)),'parentAuditSha256':sha(AUDIT)},projection={k:meta[k] for k in ['originWGS84','eastMetresPerDegree','northMetresPerDegree','horizontalScale','verticalScale','extent']},pairs=rows,counts=Counter(z['classification'] for z in rows)))
print(json.dumps(dict(pairs=len(rows),bodies=len(bodies),classifications=Counter(z['classification'] for z in rows),sourceAreaOverlapPairs=sum(z['sourceOverlapAreaGameSquared']>1e-6 for z in rows)),ensure_ascii=False))
for z in rows:print(z['pair'],z['a'],z['b'],'sourceArea',round(z['sourceOverlapAreaGameSquared'],8),'boundary',round(z['sharedSourceBoundaryLengthGame'],3),z['classification'])
