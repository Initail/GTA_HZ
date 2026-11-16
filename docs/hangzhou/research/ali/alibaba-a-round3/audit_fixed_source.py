"""Freeze source feature records and omissions; not a model or GIS repair."""
import hashlib,importlib.util,json,math,sys,xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
r=importlib.util.spec_from_file_location('mapped_metrics',HERE.parent/'measure_osm.py');measure=importlib.util.module_from_spec(r);r.loader.exec_module(measure)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):(HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def points(c):
    if isinstance(c[0],(int,float)):return [c]
    return [p for row in c for p in points(row)]
def match(f,ring):
    ps=points(f['geometry']['coordinates'])
    if f['geometry']['type']=='Point':return 1.0 if measure.inside(ps[0],ring) else 0
    return sum(measure.inside(p,ring) for p in ps)/len(ps)
def metrics(f):
    polygons=f['geometry']['coordinates'];ps=points(polygons)
    bounds=[min(p[0] for p in ps),min(p[1] for p in ps),max(p[0] for p in ps),max(p[1] for p in ps)]
    anchor=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2]
    local=[measure.enu(p,anchor) for p in ps]
    result={'sourceId':f['id'],'tags':f['properties']['tags'],'bboxCenterWGS84':anchor,'boundsWGS84':bounds,
        'basis':'measured-from-fixed-mapped-OSM, not field/cadastral survey','absoluteMappingErrorM':'unknown'}
    if f['geometry']['type']=='MultiPolygon':
        result['mappedAreaM2']=round(sum(abs(measure.signed_area([measure.enu(p,anchor) for p in poly[0]]))-sum(abs(measure.signed_area([measure.enu(p,anchor) for p in ring])) for ring in poly[1:]) for poly in polygons),2)
        result['minimumEnvelope']=measure.rect(local)
    return result

