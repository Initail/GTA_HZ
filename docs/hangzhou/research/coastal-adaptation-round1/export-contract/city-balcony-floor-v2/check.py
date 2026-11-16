from pathlib import Path
import json,math,hashlib,importlib.util,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
ROOT=Path.cwd();OUT=Path(__file__).parent

def load(p,name):
 s=importlib.util.spec_from_file_location(name,ROOT/p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
mod=load('scripts/landmarks/city_balcony_floor_v2.py','new');old=load('scripts/landmarks/city_balcony.py','old')
spec=json.loads((OUT/'candidate-spec.json').read_text());placement=spec['floorPlacement'];scale=.6;ax,az=placement['anchorGame'];lm={'x':ax,'z':az,'y':placement['baseYGame']};angle=spec['axisRadiansEastCCW'];ca,sa=math.cos(angle),math.sin(angle)
class Recorder:
 def __init__(self):self.frame=(11,22,.3);self.faces=[];self.local=[]
 def face(self,mat,pts,uv=None):
  x,y,a=self.frame;self.local.append((mat,pts));self.faces.append((mat,[(u*math.cos(a)-v*math.sin(a)+x,u*math.sin(a)+v*math.cos(a)+y,z) for u,v,z in pts]))
b=Recorder();start=b.frame;report=mod.build(b,lm,spec,scale);assert b.frame==start
triangles=[];minimum=float('inf')
for mat,face in b.faces:
 assert np.isfinite(face).all()
 for i in range(1,len(face)-1):
  tri=np.array([face[0],face[i],face[i+1]]);area=np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))/2;assert area>1e-10,(mat,face);minimum=min(area,minimum);triangles.append((mat,tri))
assert len(triangles)<=spec['budget']['maxTriangles'],(len(triangles),spec['budget'])
assert len(set(m for m,_ in b.faces))<=spec['budget']['maxMaterials']
assert report['waterMeshes']==report['lights']==report['stairsRampsLiftMeshes']==0
upper=Polygon(spec['upperOuterUVMetres'],spec['glazedFootprintsUVMetres']);lower=Polygon(spec['lowerOuterUVMetres'],spec['glazedFootprintsUVMetres']);fingers=[Polygon(f['polygonUVMetres']) for f in placement['fingers']];assert upper.difference(lower).symmetric_difference(shapely.union_all(fingers)).area<1e-10
allUpper=placement['mainUpperTrianglesUVMetres']+[[p[:2] for p in t] for f in placement['fingers'] for t in f['trianglesUVHMetres']];totalArea=sum(Polygon(t).area for t in allUpper);assert abs(totalArea-upper.area)<1e-7
assert all(upper.covers(Polygon(t).buffer(-1e-9)) for t in allUpper)
mainAreaByMaterial=collections.defaultdict(float);oldAreaByMaterial=collections.defaultdict(float);main=upper.difference(shapely.union_all(fingers))
for t,m in zip(placement['mainUpperTrianglesUVMetres'],placement['mainUpperTriangleMaterials']):mainAreaByMaterial[m]+=Polygon(t).area
for t,m in zip(spec['upperTrianglesUVMetres'],spec['upperTriangleMaterials']):oldAreaByMaterial[m]+=Polygon(t).intersection(main).area
assert all(abs(mainAreaByMaterial[k]-v)<1e-7 for k,v in oldAreaByMaterial.items())
# Exactly shared source inner-edge vertices and terminal heights; query and actual top triangle interpolation agree.
errors=[];endErrors=[];seamErrors=[];slope=[];toptris=[]
for f in placement['fingers']:
 for t in f['trianglesUVHMetres']:
  a,c,d=t;assert (c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0])>0
  for weights in [[1/3]*3,[.1,.1,.8],[.6,.3,.1]]:
   q=np.array(t).T@np.array(weights);h=mod.deck_height_metres(q[0],q[1],spec,'upper');errors.append(abs(h-q[2]));x=ax+(q[0]*ca-q[1]*sa)*scale;z=az+(q[0]*sa+q[1]*ca)*scale;assert abs(mod.deck_height_game(x,z,lm,spec,scale,'upper')-(lm['y']+q[2]*scale))<1e-8
   assert mod.deck_height_metres(q[0],q[1],spec,'lower') is None
  co=np.linalg.solve(np.c_[np.array(t)[:,:2],np.ones(3)],np.array(t)[:,2]);slope.append(float(np.linalg.norm(co[:2])))
  toptris.append(np.array(t))
 for edge in f['boundary']:
  assert edge['maxStepGame']<=1+1e-10
  for u,v,h in edge['samplesUVHMetres']:
   actual=mod.deck_height_metres(u,v,spec,'upper');assert actual is not None,(f['id'],edge,u,v)
   (endErrors if edge['kind']=='terminal' else seamErrors if edge['kind']=='inner-seam' else errors).append(abs(actual-h))
assert max(errors+endErrors+seamErrors)<1e-8
# Main top remains flat even near inner corners. Glass-room interior remains excluded at both levels.
for t in placement['mainUpperTrianglesUVMetres']:
 p=np.mean(t,axis=0);assert abs(mod.deck_height_metres(*p,spec,'upper')-6)<1e-8
for ring in spec['glazedFootprintsUVMetres']:
 q=Polygon(ring).representative_point()
 for level in ['upper','lower']:assert mod.deck_height_metres(q.x,q.y,spec,level) is None
foot=mod.ground_footprints(lm,spec,scale);origFoot=old.ground_footprints(lm,spec,scale);assert len(foot)==len(origFoot)==136
for a,c in zip(foot,origFoot):
 assert a['polygonGame']==c['polygonGame'];assert a['minYGame']==c['minYGame'];assert a['maxYGame']>a['minYGame']
 if a['kind']!='representative-pier':assert a['maxYGame']==c['maxYGame']
