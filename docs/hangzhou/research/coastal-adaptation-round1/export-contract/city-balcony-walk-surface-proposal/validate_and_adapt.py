from pathlib import Path
import json,math,hashlib,collections
import numpy as np
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
ROOT=Path.cwd();OUT=Path(__file__).parent
walk=json.loads((OUT/'public-walk-surfaces.json').read_text());occ=json.loads((OUT/'occupancy.json').read_text());seams=json.loads((OUT/'entry-seams.json').read_text());rows=[]
for level in walk['levels']:
 polys=[];area=0.;maximum=0
 for t in level['triangles']:
  assert t['actualGlbFaces'];vs=t['verticesGameXYZ'];a,b,c=np.array(vs);cross=np.cross(b-a,c-a);assert cross[1]<0 # XYZ swaps ENU winding; Babylon loader retains original root convention. Surface schema uses ENU below.
  p=Polygon([[v[0],v[2]] for v in vs]);assert p.area>0;polys.append(p);area+=p.area;maximum=max(maximum,t['maxFloat32PositionErrorGame'])
 source=Polygon(level['ringsXZ'][0],level['ringsXZ'][1:]);union=unary_union(polys);assert union.symmetric_difference(source).area<1e-7;assert abs(area-source.area)<1e-7
 rows.append({'id':level['id'],'triangleCount':len(polys),'sourcePublicAreaGame2':source.area,'triangleUnionSymDifferenceGame2':union.symmetric_difference(source).area,'triangleAreaSumErrorGame2':abs(area-source.area),'actualGlbAllTrianglesMatched':True,'maxFloat32VertexErrorGame':maximum})
assert len(occ['existingFiniteHeightSolids'])==136;assert all(c['maxYGame']>c['minYGame'] for c in occ['existingFiniteHeightSolids'])
assert all(s['lessThanUnchangedStep048'] and not s['outsideWet'] for r in seams['seams'] for s in r['crossingSamples'])
# Guard-panel vertices are all actual modeled glass vertices; surfaces/rails stay separate.
helpers=ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-clip-v3-review/check.py';prefix=helpers.read_text().split('ap=argparse.ArgumentParser')[0];namespace={'__file__':str(helpers)};exec(compile(prefix,str(helpers),'exec'),namespace);parts,_=namespace['glb'](walk['sourceArtifact']);glass=np.unique(np.concatenate([p['triangles'].reshape(-1,3) for p in parts if p['material']=='landmarkglass']),axis=0)
from shapely.strtree import STRtree
tree=STRtree([Point(p[:2]) for p in glass]);maxRail=0.;failRail=[]
for panel in occ['guardPanels']:
 for x,y,z in panel['verticesGameXYZ']:
  ids=tree.query(Point(x,z),predicate='dwithin',distance=.001);d=min((np.linalg.norm(glass[i]-[x,z,y]) for i in ids),default=math.inf);maxRail=max(maxRail,d)
  if d>.001:failRail.append(panel['id'])
assert not failRail
# Match exact SiteSurfaceData schema with explicit already-scaled ENU vertex order.
def adapt_level(level):return {'id':level['id'],'triangles':[[[v[0],v[2],v[1]] for v in t['verticesGameXYZ']] for t in level['triangles']]}
upper=next(x for x in walk['levels'] if x['id'].endswith(':upper'));lower=next(x for x in walk['levels'] if x['id'].endswith(':lower'))
overlays=[]
for light in occ['skylights']:
 assert light['intactPublicSlabBelow'] and not light['actualModeledShaft'];ts=[[[x,z,y] for x,y,z in t['verticesGameXYZ']] for t in light['actualTopOverlayTriangles']]
 for t in ts:
  a,b,c=np.array(t);assert np.cross(b-a,c-a)[2]>0;assert max(v[2] for v in t)-upper['baseYGame']<.051
 overlays.append({'id':'city-balcony:upper:'+light['id']+'-thin-cover','triangles':ts})
recommended={'cityId':'hangzhou','units':'game east/north/up; scale applied once','terrainCuts':[],'walkFloors':[adapt_level(upper),*overlays]}
allFloors={**recommended,'walkFloors':[adapt_level(lower),*recommended['walkFloors']]}
for filename,data in [('site-surfaces-upper-only.json',recommended),('site-surfaces-all-public-geometry.json',allFloors)]:
 (OUT/filename).write_text(json.dumps(data,indent=2)+'\n')
report={'floorGeometry':rows,'finiteHeightSolids':136,'guardPanels':len(occ['guardPanels']),'guardPanelVerticesAllPresentInActualGlbWithin1mm':not failRail,'maxGuardVertexErrorGame':maxRail,'skylightCount':len(overlays),'sameUpperOverlayTriangles':sum(len(o['triangles']) for o in overlays),'recommendedUpperTriangles':sum(len(o['triangles']) for o in recommended['walkFloors']),'allPublicGeometryTriangles':sum(len(o['triangles']) for o in allFloors['walkFloors']),'lowerEntryEnabledInRecommendation':False,'seamCurrentGroundProbeChecks':{r['id']:{'samples':len(r['crossingSamples']),'maxInsideToOutsideDeltaGame':max(s['currentInsideToOutsideHeightDeltaGame'] for s in r['crossingSamples']),'sourcePathWithin10GameCount':len(r['nearbySourcePaths'])} for r in seams['seams']},'terrainCutsIncludedInAdapter':False,'runtimeBodyOrBrowserAccepted':False}
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
