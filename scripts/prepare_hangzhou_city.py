"""Prepare a non-publishable Hangzhou geographic skeleton in a fresh candidate.

Road topology uses original OSM refs. Lake/river polygons become base water,
without Shenzhen mainland, southern ocean or opposite-shore assumptions.
DEM, elevated surfaces, landmark models and gameplay acceptance remain gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
import re
from pathlib import Path
from collections import Counter
import shapely
from shapely.geometry import shape, box, Point, LineString
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from city_config import ROOT, load_city, project
from hangzhou_navigation import build_navigation, nearest_connected_arrival
from hangzhou_road_direction import road_direction

DRIVEABLE={'motorway','motorway_link','trunk','primary','secondary','tertiary','residential','unclassified','service','trunk_link','primary_link','secondary_link','tertiary_link','living_street'}

def underground_footprint(tags):
    if tags.get('location')=='underground':return True
    try:layer=float(tags.get('layer','0'))
    except ValueError:layer=0
    levels=tags.get('level','').split(';')
    try:only_below=bool(levels[0]) and all(float(value)<0 for value in levels)
    except ValueError:only_below=False
    return layer<0 and (tags.get('building') in ('train_station','subway_station') or only_below)


def parts(geometry,kind):
    if geometry.is_empty: return []
    if geometry.geom_type==kind: return [geometry]
    return [part for member in getattr(geometry,'geoms',[]) for part in parts(member,kind)]


def rings(poly):
    return [[[round(x,4),round(y,4)] for x,y in ring.coords] for ring in [poly.exterior,*poly.interiors]]


def clip_road(feature, city, bounds):
    """Clip only against the study border; retain every real shared node identity."""
    tags=feature['properties']['tags']; kind=tags.get('highway')
    if kind not in DRIVEABLE or tags.get('access') in ('private','no') or tags.get('motor_vehicle')=='no': return []
    oneway,reverse,direction_basis=road_direction(tags)
    refs=feature['properties']['nodeIds']; coords=[project(*p,city) for p in feature['geometry']['coordinates']]
    if reverse:refs=list(reversed(refs));coords=list(reversed(coords))
    chunks=[]; points=[]; nodes=[]
    for index,(a,b) in enumerate(zip(coords,coords[1:])):
        clipped=LineString([a,b]).intersection(bounds)
        for segment in parts(clipped,'LineString'):
            if segment.length<.02: continue
            ends=list(segment.coords)
            keys=[]
            for point in ends:
                if math.dist(point,a)<.00001: keys.append(str(refs[index]))
                elif math.dist(point,b)<.00001: keys.append(str(refs[index+1]))
                else: keys.append(f"clip:{feature['id']}:{index}:{point[0]:.7f}:{point[1]:.7f}")
            if nodes and nodes[-1]!=keys[0]:
                chunks.append((points,nodes)); points=[]; nodes=[]
            if not nodes: points.append(list(ends[0])); nodes.append(keys[0])
            points.append(list(ends[-1])); nodes.append(keys[-1])
    if len(points)>1: chunks.append((points,nodes))
    try: lanes=max(1,min(6,int(tags.get('lanes','2').split(';')[0])))
    except ValueError: lanes=2
    # Legacy game-unit carriageway clearances, independent of geographic scaling.
    width=4.5 if kind=='service' else max(5.8,min(16,lanes*3.0))
    return [{'id':feature['id']+f'#{i}','sourceId':feature['id'],'name':tags.get('name:zh',tags.get('name','支路')),
             'kind':kind,'width':width,'widthStatus':'upstream-gameplay-clearance; not surveyed width',
             'sourceAccessTags':dict(tags),'sourceWayPointOrder':'osm-reversed' if tags.get('oneway','').strip()=='-1' else 'osm-forward',
             'oneway':oneway,'directionBasis':direction_basis,'points':p,'nodeIds':n,'grade':tags.get('layer','0'),
             'bridge':tags.get('bridge','no'),'tunnel':tags.get('tunnel','no'),
             'elevationStatus':'pending-deck-ramp-and-DEM' if tags.get('bridge','no')!='no' or tags.get('tunnel','no')!='no' or tags.get('layer','0')!='0' else 'pending-DEM'} for i,(p,n) in enumerate(chunks)]


def prepare(source, output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if ROOT/'artifacts' not in output.parents or 'public' in output.parts:
        raise ValueError('Use a candidate directory under artifacts, never public')
    if output.exists() and any(output.iterdir()): raise ValueError('Fresh candidate required; existing files preserved')
    extraction=json.loads((source/'extraction-manifest.json').read_text())
    if extraction['source']['status']!='source-verified': raise ValueError('Verified source required')
    def load(layer):
        path=source/(layer+'.geojson')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=extraction['sha256'][layer]: raise ValueError('Changed extraction: '+layer)
        return json.loads(path.read_text())['features']
    city=load_city('hangzhou'); geo=city['geography']; projection=lambda x,y,z=None: project(x,y,city)
    bounds=transform(projection,box(*geo['bboxWGS84']))
    road_features=load('roads')
    roads=[r for f in road_features for r in clip_road(f,city,bounds)]
    if not roads: raise ValueError('No drivable OSM roads')
    graph=build_navigation(roads)
    print(f"Road graph: {len(roads)} ways, {len(graph['nodes'])} nodes, {len(graph['edges'])} edges",flush=True)
    water=[]; greens=[]
    for layer,dest in [('water',water),('green',greens)]:
        for feature in load(layer):
            geometry=transform(projection,shape(feature['geometry'])).intersection(bounds)
            for poly in parts(geometry,'Polygon'):
                if poly.area<20: continue
                # Independent simplification changes shared river banks in
                # opposite directions. Preserve original water topology.
                boundary=poly if layer=='water' else poly.simplify(.3,preserve_topology=True)
                dest.append({'id':feature['id'],'name':feature['properties']['name'],'rings':rings(boundary)})
    wet=unary_union([shapely.Polygon(p['rings'][0],p['rings'][1:]) for p in water])
    # Quantize topology before serializing coordinates. Independent decimal
    # rounding can collapse a water/border neck into a self-touching land ring.
    land=shapely.set_precision(bounds.difference(wet),.0001,mode='valid_output')
    road_lines=[LineString(r['points']) for r in roads]; road_tree=STRtree(road_lines)
    buildings=[]; heights=Counter();omissions=Counter()
    for feature in load('buildings'):
        tags=feature['properties']['tags']
        if tags.get('building') in ('construction','roof','shed','garage','garages') or tags.get('building:part'): continue
        if underground_footprint(tags):
            omissions['explicit-below-ground-footprint-not-surface-building']+=1
            continue
        geometry=transform(projection,shape(feature['geometry'])).intersection(bounds)
        raw=tags.get('height',''); levels=tags.get('building:levels','')
        try:
            match=re.search(r'[0-9]+(?:\.[0-9]+)?',raw); metres=float(match[0])
            if 'ft' in raw: metres*=.3048
            basis='reported-osm-height-unverified'
        except (TypeError,ValueError):
            try: metres=float(levels)*3.3; basis='estimated-osm-levels-3.3m'
            except (TypeError,ValueError): metres=random.Random(feature['properties']['osm_id']).choice([18,24,30,39,54,72,96]); basis='estimated-upstream-typology'
        height=max(3,metres)*geo['scale']; heights[basis]+=1
        for poly in parts(geometry,'Polygon'):
            if poly.area<20: continue
            near=road_tree.query(poly.buffer(12)); clear=[]
            for index in near:
                road=roads[int(index)]
                if road['grade']=='0' and road['bridge']=='no' and road['tunnel']=='no': clear.append(road_lines[index].buffer(road['width']/2+2))
            if clear: poly=poly.difference(unary_union(clear))
            for block in parts(poly,'Polygon'):
                if block.area<20: continue
                buildings.append({'id':feature['id'],'name':feature['properties']['name'],'rings':rings(block.simplify(.3,preserve_topology=True)),
                                  'height':height,'heightSource':basis,'heightMetresSource':metres,
                                  'style':'office' if height>48 or tags.get('building') in ('office','commercial') else 'residential','seed':feature['properties']['osm_id']})
    building_shapes=[shapely.Polygon(b['rings'][0],b['rings'][1:]) for b in buildings]; building_tree=STRtree(building_shapes)
    def blocked(x,z):
        point=Point(x,z)
        if not land.covers(point): return True
        return any(building_shapes[int(i)].distance(point)<3 for i in building_tree.query(point.buffer(3)))
    catalog=json.loads((ROOT/'data/hangzhou/landmarks.json').read_text())
    source_places={f['id']:f for f in load('places')}
    source_places.update({f['id']:f for f in road_features})
    source_places.update({f['id']:f for f in load('buildings')})
    identity_path=ROOT/city['assets']['identityManifest']
    identities=json.loads(identity_path.read_text())
    if identities['sourceSha256']!=extraction['source']['sha256'] or identities['extractionSha256']!=extraction['sha256']:
        raise ValueError('Landmark identities belong to another source extraction')
    marks=[]; blockers=[]
    for record in catalog['places']:
        identity=identities['objects'].get(record['id'],{})
        feature_ids=identity.get('sourceFeatureIds',[])
        features=[source_places.get(key) for key in feature_ids]
        if not features or any(f is None for f in features):
            blockers.append({'id':record['id'],'reason':'source-feature identity requires review'}); continue
        if identity.get('anchorWGS84'):center=Point(identity['anchorWGS84'])
        elif identity.get('anchorFeatureId'):center=shape(source_places[identity['anchorFeatureId']]['geometry']).centroid
        else:center=unary_union([shape(f['geometry']) for f in features]).centroid
        x,z=project(center.x,center.y,city)
        arrival=nearest_connected_arrival([x,z],roads,graph,blocked=blocked,max_distance=1800)
        if not arrival:
            blockers.append({'id':record['id'],'reason':'no connected clear road arrival'}); continue
        marks.append({'id':record['id'],'name':record['name'],'x':x,'z':z,'lon':center.x,'lat':center.y,'area':'杭州',
                      'height':0,'excludeRadius':0,'arrival':arrival['arrival'],'yaw':arrival['yaw'],
                      'sourceFeatureIds':feature_ids,'coordinateStatus':identity['anchorMethod'],'modelStatus':'pending',
                      'roadAccessStatus':identity.get('roadAccessStatus','pending-access-review'),
                      'arrivalData':arrival,'arrivalBrowserVerified':False})
    preferred=next((m for m in marks if m['id']=='wulin-square'),None)
    if not preferred: raise ValueError('Reviewed Wulin anchor required before choosing spawn')
    spawn=nearest_connected_arrival([preferred['x'],preferred['z']],roads,graph,blocked=blocked,max_distance=800)
    if not spawn: raise ValueError('No safe connected spawn candidate')
    road_by_id={r['id']:r for r in roads}
    metadata={'cityId':'hangzhou','version':'candidate-skeleton-1','source':extraction['source'],'originWGS84':geo['originWGS84'],
              'bboxWGS84':geo['bboxWGS84'],'horizontalScale':geo['scale'],'verticalScale':geo['scale'],
              'projection':geo['projection'],'eastMetresPerDegree':geo['eastMetresPerDegree'],'northMetresPerDegree':geo['northMetresPerDegree'],
              'extent':list(bounds.bounds),'counts':{'roads':len(roads),'buildings':len(buildings),'water':len(water),'green':len(greens),'landmarks':len(marks)},
              'heightStatus':dict(heights),'landmarkBlockers':blockers,'terrainStatus':'pending-DEM',
              'surfaceBuildingOmissions':dict(omissions),
              'roadSurfaceStatus':'pending-elevated-decks-ramps-tunnels-and-collision','status':'skeleton-only-not-publishable',
              'southernOcean':False,'oppositeShore':False}
    metadata['identityManifestSha256']=hashlib.sha256(identity_path.read_bytes()).hexdigest()
    data={'meta':metadata,'land':[rings(p) for p in parts(land,'Polygon')],'coast':[], 'roads':roads,'buildings':buildings,
          'green':greens,'water':water,'landmarks':marks,'spawn':{'x':spawn['arrival'][0],'z':spawn['arrival'][1],'yaw':spawn['yaw'],'road':road_by_id[spawn['roadId']]['name']}}
    output.mkdir(parents=True,exist_ok=True)
    (output/'city.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
    (output/'navigation.json').write_text(json.dumps(graph,separators=(',',':')))
    (output/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    hashes={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in ['city.json','navigation.json','metadata.json']}
    (output/'skeleton-manifest.json').write_text(json.dumps({'sourceSha256':extraction['source']['sha256'],'sha256':hashes,'status':'skeleton-only-not-publishable'},indent=2)+'\n')
    print(json.dumps({'output':str(output),'counts':metadata['counts'],'pendingLandmarks':blockers},ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',default=load_city('hangzhou')['assets']['processedRoot']);parser.add_argument('--output',required=True)
    args=parser.parse_args();prepare(args.input,args.output)