# No mutation of source spec/placement and rigid translation behaves exactly once.
shift=Recorder();delta=(23,-45,7);mod.build(shift,{**lm,'x':ax+23,'z':az-45,'y':lm['y']+7},spec,scale)
assert len(shift.faces)==len(b.faces)
for (_,a),(_,c) in zip(b.faces,shift.faces):
 for p,q in zip(a,c):assert max(abs(q[i]-p[i]-delta[i]) for i in range(3))<1e-8
invalid=Recorder()
try:mod.build(invalid,lm,spec,.36)
except ValueError:pass
else:raise AssertionError('double scale accepted')
assert not invalid.faces
missing=json.loads(json.dumps(spec));del missing['floorPlacement']
try:mod.build(Recorder(),lm,missing,.6)
except ValueError:pass
else:raise AssertionError('missing placement silently accepted')
# Preserve old assembly faces outside changed upper finger neighborhoods (excluding slab tessellation).
ob=Recorder();old.build(ob,lm,spec,scale)
def signature(mat,face):return mat,tuple(tuple(round(v,8) for v in p) for p in face)
newFaces=collections.Counter(signature(mat,face) for mat,face in b.local);unchanged=0
for mat,ps in ob.local:
 rel=[((p[0]/scale,p[1]/scale),(p[2]-lm['y'])/scale) for p in ps]
 # Main upper slab is intentionally re-triangulated only at new seam vertices.
 if all(abs(h-6)<1e-8 for _,h in rel) or all(abs(h-5.35)<1e-8 for _,h in rel):continue
 touched=any(h>=4.35 and any(poly.distance(Point(uv))<=1.000001 for poly in fingers) for uv,h in rel)
 if not touched:
  assert newFaces[signature(mat,ps)]>0,(mat,ps);unchanged+=1
# Existing independent 1g game-ground samples determine bounded cut/fill diagnostics only.
oldSamples=json.loads((ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-datum-proposal/finger-samples.json').read_text());terrain=[]
for f in oldSamples:
 vals=[]
 for s in f['footprintSamples1Game']:
  h=mod.deck_height_game(s['x'],s['z'],lm,spec,scale,'upper')
  if h is not None:vals.append(h-s['groundYGame'])
 terrain.append({'id':f['id'],'samples':len(vals),'profileMinusCurrentGroundRangeGame':[min(vals),max(vals)],'lowerVolumeFillAuthorized':False})
# The generated upper slab alone must have no open/t-junction boundary after source-edge densification.
upper_face_count=2*len(allUpper)+len(placement['refinedUpperOuterUVMetres'])+sum(len(r) for r in placement['refinedUpperHoleUVMetres'])
# build emits lower slab first. Locate exact main/finger upper face slice from the deterministic pure object API.
lower_face_count=2*len(spec['lowerTrianglesUVMetres'])+len(spec['lowerOuterUVMetres'])+sum(len(r) for r in spec['glazedFootprintsUVMetres'])
upper_faces=b.local[lower_face_count:lower_face_count+upper_face_count];edges=collections.defaultdict(lambda:[0,0]);slabTris=[]
for material,face in upper_faces:
 for i in range(1,len(face)-1):
  t=[face[0],face[i],face[i+1]];slabTris.append(t);ps=[tuple(round(v,9) for v in p) for p in t]
  for a,c in zip(ps,ps[1:]+ps[:1]):
   key=tuple(sorted([a,c]));edges[key][0]+=1;edges[key][1]+=1 if a<c else -1
bad=[{'edge':k,'count':v[0],'balance':v[1]} for k,v in edges.items() if v!=[2,0]]
assert not bad,('upper slab unmatched edges',len(bad),bad[:3])
(OUT/'upper-slab-topology.json').write_text(json.dumps({'triangles':len(slabTris),'edges':len(edges),'quantizationMetresGame':1e-9,'unmatchedOrWrongDirectedEdges':len(bad),'status':'CPU upper slab closed; actual float32 GLB remains separate gate'},indent=2)+'\n')
report.update({'status':'CPU candidate only; no GLB/Blender/browser','faces':len(b.faces),'trianglesBeforeExport':len(triangles),'triangleBudget':spec['budget']['maxTriangles'],'materials':sorted(set(m for m,_ in b.faces)),'minimumTriangleAreaGame2':float(minimum),'sourceUpperPlanAreaGame2':upper.area*scale*scale,'upperPlanCoverageErrorGame2':abs(totalArea-upper.area)*scale*scale,'mainPavingAreaPerMaterialPreserved':dict(mainAreaByMaterial),'maxTerminalQueryErrorMetres':max(endErrors),'maxInnerSeamQueryErrorMetres':max(seamErrors),'maxProfileTriangleQueryErrorMetres':max(errors),'maxExactProfileTriangleGradient':max(slope),'unchangedAssemblyFacesChecked':unchanged,'groundFootprintCount':len(foot),'terrainContacts':terrain,'pending':['bounded terrain cut and floor selection','source public arrival','shore lower-space ownership','actual GLB topology and three views/day-night','physical runtime and performance']})
(OUT/'cpu-validation.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'collision-candidate.json').write_text(json.dumps(foot,indent=2)+'\n')
np.savez_compressed(OUT/'cpu-triangles.npz',positions=np.array([t for m,t in triangles]),materialIndices=np.array([sorted(set(m for m,_ in triangles)).index(m) for m,t in triangles],dtype='<i4'))
print(json.dumps(report,indent=2))
