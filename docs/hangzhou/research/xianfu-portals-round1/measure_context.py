"""Finite read-only source-geometry measurements; writes this research directory only."""
from pathlib import Path
import hashlib,json,math,html
from shapely.geometry import LineString,Point
from pyproj import Geod
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
src=OUT/'fixed-osm-context.json';d=json.loads(src.read_text());config=ROOT/'config/cities/hangzhou.json';g=json.loads(config.read_text())['geography'];ways={w['id']:w for w in d['ways']};geod=Geod(ellps='WGS84')
def xy(c):return [(c[0]-g['originWGS84'][0])*g['eastMetresPerDegree'],(c[1]-g['originWGS84'][1])*g['northMetresPerDegree']]
def ll(c):return [c[0]/g['eastMetresPerDegree']+g['originWGS84'][0],c[1]/g['northMetresPerDegree']+g['originWGS84'][1]]
def line(w):return LineString([xy(c) for c in w['coordinates']])
w=ways[697096305];a,b=w['coordinates'];az,_,length=geod.inv(*a,*b);low=line(w);cross=[]
for wid in (358503184,697096309):
 upper=ways[wid];pt=low.intersection(line(upper));assert pt.geom_type=='Point';common=sorted(set(w['nodeIds'])&set(upper['nodeIds']));assert not common
 cross.append({'upperWay':wid,'wgs84':ll(pt.coords[0]),'distanceFromWestPortalLocalMetres':low.project(pt),'sharedSourceNodeIds':common,'navigationJunction':False,'upperTags':upper['tags']})
portals=[]
for nid,c in zip(w['nodeIds'],w['coordinates']):
 near=[v['id'] for v in d['ways'] if nid in v['nodeIds']]
 portals.append({'nodeId':nid,'wgs84':c,'gamePoint':[q*g['scale'] for q in xy(c)],'connectedWayIds':near,'nearestUpperCentrelineLocalMetres':min(Point(xy(c)).distance(line(ways[i])) for i in (358503184,697096309))})
rels=[]
for r in d['directContainingRelations']:
 if r['tags'].get('route')!='bus':continue
 ms=[(i,m) for i,m in enumerate(r['members']) if m['type']=='w' and m['ref'] in (1418959639,697096305,697096306)]
 assert [m['ref'] for i,m in ms]==[1418959639,697096305,697096306]
 assert ms[-1][0]-ms[0][0]==2
 rels.append({'relationId':r['id'],'version':r['version'],'timestamp':r['timestamp'],'tags':r['tags'],'memberIndicesZeroBased':[i for i,m in ms],'orderedWayRefs':[m['ref'] for i,m in ms],'directionOrderValidated':False})
missing=['width','maxwidth','height','maxheight','lanes','ele','incline','surface','lit','sidewalk','embankment','cutting']
assert all(k not in w['tags'] for k in missing)
mount=[]
mid=low.interpolate(.5,normalized=True)
for i in (371748017,697096310):
 v=ways[i];cs=[v['coordinates'][0],v['coordinates'][-1]];c=min(cs,key=lambda c:Point(xy(c)).distance(mid));mount.append({'wayId':i,'name':v['tags'].get('name'),'nearestMappedEndpointWGS84':c,'endpointDistanceFromLowTunnelMidpointLocalMetres':Point(xy(c)).distance(mid),'sharedNodeIdsWithLowTunnel':sorted(set(v['nodeIds'])&set(w['nodeIds']))})
results={'researchDate':'2026-11-11','status':'source-topology-confirmed-portal-dimensions-and-appearance-blocked','inputs':{'fixedContextSha256':sha(src),'cityConfigSha256':sha(config),'P1ReviewSha256':sha(ROOT/'docs/hangzhou/audit/review-20261016/landmark-evidence/source-selection-v2/P1-minimum-repair.md'),'portalContextSha256':sha(ROOT/'docs/hangzhou/audit/review-20261016/landmark-evidence/source-selection-v2/portal-context.json')},'projection':g,'measurementClass':'measured-from-OSM-coordinate-geometry-not-field-survey','sourcePositionalAccuracy':'unknown; decimal precision is not positional accuracy','tunnel':{'wayId':w['id'],'version':w['version'],'timestamp':w['timestamp'],'tags':w['tags'],'sourceNodeCount':len(w['nodeIds']),'wgs84GeodesicLengthMetres':length,'localProjectionLengthMetres':low.length,'gameLength':low.length*g['scale'],'initialAzimuthDegreesFromNorth':az,'missingDimensionAndConstructionTags':missing},'portals':portals,'planarCrossings':cross,'busRelations':rels,'distinctMountainTunnels':mount,'physicalMeasurementVerified':False,'photosVerified':0,'browserOrDrivingTestPerformed':False}
(OUT/'measurements.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
# Fixed source plan. Thin centre-lines deliberately do not depict carriageway widths.
center=mid.coords[0];unit=5.0;cx,cy=460,310
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="660" viewBox="0 0 920 660">','<rect width="920" height="660" fill="#f7fafc"/>','<style>text{font-family:Arial,sans-serif;fill:#182b3a;font-size:14px}</style>','<text x="25" y="30" font-size="21">Xianfu road underpass — fixed OSM centre-line evidence</text>','<text x="25" y="55">Snapshot 2026-10-11 | WGS84 → project local metres | North up | Widths/heights unknown</text>','<defs><clipPath id="frame"><rect x="25" y="80" width="870" height="470"/></clipPath></defs>','<g clip-path="url(#frame)">']
def pos(c):x,y=xy(c);return cx+(x-center[0])*unit,cy-(y-center[1])*unit
for wid,color in [(358503184,'#e58a18'),(697096309,'#c16704'),(1418959639,'#228452'),(697096306,'#228452'),(697096305,'#405bc8')]:
 pts=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(pos,ways[wid]['coordinates']));dash=' stroke-dasharray="7 4"' if wid==697096305 else '';svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3"{dash}/>')
for i,p in enumerate(portals):
 x,y=pos(p['wgs84']);dx=-145 if i==0 else 12;dy=28 if i==0 else -12
 svg += [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#405bc8"/>',f'<text x="{x+dx:.2f}" y="{y+dy:.2f}">node {p["nodeId"]}</text>']
for p in cross:
 x,y=pos(p['wgs84']);svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="none" stroke="#b32424" stroke-width="2"/>')
svg += ['</g>','<text x="25" y="100">N ↑</text>','<text x="25" y="575">Blue dashed: way697096305, layer=-1 / tunnel=yes; green: connected residential approaches.</text>','<text x="25" y="598">Orange: two Xianfu carriageways. Red circles: centre-line crossings WITHOUT shared source nodes.</text>','<text x="25" y="622">OSM contributors / ODbL-1.0. Source topology only; NOT a portal outline, survey or visual acceptance.</text>',f'<path d="M 730 520 h {20*unit}" stroke="#182b3a" stroke-width="3"/><text x="750" y="510">20 local m</text>','</svg>']
(OUT/'source-plan.svg').write_text('\n'.join(svg)+'\n')
print(json.dumps({'length':results['tunnel'],'crossings':cross,'portals':portals,'distinctMountainTunnels':mount},ensure_ascii=False,indent=2))
