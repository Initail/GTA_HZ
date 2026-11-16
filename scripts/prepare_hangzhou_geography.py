"""Bind game-unit terrain/road/water data in a fresh runtime investigation.

All high-resolution decks, site floors and water datums remain explicitly
estimated. This packet is not a gameplay, GLB or visual acceptance result.
"""
from __future__ import annotations
import argparse,hashlib,json,math,shutil
from pathlib import Path
from collections import Counter
import numpy as np
from shapely.geometry import Polygon,Point
from city_config import ROOT,load_city
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sample_grid(values,g,x,z):
 u=(x-g['x0'])/g['step'];v=(z-g['z0'])/g['step'];i=min(g['columns']-2,max(0,math.floor(u)));j=min(g['rows']-2,max(0,math.floor(v)))
 fx,fz=max(0,min(1,u-i)),max(0,min(1,v-j));a,b,d,c=map(float,[values[j,i],values[j,i+1],values[j+1,i],values[j+1,i+1]])
 return a+(b-a)*fx+(d-a)*fz if fx+fz<=1 else c+(d-c)*(1-fx)+(b-c)*(1-fz)

def prepare(skeleton,collision,terrain,roads,output):
 skeleton,collision,terrain,roads,output=map(lambda p:Path(p).resolve(),[skeleton,collision,terrain,roads,output])
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
 profile=load_city('hangzhou');scale=profile['geography']['scale'];geo=profile['geography']
 city=json.loads((collision/'city-runtime-collision.json').read_text());cr=json.loads((collision/'report.json').read_text());tm=json.loads((terrain/'manifest.json').read_text());rl=json.loads((roads/'road-levels.json').read_text());rr=json.loads((roads/'report.json').read_text())
 source_sha=digest(skeleton/'city.json')
 if cr['inputSha256']['city']!=source_sha or tm['sourcePlacesSha256']!=source_sha or rl['inputs']['citySha256']!=source_sha:raise ValueError('Mixed source cities')
 if cr['cityRuntimeCollisionSha256']!=digest(collision/'city-runtime-collision.json') or rl['inputs']['terrainManifestSha256']!=digest(terrain/'manifest.json') or rr['roadLevelsSha256']!=digest(roads/'road-levels.json') or rr['navigationSha256']!=digest(roads/'navigation.json'):raise ValueError('Changed candidate inputs')
 if city['meta']['cityId']!='hangzhou' or tm['units']!='real metres above EGM2008; not yet game-scaled' or rl['units']!='game metres; scale already applied once':raise ValueError('City/unit mismatch')
 g=tm['grid'];arrays={}
 for filename in ['dsm-egm2008-metres.bin','ground-estimate-egm2008-metres.bin']:
  p=terrain/filename
  if digest(p)!=tm['files'][filename]['sha256']:raise ValueError('Changed source terrain grid')
  values=np.fromfile(p,dtype='<f4').reshape(g['rows'],g['columns'])
  if not np.all(np.isfinite(values)):raise ValueError('Incomplete terrain')
  arrays[filename]=values
 reference_path=ROOT/profile['water']['referencePolicy'];reference=json.loads(reference_path.read_text());body_reports=[]
 controlled={reference[key]['waterFeatureId']:(reference[key].get('sameSourceEditedDSMHeightM',reference[key].get('sameSourceEditedDSMReferenceHeightM')),key) for key in ['WestLake','Qiantang']}
 for water in city['water']:
  polygon=Polygon(water['rings'][0],water['rings'][1:])
  if not polygon.is_valid:raise ValueError('Invalid water source polygon')
  if water['id'] in controlled:
   metres,system=controlled[water['id']];basis='source-consistent provisional edited DSM reference; absolute datum conversion and tide not verified'
  else:
   point=polygon.representative_point();metres=sample_grid(arrays['dsm-egm2008-metres.bin'],g,point.x,point.y);system='separate-source-waterbody';basis='representative point in actual polygon, edited 30m DSM estimate; narrow controlled canals and pools uncertain'
  water['height']=metres*scale;water['heightBasis']=basis;water['heightDatum']='EGM2008 source estimate';water['heightStatus']='estimated-not-surveyed'
  body_reports.append({'id':water['id'],'system':system,'heightGame':water['height'],'sourceMetres':metres,'basis':basis})
 by_id={r['id']:r for r in rl['roads']}
 for road in city['roads']:
  candidate=by_id[road['id']]
  if candidate['nodeIds']!=road['nodeIds'] or candidate['points']!=road['points'] or candidate['width']!=road['width']:raise ValueError('Changed road identity')
  road['heights']=candidate['heights']
 city['meta']['terrainStatus']='source-DSM-estimate; road corridor earthworks and landmark floors pending'
 city['meta']['roadSurfaceStatus']='source-node heights in game units; deck geometry/tunnels/actors require current physical QA'
 city['meta']['status']='runtime-geography-packet-not-playable-delivery'
 output.mkdir(parents=True,exist_ok=True);folder=output/'geography';folder.mkdir()
 game_ground=(arrays['ground-estimate-egm2008-metres.bin']*scale).astype('<f4')
 (folder/'terrain-game.bin').write_bytes(game_ground.tobytes());shutil.copyfile(roads/'road-levels.json',folder/'road-levels.json');shutil.copyfile(roads/'navigation.json',output/'navigation.json')
 (output/'city.json').write_text(json.dumps(city,ensure_ascii=False,separators=(',',':')))
 manifest={'schemaVersion':1,'cityId':'hangzhou','originWGS84':geo['originWGS84'],'horizontalScale':scale,'eastMetresPerDegree':geo['eastMetresPerDegree'],'northMetresPerDegree':geo['northMetresPerDegree'],
  'units':'game metres; scale applied once','grid':g,'terrainFile':'terrain-game.bin','terrainSha256':digest(folder/'terrain-game.bin'),'roadLevelsFile':'road-levels.json','roadLevelsSha256':digest(folder/'road-levels.json'),'roadTerrainTransitionGame':profile['roadSurfaces']['terrainTransitionGame'],
  'sourceStatus':'30m DSM-derived ground estimate, never measured DTM','groundMeshRequired':'same b-d triangle diagonal; match road corridor earthworks before physical acceptance'}
 (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 report={'kind':'estimated-source-bound-runtime-geography-packet','cityId':'hangzhou','counts':city['meta']['counts'],'roadCount':len(rl['roads']),'waterSystems':dict(Counter(r['system'] for r in body_reports)),
  'waterBodies':body_reports,'roadMaximumGradient':rr['maximumTotalGradient'],
  'inputs':{'skeletonCitySha256':source_sha,'collisionReportSha256':digest(collision/'report.json'),'sourceTerrainManifestSha256':digest(terrain/'manifest.json'),'roadLevelReportSha256':digest(roads/'report.json'),'waterReferenceSha256':digest(reference_path)},
  'files':{str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file()},
  'pending':['baked 3D terrain/road/deck meshes','road corridor earthworks','individual landmark ground platforms','temple terraces and steps','tunnel portals/ceilings','per-body shoreline and simultaneous reflections','game loading and all browser gameplay/visual/performance acceptance']}
 (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['kind','counts','roadCount','waterSystems','roadMaximumGradient','pending']},ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--skeleton',required=True);p.add_argument('--collision',required=True);p.add_argument('--terrain',required=True);p.add_argument('--roads',required=True);p.add_argument('--output',required=True)
 a=p.parse_args();prepare(a.skeleton,a.collision,a.terrain,a.roads,a.output)
