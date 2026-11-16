"""Bind the existing street kit's selection frame to source-mapped Hangzhou roads."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from shapely.geometry import LineString,Point
from city_config import ROOT,load_city
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(source,cafe,output):
 source,cafe,output=map(lambda p:Path(p).resolve(),[source,cafe,output])
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
 c=json.loads((source/'city.json').read_text());v=json.loads((cafe/'report.json').read_text());site=v['site'];p=Point(site['x'],site['z'])
 roads=[r for r in c['roads'] if r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no' and r['name']!='支路' and r['kind'] in ['primary','secondary','tertiary']]
 nearest=min(roads,key=lambda r:LineString(r['points']).distance(p));name=nearest['name']
 selected=[r for r in roads if r['name']==name and LineString(r['points']).distance(p)<700]
 points=np.array([point for r in selected for point in r['points'] if math.dist(point,[site['x'],site['z']])<700])
 center=points.mean(axis=0);_,vectors=np.linalg.eigh(np.cov(points-center,rowvar=False));axis=vectors[:,-1]
 along=(points-center)@axis;ends=[points[int(np.argmin(along))].tolist(),points[int(np.argmax(along))].tolist()]
 profile=load_city('hangzhou');marks={m['id']:m for m in c['landmarks']}
 profile['streetScene'].update(name=name+'–钱江新城',originGame=[site['x'],site['z']],destinationGame=[marks['civic-center']['x'],marks['civic-center']['z']],
  spineGame=ends,cafeAnchor=[site['x'],site['z']],sourceRoadName=name,sourceRoadIds=[r['id'] for r in selected],
  lengthGame=math.dist(*ends),selectionFrameOnly=True,status='source-bound-geographic-candidate-physical-and-visual-pending')
 profile['localLighting']=[{'id':'hangzhou-cafe','x':site['x'],'z':site['z'],'inner':130,'outer':220},
  {'id':'city-balcony','x':marks['city-balcony']['x'],'z':marks['city-balcony']['z'],'inner':420,'outer':600}]
 profile['water']['publicSurfaceLookCenterGame']=[marks['city-balcony']['x'],marks['city-balcony']['z']]
 output.mkdir(parents=True,exist_ok=True)
 (output/'profile-proposal.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n')
 report={'kind':'existing-game-unit-street-kit-source-binding','streetScene':profile['streetScene'],
  'inputs':{'citySha256':digest(source/'city.json'),'cafeReportSha256':digest(cafe/'report.json')},
  'profileSha256':digest(output/'profile-proposal.json'),'noNewRoadGeometryFromFrame':True,
  'pending':['street object placement/collision','trees and cafe avoidance','terrain/site level','shader/lighting visuals and performance','browser driving/walking']}
 (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--cafe',required=True);p.add_argument('--output',required=True)
 a=p.parse_args();prepare(a.input,a.cafe,a.output)
