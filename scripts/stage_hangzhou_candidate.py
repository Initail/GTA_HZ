"""Serial staging of checked Hangzhou layers; never activate or publish a city.

This binds collision floors to actual ordinary building render data and copies
verified bytes. Missing gameplay layers and failed physical gates remain explicit.
"""
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path
from city_config import ROOT
from hangzhou_surface import digest

def key(building):return building['id'],json.dumps(building['rings'],separators=(',',':'))
def stage(source,collision,render_data,assets,parking,parking_audit,output):
    source,collision,render_data,assets,parking,parking_audit,output=[Path(p).resolve() for p in [source,collision,render_data,assets,parking,parking_audit,output]]
    if ROOT/'artifacts' not in output.parents or output.exists():raise ValueError('Fresh Hangzhou artifact directory required')
    old=json.loads((source/'city.json').read_text());c_report=json.loads((collision/'report.json').read_text());city=json.loads((collision/'city-runtime-collision.json').read_text())
    if old['meta']['cityId']!='hangzhou' or city['meta']['cityId']!='hangzhou':raise ValueError('City identity mismatch')
    if c_report['inputSha256']['city']!=digest(source/'city.json') or c_report['cityRuntimeCollisionSha256']!=digest(collision/'city-runtime-collision.json'):raise ValueError('Changed collision preparation')
    for part in ['roads','water','green','land','coast','spawn']:
        if old[part]!=city[part]:raise ValueError('Unexpected geographic change '+part)
    rendered=json.loads((render_data/'manifest.json').read_text());models=json.loads((assets/'asset-manifest.json').read_text());audit=json.loads(parking_audit.read_text());parked=json.loads((parking/'parked.json').read_text())
    if not audit['pass'] or audit['sha256']!=digest(parking/'parked.json') or audit['newDetail']['sha256']!=digest(collision/'detail-collision-manifest.json'):raise ValueError('Parking clearance does not bind selected collisions')
    for filename,sha in parked['sourceInputsSha256'].items():
        if digest(ROOT/filename)!=sha:raise ValueError('Changed parking input '+filename)
    source_export=json.loads((ROOT/models['input']/'asset-manifest.json').read_text())
    if models['inputManifestSha256']!=digest(ROOT/models['input']/'asset-manifest.json') or source_export['sourceManifestSha256']!=digest(render_data/'manifest.json'):raise ValueError('Compressed assets do not bind render geometry')
    if rendered['buildingsSha256']!=digest(render_data/'buildings.json'):raise ValueError('Changed rendered building floors')
    floors={key(b):b for b in json.loads((render_data/'buildings.json').read_text())};ordinary=[b for b in city['buildings'] if b['style']!='landmark-detail']
    if len(floors)!=len(ordinary) or {key(b) for b in ordinary}!=set(floors):raise ValueError('Collision/render ordinary footprint mismatch')
    for b in ordinary:
        f=floors[key(b)];b.update(minY=f['minY'],maxY=f['maxY'])
    city['meta']['status']='staged-Hangzhou-candidate-incomplete-not-activated'
    shutil.copytree(source,output)
    (output/'city.json').write_text(json.dumps(city,ensure_ascii=False,separators=(',',':')))
    shutil.copy2(collision/'detail-collision-manifest.json',output/'detail-collision-candidate.json')
    for asset in models['assets']:
        p=assets/asset['file']
        if digest(p)!=asset['sha256']:raise ValueError('Changed compressed model '+asset['file'])
        shutil.copy2(p,output/asset['file'])
    (output/'ebikes').mkdir();shutil.copy2(parking/'parked.json',output/'ebikes/parked.json')
    envelope=json.loads((ROOT/'docs/hangzhou/audit/ebike-body-envelopes.json').read_text());prototype=ROOT/envelope['source']
    if digest(prototype)!=envelope['sha256']:raise ValueError('Changed unscaled e-bike model')
    shutil.copy2(prototype,output/'ebikes/ebikes.glb');shutil.copy2(prototype.parent/'manifest.json',output/'ebikes/manifest.json')
    dependencies=[source/'city.json',source/'navigation.json',collision/'report.json',collision/'detail-collision-manifest.json',render_data/'manifest.json',assets/'asset-manifest.json',parking_audit,parking/'parked.json',prototype,prototype.parent/'manifest.json',Path(__file__)]
    report={'schemaVersion':1,'cityId':'hangzhou','kind':'staged-intermediate-runtime-candidate','sources':{str(p.relative_to(ROOT)):digest(p) for p in dependencies},
      'files':{str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file()},
      'ordinaryBuildingParts':len(ordinary),'detailCollisionShapes':c_report['collisionShapes'],'parkedBikes':len(parked['bikes']),
      'meshApproximation':rendered['meshApproximation'],'active':False,'status':'incomplete; cannot advertise playable or visually accepted',
      'pending':['ground mesh approximation and seams','bridge decks/ramps/tunnels and real access','landmark model floors/full scope/combined manifest','native props and ground joins','near facades/rooftops/ambient occlusion/signs','shoreline water materials and lamps','life hubs/cafe/source arrivals','all gameplay/browser/visual/night/performance']}
    (output/'stage-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sources','files','meshApproximation']},ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for option in ['source','collision','render-data','assets','parking','parking-audit','output']:p.add_argument('--'+option,required=True)
    a=p.parse_args();stage(a.source,a.collision,a.render_data,a.assets,a.parking,a.parking_audit,a.output)
