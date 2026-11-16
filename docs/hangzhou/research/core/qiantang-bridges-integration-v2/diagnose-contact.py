from pathlib import Path
import json,math,collections
import numpy as np
from shapely.geometry import Polygon,Point,box
from shapely import STRtree
P=Path(__file__).resolve().parent;runtime=json.loads((P/'runtime-collision.json').read_text());solids=json.loads((P/'collision-candidate.json').read_text())['rows'];polys=[Polygon(r['polygonGame']) for r in solids];tree=STRtree(polys);roads={r['id']:r for r in json.loads((P/'candidate-road-levels.json').read_text())['roads']};output=[];bykind=collections.Counter()
for sample in runtime['rows']:
 if not sample['carBlocked']:continue
 point=Point(sample['x'],sample['z']);hits=[]
 for j in tree.query(point.buffer(1.15)):
  r=solids[int(j)];y=sample['height']
  if y>=r['maxYGame'] or y+1.6<=r['minYGame']:continue
  d=point.distance(polys[int(j)])
  if d>=1.15:continue
  hits.append({'id':r['id'],'kind':r['kind'],'distanceGame':d,'minY':r['minYGame'],'maxY':r['maxYGame'],'maxAboveRawFloor':r['maxYGame']-y,'minAboveRawFloor':r['minYGame']-y,'actualPrimitiveVertices':r['verticesGameENU'],'originalSourceFaceRange':r['originalSourceFaceRange']});bykind[(sample['bridgeId'],r['kind'])]+=1
 output.append({**sample,'sourceMemberHits':hits})
report={'scope':'Exact cause of actual CityCollision centre-point failures using retained source primitive envelopes; positive envelope is not proof of exact car/body mesh intersection','cases':output,'kindCounts':[{'bridgeId':k[0],'kind':k[1],'count':n} for k,n in bykind.items()],'unexplained':sum(not r['sourceMemberHits'] for r in output),'rule':'original 1.15 margin and raw floor..floor+1.6 body interval unchanged'};(P/'contact-diagnostics.json').write_text(json.dumps(report,separators=(',',':')));print(report['kindCounts']);print('unexplained',report['unexplained']);print([(r['bridgeId'],r['sourceMemberHits'][0]['kind'],r['sourceMemberHits'][0]['maxAboveRawFloor']) for r in output[::max(1,len(output)//8)]])
