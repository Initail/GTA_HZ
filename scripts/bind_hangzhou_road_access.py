"""Bind fixed-source tags to existing road objects without touching their geometry.

Dry run by default. --output writes one NEW city.json after all checks pass.
No download, Blender, road reconstruction, graph rewrite or current-file overwrite.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math
from pathlib import Path

FIELDS=('points','nodeIds','heights','grade','bridge','tunnel','width','oneway')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def is_subsequence(values,source):
    cursor=iter(source)
    return all(any(candidate==value for candidate in cursor) for value in values)
def bind(city,features,geo):
    if city.get('meta',{}).get('cityId')!='hangzhou':raise ValueError('Only explicitly identified Hangzhou input is supported')
    by_id={feature['id']:feature for feature in features}
    if len(by_id)!=len(features):raise ValueError('Duplicate source feature IDs')
    physical_before=hashlib.sha256(canonical([{key:road.get(key) for key in ('id',*FIELDS)} for road in city['roads']])).hexdigest()
    counts=collections.Counter();tag_keys=collections.Counter();ambiguous=[];records=[]
    for road in city['roads']:
        ident=road.get('sourceId')
        if not ident or ident not in by_id:raise ValueError('Missing exact sourceId binding: '+road['id'])
        feature=by_id[ident];props=feature['properties'];tags=props.get('tags');refs=list(map(str,props.get('nodeIds',[])));points=feature['geometry']['coordinates']
        if not isinstance(tags,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in tags.items()):raise ValueError('Non-string source tags: '+ident)
        if not refs or len(refs)!=len(points):raise ValueError('Invalid source nodes: '+ident)
        if len(road.get('nodeIds',[]))!=len(road.get('points',[])):raise ValueError('Current road lacks source identities: '+road['id'])
        normalized_reverse=tags.get('oneway','').strip()=='-1'
        expected=list(reversed(refs)) if normalized_reverse else refs
        source_nodes=set(refs);current=list(map(str,road['nodeIds']));real=[node for node in current if node in source_nodes]
        if not real or any(node not in source_nodes and not node.startswith('clip:'+ident+':') for node in current):raise ValueError('Unexpected non-source node: '+road['id'])
        if not is_subsequence(real,expected):raise ValueError('Road node order disagrees with normalized source direction: '+road['id'])
        if is_subsequence(real,list(reversed(expected))):ambiguous.append(road['id'])
        # Verify that source IDs still refer to the original projected x/z vertices.
        positions=collections.defaultdict(list)
        for node,point in zip(refs,points):positions[node].append(point)
        for node,point in zip(current,road['points']):
            if node not in source_nodes:continue
            if not any(math.dist(point,[(ll[0]-geo['originWGS84'][0])*geo['eastMetresPerDegree']*geo['scale'],(ll[1]-geo['originWGS84'][1])*geo['northMetresPerDegree']*geo['scale']])<0.001 for ll in positions[node]):raise ValueError('Changed x/z source position: '+road['id'])
        point_order='osm-reversed' if normalized_reverse else 'osm-forward'
        records.append((road,dict(tags),point_order));counts[point_order]+=1;tag_keys.update(tags.keys())
    # Mutate only the two additive metadata fields, after validation of every road.
    for road,tags,point_order in records:
        road['sourceAccessTags']=tags
        road['sourceWayPointOrder']=point_order
    physical_after=hashlib.sha256(canonical([{key:road.get(key) for key in ('id',*FIELDS)} for road in city['roads']])).hexdigest()
    if physical_before!=physical_after:raise AssertionError('Physical road fields changed')
    return {'roadsBound':len(records),'pointOrderCounts':dict(counts),'allSourceTagsPreserved':True,'tagKeyCounts':dict(sorted(tag_keys.items())),
            'ambiguousOrderValidatedByExistingNormalizationContract':ambiguous,'physicalFields':list(FIELDS),'physicalSha256Before':physical_before,'physicalSha256After':physical_after,
            'geometryUnchanged':True,'navigationUnchanged':True,'notes':['sourceAccessTags contains all original way tags, not a filtered permission whitelist','sourceWayPointOrder describes current points relative to original OSM refs','absence of an access tag does not prove that a site is ungated','existing non-road city fields and objects are not edited']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--city',required=True);p.add_argument('--source',required=True);p.add_argument('--extraction-manifest',required=True);p.add_argument('--profile',required=True);p.add_argument('--output');p.add_argument('--report');a=p.parse_args()
    city_path,source_path,manifest_path,profile_path=map(Path,[a.city,a.source,a.extraction_manifest,a.profile])
    manifest=json.loads(manifest_path.read_text());expected=manifest['sha256']['roads']
    if sha(source_path)!=expected:raise ValueError('Fixed source roads hash does not match extraction manifest')
    if manifest.get('source',{}).get('status')!='source-verified':raise ValueError('Source is not verified')
    city=json.loads(city_path.read_text());features=json.loads(source_path.read_text())['features'];profile=json.loads(profile_path.read_text())
    report=bind(city,features,profile['geography']);report.update({'inputCitySha256':sha(city_path),'inputRoadsSha256':expected,'sourceSnapshot':manifest.get('source',{}).get('snapshot'),'outputWritten':False})
    if a.output:
        output=Path(a.output).resolve()
        if output.exists() or output==city_path.resolve() or 'public' in output.parts:raise ValueError('Output must be a NEW non-public file; no existing candidate may be overwritten')
        if not output.parent.is_dir():raise ValueError('Create and review the fresh output directory explicitly before writing')
        output.write_text(json.dumps(city,ensure_ascii=False,separators=(',',':'))+'\n');report['outputWritten']=True;report['outputSha256']=sha(output)
    if a.report:
        target=Path(a.report)
        if target.exists():raise ValueError('Report path already exists')
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ['roadsBound','pointOrderCounts','allSourceTagsPreserved','geometryUnchanged','navigationUnchanged','outputWritten','inputRoadsSha256']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