def main():
    manifest=json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text());files={}
    for name in ['buildings','roads','places','pois','water','green']:
        path=ROOT/f'data/processed/hangzhou/{name}.geojson';actual=sha(path)
        assert actual==manifest['sha256'][name],(name,'fixedextracthashchanged')
        files[name]=json.loads(path.read_text())['features']
    sites={id:next(f for f in files['places'] if f['id']==id) for id in ['way/645135612','way/1228913717','way/1293416973','way/1293548829']}
    records={}
    for sid,f in sites.items():
        ring=f['geometry']['coordinates'][0][0];selected={}
        for layer,fs in files.items():
            chosen=[]
            for obj in fs:
                fraction=match(obj,ring)
                if fraction>=.8 if layer=='buildings' else fraction>0:
                    chosen.append(dict(obj,sourceSelection={'method':'atleast80percentvertexinside' if layer=='buildings' else 'anysourcevertexinside','vertexFractionInside':fraction}))
            selected[layer]=chosen
        records[sid]={'parcel':f,'metrics':metrics(f),'layers':selected}
    a9=next(f for f in files['buildings'] if f['id']=='way/456731145')
    old=json.loads((HERE.parent/'alibaba-a-round2/geofabrik-footprints.json').read_text())['features'];oldids={f['id'] for f in old}
    current={f['id']:f for f in files['buildings']}
    for f in old:assert current[f['id']]['geometry']==f['geometry'],('priorfrozenoutlinechanged',f['id'])
    history=[]
    for w in ET.parse(HERE/'references/a9-osm-history.osm').getroot().findall('way'):
        history.append({'version':int(w.attrib['version']),'timestamp':w.attrib['timestamp'],'tags':{t.attrib['k']:t.attrib['v'] for t in w.findall('tag')},'nodeIds':[t.attrib['ref'] for t in w.findall('nd')]})
    assert len({tuple(a['nodeIds']) for a in history})==1
    aux=json.loads((HERE.parent/'snapshots/overpass-alibaba-buildings.json').read_text());way=next(e for e in aux['elements'] if e['type']=='way' and e['id']==456731145)
    assert list(map(str,way['nodes']))==history[-1]['nodeIds']
    north=records['way/1293416973']['layers']['buildings'];east=records['way/1293548829']['layers']['buildings'];hq=records['way/1228913717']['layers']['buildings']
    a=records['way/645135612']['layers'];bodylinks=[f for f in a['buildings'] if f['properties']['tags'].get('building:min_level') or f['properties']['tags'].get('layer') and not f['properties']['tags'].get('name')]
    bodylinks=[f for f in bodylinks if not f['properties']['tags'].get('name')]
    roads=[f for f in a['roads'] if f['properties']['tags'].get('bridge') or f['properties']['tags'].get('layer','0')!='0' or f['properties']['tags'].get('tunnel')]
    save('fixed-source-objects.json',{'source':manifest['source'],'sourceCrs':'EPSG:4326','sourceFileHashes':manifest['sha256'],'sites':records})
    save('a9-source-audit.json',{'sourcePbfSha256':manifest['source']['sha256'],'sourceExtractSha256':manifest['sha256']['buildings'],
        'feature':a9,'metrics':metrics(a9),'history':history,'historyNodesUnchangedAcrossVersions':True,'historyLastNodesExactAuxiliaryMatch':True,
        'historySourceSha256':sha(HERE/'references/a9-osm-history.osm'),'previous13ResearchFootprintsExactFixedMatch':True,
        'OSMlevelsAsMetricHeight':False,'currentOfficialOwnerBuildingIdCrosswalk':None,'modernFacadeHeightEntrance':'unknown',
        'previousRound2SpecSha256':sha(HERE.parent/'alibaba-a-round2/spec.json'),'previousRound2ModuleSha256':sha(ROOT/'scripts/landmarks/alibaba_a.py')})
    save('link-source-audit.json',{'sourcePbfSha256':manifest['source']['sha256'],'mappedUnnamedElevatedBuildings':[metrics(f) for f in bodylinks],
        'alreadyInRound2':[f['id'] for f in bodylinks if f['id'] in oldids],'newProposedSourceIds':[f['id'] for f in bodylinks if f['id'] not in oldids],
        'mappedGradeBridgeTunnelRoads':roads,'historicalArchitectNetworkReportedM':'>1000','historicalCenterlineLengthMeasuredM':None,
        'limitation':'Polygon perimeters/OSM highway segments are not complete architect linkcenterlines. Some ground wetland bridges andunderground metrofootpaths are different structures. no topology/bodygeometry inferred from XY intersections.'})
    save('cainiao-source-audit.json',{'sourcePbfSha256':manifest['source']['sha256'],'parcels':[{'sourceId':sid,**records[sid]['metrics']} for sid in ['way/1228913717','way/1293416973','way/1293548829']],
        'hqMappedBuildingIds':[f['id'] for f in hq],'northIndustryMappedBuildingIds':[f['id'] for f in north],'eastIndustryMappedBuildingIds':[f['id'] for f in east],
        'mappedHeadquartersSourceId':'way/1355173307','separateVisitorAuditoriumSourceId':None,'partnerOfficeTowerSourceIds':[],
        'emptyOSMDoesNotMeanPhysicalAbsence':True,'currentOfficialMultiDirectionPhotosShowUnmappedBuildings':True,
        'pending':['Separatevisitor/auditorium footprint/georeferenceddimensions','North/eastpartneroffices unique footprint andcount','Asbuiltupperjoggingloopheight/route/roadcrossing','Actualdoor/gate/canalbank/rampheightandaccess']})
    print(json.dumps({'A9':metrics(a9),'fourLinksAlreadyModeled':[f['id'] for f in bodylinks if f['id'] in oldids],
        'newTaggedLinks':[f['id'] for f in bodylinks if f['id'] not in oldids],'AgradedRoads':len(roads),'cainiaoHQ':len(hq),'cainiaoNorth':len(north),'cainiaoEast':len(east)},ensure_ascii=False))

if __name__=='__main__':main()
