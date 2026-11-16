"""Conservative v1 byte-mask repair and explicitly bounded physical rebinding.

Retains only existing safe cells; validates complete reserved discs against the
new source. Re-samples slope only where changed physical height can influence
one of its original eight probes. No Blender, runtime or public-city mutation.
"""
from __future__ import annotations
import argparse,json,math,time
from pathlib import Path
from collections import Counter
import numpy as np
import shapely
from shapely.geometry import LineString,Point,Polygon,box
from shapely.strtree import STRtree
from hangzhou_surface import Surface,digest
from prepare_hangzhou_meadow import source_geometry,ground_batch,RADIUS,GUARD
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser()
 for k in ['previous','old-source','source','detail','life','output']:p.add_argument('--'+k,required=True)
 a=p.parse_args();old=ROOT/a.previous;oldsrc=ROOT/a.old_source;src=ROOT/a.source;out=ROOT/a.output
 if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh artifact output required')
 start=time.monotonic();inputs={}
 def read(path):inputs[str(path.relative_to(ROOT))]=digest(path);return json.loads(path.read_text())
 prior=read(old/'report.json');oldmask=read(old/'meadow.json');assert digest(old/'meadow.json')==prior['manifestSha256']
 old_snapshot=old/'preparer-source.py';snapshot_key='scripts/prepare_hangzhou_meadow.py'
 for name,h in prior['inputs'].items():
  path=old_snapshot if name==snapshot_key else ROOT/name
  assert digest(path)==h,('Changed original source',name);inputs[str(path.relative_to(ROOT))]=h
 city=read(src/'city.json');oldcity=read(oldsrc/'city.json');detail=read(ROOT/a.detail);life=read(ROOT/a.life);geo=read(src/'geography/manifest.json');oldgeo=read(oldsrc/'geography/manifest.json');roads=read(src/'geography'/geo['roadLevelsFile']);oldroads=read(oldsrc/'geography'/oldgeo['roadLevelsFile']);sites=read(src/'geography'/geo['siteSurfacesFile']);oldsites=read(oldsrc/'geography'/oldgeo['siteSurfacesFile'])
 assert {k:v for k,v in city.items() if k not in ['roads','landmarks']}=={k:v for k,v in oldcity.items() if k not in ['roads','landmarks']}
 assert [(m['id'],m['x'],m['z'],m.get('excludeRadius',0)) for m in city['landmarks']]==[(m['id'],m['x'],m['z'],m.get('excludeRadius',0)) for m in oldcity['landmarks']]
 assert geo['grid']==oldgeo['grid'] and geo['roadTerrainTransitionGame']==oldgeo['roadTerrainTransitionGame']
 assert digest(src/'geography'/geo['terrainFile'])==digest(oldsrc/'geography'/oldgeo['terrainFile'])
 assert len(roads['roads'])==len(oldroads['roads']) and len(city['roads'])==len(oldcity['roads'])
 def without_height(row):return {k:v for k,v in row.items() if k not in ['heights','heightBasis','previousEstimatedHeights']}
 for before,after in zip(oldcity['roads'],city['roads']):assert without_height(before)==without_height(after)
 changed=[];boxes=[];changed_segments=[];node_changes=set()
 for before,after in zip(oldroads['roads'],roads['roads']):
  assert without_height(before)==without_height(after),('Non-height road change',before['id'])
  if before['heights']==after['heights']:continue
  indices=[i for i,(x,y) in enumerate(zip(before['heights'],after['heights'])) if x!=y]
  node_changes.update(str(after['nodeIds'][i]) for i in indices);changed.append({'id':after['id'],'tier':after['tier'],'changedVertexIndices':indices})
  if after['tier']!=0:continue
  for j in range(len(after['points'])-1):
   if before['heights'][j:j+2]==after['heights'][j:j+2]:continue
   points=after['points'][j:j+2];distance=after['width']/2+geo['roadTerrainTransitionGame']+RADIUS+GUARD
   xs,zs=zip(*points);bounds=[min(xs)-distance,min(zs)-distance,max(xs)+distance,max(zs)+distance];boxes.append(box(*bounds));changed_segments.append({'roadId':after['id'],'segment':j,'points':points,'influenceAndProbeRadiusGame':distance,'conservativeBounds':bounds})
 changed_sites=[]
 for kind in set(oldsites)|set(sites):
  if kind not in ['terrainCuts','terrainPatches']:
   if kind not in ['walkFloors','solidSlabs']:assert oldsites.get(kind)==sites.get(kind)
   continue
  oldby={g['id']:g for g in oldsites.get(kind,[])};newby={g['id']:g for g in sites.get(kind,[])}
  for ident in oldby.keys()|newby.keys():
   if oldby.get(ident)==newby.get(ident):continue
   triangles=[t for g in [oldby.get(ident),newby.get(ident)] if g for t in g['triangles']];points=np.asarray(triangles).reshape(-1,3);lo=points[:,:2].min(axis=0)-RADIUS-GUARD;hi=points[:,:2].max(axis=0)+RADIUS+GUARD;bounds=[*lo,*hi];boxes.append(box(*bounds));changed_sites.append({'kind':kind,'id':ident,'conservativeBounds':bounds})
 for path in [src/'geography'/geo['terrainFile'],*[src/name for name in ['scene-input-integration.json','landmark-scene-integration.json'] if (src/name).exists()],Path(__file__),ROOT/'scripts/prepare_hangzhou_meadow.py',ROOT/'scripts/hangzhou_surface.py',ROOT/'scripts/hangzhou_site_surfaces.py']:inputs[str(path.relative_to(ROOT))]=digest(path)
 geometry={};field=Surface(src);green,land,groups=source_geometry(city,detail,sites,life,geometry)
 edge_trees=[(STRtree(list(shapely.get_parts(green.boundary))),RADIUS+GUARD),(STRtree(list(shapely.get_parts(land.boundary))),RADIUS+GUARD+2)]
 assert all(len(t.geometries)>0 for t,_ in edge_trees);shapely.prepare(green);shapely.prepare(land);affected_tree=STRtree(boxes)
 (out/'meadow').mkdir(parents=True);counts=Counter();tiles=[];changes=[];sample_xy=[];affected_examples=[];preserved_slope_hash=__import__('hashlib').sha256();kept_slope_hash=__import__('hashlib').sha256()
 for n,tile in enumerate(oldmask['tiles']):
  path=old/tile['url'];assert digest(path)==tile['sha256'];data=np.fromfile(path,dtype='u1').reshape(1024,3);indices=np.flatnonzero(data[:,0]==255);assert len(indices)==tile['count'];counts['previousSafeCells']+=len(indices)
  xx=tile['ix']*128+(indices%32+.5)*4;zz=tile['iz']*128+(indices//32+.5)*4;pts=shapely.points(xx,zz);valid=shapely.contains(green,pts)&shapely.contains(land,pts);counts['removed:not-inside-area']+=int((~valid).sum())
  for key,tree,distance in [('green-boundary',*edge_trees[0]),('land-boundary',*edge_trees[1])]+[(k,*v) for k,v in groups.items()]:
   take=np.flatnonzero(valid)
   if not len(take):break
   pairs=tree.query(pts[take],predicate='dwithin',distance=distance);removed=take[np.unique(pairs[0])];valid[removed]=False;counts['removed:'+key]+=len(removed)
  take=np.flatnonzero(valid);output=np.zeros_like(data);output[indices[take]]=data[indices[take]]
  affected=np.zeros(len(take),dtype=bool)
  if len(take):
   pairs=affected_tree.query(pts[take],predicate='intersects');affected[np.unique(pairs[0])]=True
   affected_rows=indices[take[affected]];ax,az=xx[take[affected]],zz[take[affected]]
   counts['recomputedSlopeCells']+=len(affected_rows)
   if len(affected_rows):
    height=ground_batch(field,ax,az);slope=np.zeros(len(affected_rows))
    for radius in [.25,RADIUS]:
     for dx,dz in [(radius,0),(-radius,0),(0,radius),(0,-radius)]:slope=np.maximum(slope,np.degrees(np.arctan(np.abs(ground_batch(field,ax+dx,az+dz)-height)/radius)))
    encoded=np.minimum(255,np.ceil(slope*4)).astype('u1');counts['slopeBytesChanged']+=int(np.sum(encoded!=output[affected_rows,2]));output[affected_rows,2]=encoded
    if len(affected_examples)<100:affected_examples.extend([[float(x),float(z)] for x,z in zip(ax[:4],az[:4])])
   unchanged=indices[take[~affected]];assert np.array_equal(output[unchanged],data[unchanged]);preserved_slope_hash.update(data[unchanged].tobytes());kept_slope_hash.update(output[unchanged].tobytes());counts['unchangedPhysicalRegionCells']+=len(unchanged)
   if len(sample_xy)<2048:sample_xy.append([float(xx[take[len(take)//2]]),float(zz[take[len(take)//2]])])
  counts['safeCells']+=len(take);counts['runtimeEligibleCells']+=int(np.sum((output[:,0]==255)&(output[:,2]<=48)&(output[:,1]<=198)))
  changes.append({'id':tile['id'],'previous':len(indices),'safe':len(take),'slopeRecomputed':int(affected.sum()),'bytesChanged':int(np.sum(output!=data))})
  if len(take):
   file=out/tile['url'];file.write_bytes(output.tobytes());tiles.append({**tile,'count':len(take),'sha256':digest(file)})
  if n%500==0:print('repair',n,'/',len(oldmask['tiles']),'safe',counts['safeCells'],'sec',round(time.monotonic()-start,1),flush=True)
 assert tiles and len(tiles)<=20000 and counts['safeCells']>0;assert counts['previousSafeCells']==prior['budgets']['safeCells'];assert preserved_slope_hash.hexdigest()==kept_slope_hash.hexdigest()
 sample_xy.extend(affected_examples[:64]);q=np.asarray(sample_xy);values=ground_batch(field,q[:,0],q[:,1]);scalar=np.asarray([field.ground(float(x),float(z)) for x,z in q]);parity=float(np.abs(values-scalar).max());assert parity<1e-7
 for name,h in inputs.items():assert digest(ROOT/name)==h,('Input drift',name)
 manifest={**oldmask,'sourceSHA':inputs,'tiles':tiles,'proof':{**oldmask['proof'],'polygonalExtraction':geometry,'allExistingSafeCellsRechecked':True,'repairConservativeSubset':True},'budgets':{'tiles':len(tiles),'safeCells':counts['safeCells'],'runtimeEligibleCells':counts['runtimeEligibleCells'],'binaryBytes':len(tiles)*3072,'maxTwelveCachedTileBytes':12*3072}}
 (out/'meadow.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n')
 proof={'changedRoads':changed,'changedNodeCount':len(node_changes),'changedTier0Segments':changed_segments,'changedGroundSiteGroups':changed_sites,'sameTerrainSha256':digest(src/'geography'/geo['terrainFile']),'roadXYWidthTierNodeIdentityOrderUnchanged':True,'otherGrassRelevantCityGeometryUnchanged':True,'newWalkFloorsAndSlabsExcludedAsGeometry':True,'unchangedRule':'Every retained centre outside every closed segment AABB expanded by width/2+transition+2.9+.02 has all original 8 probes outside changed tier0 segment influence; old/new site changed domains also expanded. Other road heights and exact source order are unchanged. Above-ground tiers do not enter Surface uncut_ground.','unchangedByteSequenceSha256':kept_slope_hash.hexdigest(),'affectedExamples':affected_examples}
 (out/'physical-rebind-proof.json').write_text(json.dumps(proof,indent=2)+'\n');(out/'tile-repair-audit.json').write_text(json.dumps(changes,separators=(',',':'))+'\n')
 report={'kind':'source-bound conservative byte repair and v9 physical rebind','inputs':inputs,'manifestSha256':digest(out/'meadow.json'),'counts':dict(counts),'budgets':manifest['budgets'],'scalarParity':{'samples':len(values),'maximumErrorGame':parity},'samplePoints':[[float(x),float(z),float(y)] for (x,z),y in zip(q,values)],'priorPreparerSnapshot':{'sourcePath':snapshot_key,'sourceSha256':prior['inputs'][snapshot_key],'snapshot':str(old_snapshot.relative_to(ROOT)),'verifiedWithoutEditingOldReport':True},'physicalRebindProofSha256':digest(out/'physical-rebind-proof.json'),'geometry':geometry,'seconds':time.monotonic()-start,'pending':['independent exhaustive reserved-circle geometry audit','runtime actual masks loader','GPU/night/browser/performance'],'status':'candidate; not installed'}
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['counts','budgets','scalarParity','seconds']},indent=2))
if __name__=='__main__':main()
