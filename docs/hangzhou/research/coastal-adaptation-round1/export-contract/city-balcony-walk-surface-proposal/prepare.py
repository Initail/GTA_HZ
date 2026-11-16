from pathlib import Path
import json,hashlib,struct,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,shape
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-surface-proposal';bindings={}
def bind(p):
 p=Path(p);bindings[str(p)]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest();return ROOT/p
def read(p):return json.loads(bind(p).read_text())
def save(n,x):(OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base='artifacts/cities/hangzhou/';prep=base+'shore-meshes-v2/';exp=base+'shore-glb-v2/';inp=base+'render-input-v6/'
m=read(prep+'manifest.json');em=read(exp+'asset-manifest.json');props=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/proposals.json')['proposals'];city=read(inp+'city.json');wet=shapely.union_all([Polygon(w['rings'][0],w['rings'][1:]) for w in city['water']])
sourcechecks={p:hashlib.sha256(bind(p).read_bytes()).hexdigest()==sha for p,sha in m['inputs'].items()}
# Independent GEOS projection/STRtree and linear algebra terrain sampler, not producer Surface.
gm=read(inp+'geography/manifest.json');rl=read(inp+'geography/road-levels.json');grid=gm['grid'];values=np.fromfile(bind(inp+'geography/'+gm['terrainFile']),dtype='<f4').reshape(grid['rows'],grid['columns']);segments=[];spec=[]
for r in rl['roads']:
 if r['tier']!=0:continue
 for i in range(len(r['points'])-1):segments.append(LineString(r['points'][i:i+2]));spec.append((r['heights'][i],r['heights'][i+1],r['width']))
st=STRtree(segments);transition=gm['roadTerrainTransitionGame'];max_margin=max(s[2]/2+transition for s in spec)
def ground(x,z):
 u=(x-grid['x0'])/grid['step'];v=(z-grid['z0'])/grid['step'];i,j=math.floor(u),math.floor(v);fx,fz=u-i,v-j
 corners=np.array([[0,0,1],[1,0,1],[0,1,1]]) if fx+fz<=1 else np.array([[1,1,1],[0,1,1],[1,0,1]])
 heights=[values[j+int(dz),i+int(dx)] for dx,dz,_ in corners];weights=np.linalg.solve(corners.T,np.array([fx,fz,1.]));baseheight=float(np.dot(weights,heights));weights=[];levels=[];q=Point(x,z)
 for k in map(int,st.query(q,predicate='dwithin',distance=max_margin)):
  line=segments[k];ya,yb,width=spec[k];dist=q.distance(line)
  if dist>=width/2+transition:continue
  t=line.project(q)/line.length if line.length else 0;edge=np.clip((dist-width/2)/transition,0,1);weight=float(1-3*edge**2+2*edge**3);weights.append(weight);levels.append(ya+(yb-ya)*t)
 return baseheight+(float(np.average(levels,weights=weights))-baseheight)*max(weights) if weights else baseheight

def topology(ts):
 edges=collections.defaultdict(lambda:[0,0]);vs=set();zero=0
 for t in ts:
  ps=[tuple(p) for p in t];vs.update(ps);zero+=np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))==0
  for a,b in zip(ps,ps[1:]+ps[:1]):
   key=tuple(sorted([a,b]));edges[key][0]+=1;edges[key][1]+=1 if a<b else -1
 volume=float(np.einsum('ij,ij->i',ts[:,0]-ts[0,0],np.cross(ts[:,1]-ts[0,0],ts[:,2]-ts[0,0])).sum()/6)
 return {'vertices':len(vs),'edges':len(edges),'triangles':len(ts),'euler':len(vs)-len(edges)+len(ts),'zeroArea':int(zero),'badEdges':sum(c!=2 or b!=0 for c,b in edges.values()),'signedVolume':volume}
