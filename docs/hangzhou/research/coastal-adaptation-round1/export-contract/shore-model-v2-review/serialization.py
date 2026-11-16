import runpy
from pathlib import Path
scope=runpy.run_path(str(Path(__file__).with_name('check.py')));globals().update({k:v for k,v in scope.items() if not k.startswith('__')})
rows=[]
for rec in m['objects']:
 part=next(a for a in actual if a['name']==rec['name']+'_'+rec['material']);gt=part['triangles'];fp=shapely.union_all([Polygon(t[:,:2]) for t in gt if Polygon(t[:,:2]).area>1e-12]);original=footprints[rec['id']]
 # Closed positive-volume mesh with upward tops: directed normals of source boundary vertical faces should face wet area.
 frontnormal=[]
 prop=next(p for p in props if p['id']==rec['id']);line=LineString(prop['geometryGame']['coordinates'])
 for t in all_npz[rec['id']]:
  if max(Point(p[:2]).distance(line) for p in t)>1e-8:continue
  n=np.cross(t[1]-t[0],t[2]-t[0]);nxy=np.linalg.norm(n[:2])
  if nxy<1e-10:continue
  c=t.mean(axis=0);q=c[:2]+n[:2]/nxy*.01;frontnormal.append(wet.covers(Point(q)))
 rows.append({'id':rec['id'],'npzAllBoundaryFrontNormalsFaceWet':all(frontnormal),'boundaryVerticalFaces':len(frontnormal),'float32FootprintWetIntrusionAreaGame2':fp.intersection(wet).area,'float32VsNpZFootprintHausdorffGame':fp.hausdorff_distance(original),'float32VsNpZFootprintSymmetricDifferenceGame2':fp.symmetric_difference(original).area,'distanceToActualCityBalconyFootprintGame':None})
bal,bg=glb(base+'landmarks/city-balcony-v1/city-balcony.glb');bf=shapely.union_all([Polygon(t[:,:2]) for part in bal for t in part['triangles'] if Polygon(t[:,:2]).area>1e-12])
for row in rows:row['distanceToActualCityBalconyFootprintGame']=footprints[row['id']].distance(bf)
save('serialized-boundary.json',rows)
