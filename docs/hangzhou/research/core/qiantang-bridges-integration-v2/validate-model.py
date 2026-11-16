from pathlib import Path
import sys,json,hashlib,math,collections,copy
import numpy as np
P=Path(__file__).resolve().parent;ROOT=P.parents[4];sys.path.insert(0,str(ROOT/'scripts'))
from landmarks import qiantang_bridges_v2 as m
spec=json.loads((P/'spec.json').read_text());lm=spec['placementGame'];checks=[]
def check(name,ok,value=None):checks.append({'name':name,'pass':bool(ok),'value':value})
class B:
 def __init__(self):self.frame=(77.,-63.,.73);self.faces=[]
 def face(self,material,points,uv=None):
  x,z,angle=self.frame;c,s=math.cos(angle),math.sin(angle);self.faces.append((material,[(x+u*c-v*s,z+u*s+v*c,h) for u,v,h in points],uv))
b=B();before=b.frame;report=m.build(b,lm,spec,.6);check('B frame restored',b.frame==before)
adapter,full=m._collision_source(spec);oldm,raw=m._load(spec);effective=copy.deepcopy(raw)
for bridge in effective['bridges']:bridge['profile'].update(spec.get('heightOverridesPhysicalM',{}).get(bridge['id'],{}))
refB=adapter._CaptureB();active={'id':None};decks=[];oldRail=set();originalDeck=oldm._deck;originalRails=oldm._rails
for name in ['_qiantang','_fuxing','_zhijiang']:
 function=getattr(oldm,name)
 def wrap(mesh,bridge,xy,function=function):active['id']=bridge['id'];return function(mesh,bridge,xy)
 setattr(oldm,name,wrap)
def deck(mesh,pt,a,end,width,height,thick,top=False,mat='concrete'):
 start=len(refB.faces);originalDeck(mesh,pt,a,end,width,height,thick,top,mat);decks.append({'mode':'rail' if active['id']=='qiantang-bridge' and top else 'road','sourceFaceRange':[start,len(refB.faces)]})
def rail(*args):
 start=len(refB.faces)
 if active['id']=='qiantang-bridge':args=(*args[:-1],args[-1]+spec.get('qiantangUpperDeckAboveChordM',0))
 originalRails(*args)
 if active['id']=='fuxing-bridge':oldRail.update(range(start,len(refB.faces)))
oldm._deck=deck;oldm._rails=rail;oldm.build(refB,lm,effective,.6);reference={'faces':refB.faces,'decks':decks};remove={i for d in decks if d['mode']=='road' for i in range(*d['sourceFaceRange'])};originalFaces=[(i,f) for i,f in enumerate(refB.faces) if i not in remove|oldRail];point=m._point_transform(spec,full);partRanges=[];start=0
for part in report['bridges']:partRanges.append((start,start+part['faces'],part['id']));start+=part['faces']
newRail={i+next(lo for lo,hi,id in partRanges if id=='fuxing-bridge') for r in report['updatedRailings'] for i in range(r['faceStartInBridge'],r['faceEndInBridge'])};retained=[(i,f) for i,f in enumerate(b.faces) if i not in newRail];errors=[];materialSame=True
for (index,(material,vertices)),(j,actual) in zip(originalFaces,retained):
 bridge=next(id for lo,hi,id in partRanges if lo<=j<hi);expected=np.array([point(v,bridge) for v in vertices]);errors.append(float(np.abs(expected-np.array(actual[1])).max()));materialSame &= material==actual[0]
check('all unchanged source faces except explicitly reconstructed edge railings remain one-to-one',len(originalFaces)==len(retained),[len(originalFaces),len(retained)]);check('every retained material unchanged',materialSame);check('source algorithms with explicit upper-level revision and rigid Fuxing correction match all nonrailing geometry',max(errors)<1e-8,max(errors));check('removed only semantic source road-deck face ranges',len(report['removedRoadDeckPrimitives'])==len([d for d in reference['decks'] if d['mode']=='road']),len(report['removedRoadDeckPrimitives']));check('both Fuxing railings rebuilt from reported-width support edges',len(report['updatedRailings'])==2 and all(len(r['intervalsM'])==5 for r in report['updatedRailings']),[r['intervalsM'] for r in report['updatedRailings']]);check('reported structural identities preserved',report['bridges'][0]['trussSpans']==16 and report['bridges'][1]['largeArches']==2 and report['bridges'][1]['smallArches']==9 and report['bridges'][2]['archPylons']==2)
uvZero=0;fzero=0;triangles=[];uvs=[];materials=[]
for mat,vertices,uv in b.faces:
 for i in range(1,len(vertices)-1):
  ids=[0,i,i+1];t=np.array([vertices[j] for j in ids]);v=np.array([uv[j] for j in ids]).astype('f4').astype('f8');uvZero+=int((v[1,0]-v[0,0])*(v[2,1]-v[0,1])-(v[1,1]-v[0,1])*(v[2,0]-v[0,0])==0);fzero+=int(np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))==0);triangles.append(t);uvs.append(v);materials.append(mat)
check('actual candidate triangles and UV nondegenerate',uvZero==0 and fzero==0,{'zeroUVf32':uvZero,'zeroGeometryf64':fzero});check('candidate within original triangle budget',len(triangles)<=spec['budget']['maxTriangles'],len(triangles));check('road/water/light ownership explicit',report['candidateRoadTopPlanes']==0 and report['candidateWaterPlanes']==0 and report['lightCount']==0)
domains=m.deck_domains(lm,spec,.6);collisions=m.ground_footprints(lm,spec,.6);(P/'deck-ownership.json').write_text(json.dumps({'scope':'actual original road shell support domains; single renderer owner must reproduce complete reported-width support, raw Y concrete and Y+.1 asphalt, suppress default strips/shell duplicates within domain; source rail separate','domains':domains,'blockers':['source renderer support domain generation not integrated','near-end complete Fuxing lower path/railings remains mismatch','rail deck is appearance only, never car navigation']},separators=(',',':')));(P/'collision-candidate.json').write_text(json.dumps({'scope':'retained original structural primitive conservative envelopes; no road deck or full arch bounding box, runtime actor acceptance pending','rows':collisions},separators=(',',':')))
check('road support owner distinct from rail object',all(d['geometryOwner']=='source-road renderer' for d in domains if d['mode']=='road') and len([d for d in domains if d['mode']=='rail'])==1)
np.savez(P/'candidate-mesh.npz',trianglesENU=np.array(triangles),uvs=np.array(uvs),materials=np.array(materials));result={'scope':'pure source B build, retained primitive identity/rigid transform/ownership; no Blender/GLB/browser','moduleSha256':hashlib.sha256((ROOT/'scripts/landmarks/qiantang_bridges_v2.py').read_bytes()).hexdigest(),'specSha256':hashlib.sha256((P/'spec.json').read_bytes()).hexdigest(),'report':report,'checks':checks,'passed':sum(c['pass'] for c in checks),'failed':sum(not c['pass'] for c in checks),'collisionPrimitives':len(collisions),'deckDomains':len(domains)};(P/'validation-model.json').write_text(json.dumps(result,indent=2));print({k:result[k] for k in ['passed','failed','collisionPrimitives','deckDomains']});print([c for c in checks if not c['pass']])