def glb(p):
 raw=bind(p).read_bytes();magic,v,length=struct.unpack_from('<4sII',raw);assert magic==b'glTF' and length==len(raw);off=12;g=None;blob=None
 while off<len(raw):
  n,k=struct.unpack_from('<II',raw,off);chunk=raw[off+8:off+8+n];off+=8+n
  if k==0x4E4F534A:g=json.loads(chunk)
  if k==0x004E4942:blob=chunk
 def acc(i):
  a=g['accessors'][i];bv=g['bufferViews'][a['bufferView']];dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];size=np.dtype(dtype).itemsize;stride=bv.get('byteStride',n*size);offset=bv.get('byteOffset',0)+a.get('byteOffset',0)
  return np.ndarray((a['count'],n),dtype=dtype,buffer=blob,offset=offset,strides=(stride,size)).copy()
 out=[]
 def walk(i,parent):
  node=g['nodes'][i]
  if 'matrix' in node:local=np.array(node['matrix']).reshape(4,4).T
  else:
   local=np.eye(4);x,y,z,w=node.get('rotation',[0,0,0,1]);local[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(node.get('scale',[1,1,1]));local[:3,3]=node.get('translation',[0,0,0])
  world=parent@local
  if 'mesh' in node:
   mesh=g['meshes'][node['mesh']]
   for p in mesh['primitives']:
    a=p['attributes'];pos=acc(a['POSITION']);ind=acc(p['indices']).ravel() if 'indices' in p else np.arange(len(pos));wp=(np.c_[pos,np.ones(len(pos))]@world.T)[:,:3];enu=wp[:,[0,2,1]]*np.array([1,-1,1]);uv=acc(a['TEXCOORD_0']) if 'TEXCOORD_0' in a else None;norm=acc(a['NORMAL']) if 'NORMAL' in a else None
    out.append({'name':mesh['name'],'material':g['materials'][p['material']]['name'],'triangles':enu[ind.reshape(-1,3)],'uv':None if uv is None else uv[ind.reshape(-1,3)],'normals':norm,'world':world.tolist()})
  for child in node.get('children',[]):walk(child,world)
 for i in g['scenes'][g.get('scene',0)]['nodes']:walk(i,np.eye(4))
 return out,g
import importlib.util
folder='docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2/';specb=read(folder+'candidate-spec.json');placement=specb['floorPlacement'];collisions=read(folder+'collision-candidate.json');source=bind('scripts/landmarks/city_balcony_floor_v2.py');ss=importlib.util.spec_from_file_location('balcony_floor',source);mod=importlib.util.module_from_spec(ss);ss.loader.exec_module(mod);bind('src/city-walk.ts');bind('src/driving.ts')
artifact=base+'landmarks/city-balcony-floor-v2/city-balcony.glb';actual,g=glb(artifact);artifactHash=bindings[artifact];ax,az=placement['anchorGame'];by=placement['baseYGame'];a=placement['axisRadiansEastCCW'];ca,sa=math.cos(a),math.sin(a);scale=.6;lm={'x':ax,'z':az,'y':by};upperY=placement['upperYGame'];WALK_RADIUS=.23

def enu(p):u,v,h=p;return [ax+(u*ca-v*sa)*scale,az+(u*sa+v*ca)*scale,by+h*scale]
def xyz(p):x,z,y=enu(p);return [x,y,z]
def xz(p):return enu([*p,0])[:2]
def canonical(t):return tuple(sorted(tuple(round(float(x),6) for x in p) for p in t))
actualFaces={}
for part in actual:
 for i,t in enumerate(part['triangles']):actualFaces.setdefault(canonical(t),[]).append({'mesh':part['name'],'triangleIndex':i,'material':part['material']})
def triangle(ident,pts,ref):
 world=[enu(p) for p in pts];serialized=np.asarray(world,dtype='<f4').astype('f8');hits=actualFaces.get(canonical(serialized),[])
 if not hits:raise ValueError('Missing actual support triangle '+ident)
 n=np.cross(serialized[1]-serialized[0],serialized[2]-serialized[0]);assert n[2]>0
 return {'id':ident,'verticesGameXYZ':[[x,y,z] for x,z,y in world],'sourceRef':ref,'actualGlbFaces':hits,'actualFloat32VerticesGameXYZ':[[x,y,z] for x,z,y in serialized],'maxFloat32PositionErrorGame':float(np.linalg.norm(serialized-np.array(world),axis=1).max())}
levels=[]
for level in ['lower','upper']:
 ts=[]
 if level=='lower':
  for i,t in enumerate(specb['lowerTrianglesUVMetres']):ts.append(triangle('lower-'+str(i),[[*p,0] for p in t],{'field':'lowerTrianglesUVMetres','index':i}))
 else:
  for i,t in enumerate(placement['mainUpperTrianglesUVMetres']):ts.append(triangle('upper-main-'+str(i),[[*p,6] for p in t],{'field':'floorPlacement.mainUpperTrianglesUVMetres','index':i}))
  for f in placement['fingers']:
   for i,t in enumerate(f['trianglesUVHMetres']):ts.append(triangle('upper-'+f['id']+'-'+str(i),t,{'field':'floorPlacement.fingers.'+f['id']+'.trianglesUVHMetres','index':i}))
 ring=specb[level+'OuterUVMetres'];levels.append({'id':'city-balcony:'+level,'kind':'public-floor-support','baseYGame':by if level=='lower' else upperY,'ringsXZ':[[xz(p) for p in ring],*[[xz(p) for p in h] for h in specb['glazedFootprintsUVMetres']]],'triangles':ts,'requiresHeightAwareBodyOccupancyCheck':True,'supportIsNotWholeHeightCollider':True,'entryPolicy':'two named continuous ground seams only' if level=='upper' else 'no source-verified entry or connection yet; do not auto-select this floor from ground or upper','materialClaim':'existing modeled concrete/paving, not a verified lawn layer'})
# Height-aware original column/wall envelopes, not all-height platform footprints.
blocks=[{'id':'existing-solid-'+str(i),'kind':c['kind'],'ringsXZ':[c['polygonGame']],'minYGame':c['minYGame'],'maxYGame':c['maxYGame'],'sourceFeatureIds':c['sourceFeatureIds'],'basis':c['basis'],'doNotApplyOutsideHeightInterval':True} for i,c in enumerate(collisions)]
# Exact source rail panel sheets, including upper glass-room perimeters. No full-building barrier.
rails=[]
def emit_rails(ident,ring,levelM,openEdges):
 rail=specb['estimates']['rails']['value']
 for edge,(p,q) in enumerate(zip(ring,ring[1:]+ring[:1])):
  if edge in openEdges:continue
  count=max(1,math.ceil(math.dist(p,q)/rail['panelPitchM']))
  for j in range(count):
   aa=[p[k]+(q[k]-p[k])*j/count for k in [0,1]];bb=[p[k]+(q[k]-p[k])*(j+1)/count for k in [0,1]]
   def h(v,offset):
    hh=levelM+offset
    if hh>=placement['upperAssemblyDeformMinimumRelativeMetres']:hh+=mod._profile_height(*v,specb,1.)-6
    return hh
   pts=[[*aa,h(aa,.1)],[*bb,h(bb,.1)],[*bb,h(bb,rail['heightM'])],[*aa,h(aa,rail['heightM'])]];vertices=[xyz(v) for v in pts]
   rails.append({'id':ident+'-edge-'+str(edge)+'-panel-'+str(j),'sourceOuterEdgeIndex':edge,'levelId':'city-balcony:upper' if levelM==6 else 'city-balcony:lower','kind':'thin-glass-guard-sheet-with-steel-frame','verticesGameXYZ':vertices,'planSegmentXZ':[xz(aa),xz(bb)],'minYGame':min(p[1] for p in vertices),'maxYGame':max(p[1] for p in vertices),'actualSheetThicknessGame':0,'steelFrameWidthGame':rail['frameWidthM']*.6,'bodyCollisionPolicy':'finite-height swept segment/panel using existing actor radius; not a floor, not an infinite wall','basis':'modeled source perimeter guard; dimensions estimated'})
emit_rails('upper-perimeter',specb['upperOuterUVMetres'],6,{9,13,14,15});emit_rails('lower-perimeter',specb['lowerOuterUVMetres'],0,{7,8,9,10})
for i,h in enumerate(specb['glazedFootprintsUVMetres']):emit_rails('upper-glazed-hole-'+str(i),h,6,set())
# Actual skylight geometry is a raised cover above an intact slab, never a modeled shaft.
skylights=[]
for i,(u,v) in enumerate([(-128,-46),(-82,-48),(-32,-49),(17,-51),(66,-47),(112,-39)]):
 if not mod._public(u,v,specb,'upper'):continue
 radius=specb['estimates']['skylights']['value']['radiusM'];ring=[[u+radius*math.cos(j*2*math.pi/20),v+radius*math.sin(j*2*math.pi/20)] for j in range(20)];poly=Polygon([xz(q) for q in ring]);overlays=[]
 for part in actual:
  if part['material'] not in ['steel','landmarkglass']:continue
  expected=upperY+(.05+.065/2)*.6 if part['material']=='steel' else upperY+.035*.6
  for j,t in enumerate(part['triangles']):
   if max(abs(t[:,2]-expected))>.0002:continue
   n=np.cross(t[1]-t[0],t[2]-t[0])
   if n[2]<=1e-10:continue
   if not poly.buffer(.04).covers(Polygon(t[:,:2])):continue
   overlays.append({'id':'skylight-'+str(i)+'-'+part['material']+'-'+str(j),'verticesGameXYZ':[[float(x),float(y),float(z)] for x,z,y in t],'actualGlbMesh':part['name'],'actualGlbTriangleIndex':j,'sameSupportLevelId':'city-balcony:upper'})
 skylights.append({'id':'skylight-'+str(i),'sourceLocalCenterUVMetres':[u,v],'ringsXZ':[list(poly.exterior.coords)],'radiusGame':radius*.6,'glassCoverYGame':upperY+.021,'rimYRangeGame':[upperY+(.05-.065/2)*.6,upperY+(.05+.065/2)*.6],'intactPublicSlabBelow':True,'actualModeledShaft':False,'currentRealSiteLoadBearingUnknown':True,'occupancyPolicy':'same-upper-level thin cover/frame detail; never create a hole or link to lower; these actual top triangles may supply <=.0495g sole offset without changing step rule','actualTopOverlayTriangles':overlays})
# Full-width source shore mouths, bounded geometric crossing data. No instantaneous floor switch.
paths=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/riverside-paths.geojson')['features'];seams=[]
for f in placement['fingers']:
 poly=Polygon([xz(q) for q in f['polygonUVMetres']]);edges=[];rawline=[];crossings=[]
 for e in f['boundary']:
  if e['kind']!='terminal':continue
  points=[enu(p) for p in e['samplesUVHMetres']];edges.append({'sourceVertexIndices':e['sourceVertexIndices'],'verticesGameXYZ':[[x,y,z] for x,z,y in points]});rawline.extend(points[:-1])
  for aa,bb in zip(points,points[1:]):
   aa,bb=np.array(aa),np.array(bb);mid=(aa+bb)/2;d=bb[:2]-aa[:2];n=np.array([-d[1],d[0]])/np.linalg.norm(d)
   if poly.covers(Point(mid[:2]+n*.05)):n=-n
   out=mid[:2]+n*.3;inside=mid[:2]-n*.3;profile=mod.deck_height_game(*inside,lm,specb,.6,'upper');gnd=ground(*out);gap=abs(gnd-mid[2]);candidate={'sourceEdge':e['sourceVertexIndices'],'seamMidpointGameXYZ':[mid[0],mid[2],mid[1]],'outwardNormalXZ':n.tolist(),'insidePointGameXYZ':[inside[0],profile,inside[1]],'outsidePointGameXYZ':[out[0],gnd,out[1]],'currentOutsideGroundMinusSeamGame':gnd-mid[2],'currentInsideToOutsideHeightDeltaGame':abs(gnd-profile),'lessThanUnchangedStep048':bool(abs(gnd-profile)<.48),'outsideWet':bool(wet.covers(Point(out)))};crossings.append(candidate)
 rawline.append(points[-1]);line=LineString([q[:2] for q in rawline]);near=[]
 for path in paths:
  tags=path['properties']['tags'];geom=shape(path['geometryGame']);distance=line.distance(geom)
  if distance<10:near.append({'sourceId':path['id'],'distanceToWholeSeamGame':distance,'tags':tags,'nodeIds':path['properties']['nodeIds'],'identity':'source proximity only; no graph/actual entry assertion'})
 near.sort(key=lambda r:r['distanceToWholeSeamGame'])
 endMargin=WALK_RADIUS+specb['estimates']['rails']['value']['frameWidthM']*.6/2+.001
 seams.append({'id':'city-balcony:upper:'+f['id']+'-shore-entry','fromSupport':'external-ground','toSupport':'city-balcony:upper','sourceRelation':'relation/8718551','sourceTerminalEdges':f['terminalSourceEdges'],'segments':edges,'wholeSeamLengthGame':line.length,'previewSafeCenterStationsGame':[endMargin,line.length-endMargin],'previewTrimBasis':'walk radius.23 + modeled steel halfwidth.0255 + .001 float allowance; still requires current CityWalk.clear and all props/agents checks','crossingSamples':crossings,'nearbySourcePaths':near[:8],'transitionRules':['must physically cross one of these finite source terminal edges from its outside to inside or reverse','retain previous support and reference feet height throughout this move; body footprint must remain supported and clear','source/destination floor height difference must satisfy unchanged <.48 step rule; no picking highest/lowest layer by XY','allow no direct upper-to-lower transition; no stairs/lift verified','source path proximity is not a connected public-route/operational-door acceptance'],'runtimeOrPublicEntryAccepted':False})
# Direct blocker context: original collision water check would reject overwater public deck unless scoped to valid support.
runtimeContract={'preservedParameters':{'walkSpeed':1.6,'runSpeed':4.2,'walkRadius':.23,'stepStrictLessThan':.48,'carExitMaxHeightDifference':.55,'carEnterMaxHeightDifference':.8,'carEnterPathStepMax':.48,'cameraEyeHeight':1.53},'supportStateRequired':['current support ID','previous feet height','previous position and actual swept crossing'],'floorSelection':'retain current level across same-level adjacent triangles; enter/leave upper only by named shore seam; lower data exists but no validated transition edge yet','notAllowed':['max(all floor heights, terrain)','nearest floor regardless vertical state','instant upper/lower flip at same XY','turn entire floor footprint into all-height building collision','blanket water/land/obstacle exemption','tunnel/shared XY becomes access edge'],'waterPolicy':'only a finite-height valid current public support may satisfy local footing over water; still check rail/glass/columns, body and boundaries; do not mutate base water polygon','grassAndStairs':'upper park/grass appearance, exact real stair/elevator locations and lower entry all unknown; no extra support triangles generated','vehicleRules':'no new parking/upper car spawn/car access inferred; preserve car enter/exit checks and heights'}
save('public-walk-surfaces.json',{'schemaVersion':1,'id':'city-balcony-public-walk-candidate','cityId':'hangzhou','coordinateOrder':'verticesGameXYZ=[east,up,north], game units; never scale again','sourceArtifact':artifact,'sourceArtifactSha256':artifactHash,'moduleSha256':bindings['scripts/landmarks/city_balcony_floor_v2.py'],'levels':levels,'runtimeContract':runtimeContract,'status':'geometry ready for independent runtime integration; not reachable/physical/visual accepted'})
save('occupancy.json',{'existingFiniteHeightSolids':blocks,'guardPanels':rails,'skylights':skylights,'solidFloorMustNotBecomeInfiniteCollider':True,'bodyHeightExistingGame':1.6,'pending':['world prop/vegetation clearance','guard steel full segment collision against body','actual public/lower entry and routing']})
save('entry-seams.json',{'seams':seams,'groundSource':'render-input-v6 independent road/DSM current game sampler; proposed local terrain cuts not assumed active','bodyOrRuntimeTested':False})
save('input-bindings.json',bindings)
print(json.dumps({'levels':[(r['id'],len(r['triangles'])) for r in levels],'guardPanels':len(rails),'skylights':[(r['id'],len(r['actualTopOverlayTriangles'])) for r in skylights],'seams':[(r['id'],r['wholeSeamLengthGame'],max(s['currentInsideToOutsideHeightDeltaGame'] for s in r['crossingSamples']),len(r['nearbySourcePaths'])) for r in seams]},indent=2))
