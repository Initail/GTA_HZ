"""Record manually reviewed OSM identities, without granting model/access passes."""
import argparse
import json
from pathlib import Path
from city_config import ROOT,load_city

IDENTITIES={
 'cainiao-headquarters':['way/1228913717'],
 'alibaba-a':['way/645135612'],'alibaba-b':['way/544285896'],'alibaba-c':['way/645093961'],
 'west-lake':['relation/2308774'],'wulin-square':['way/589390765'],
 'lingyin-temple':['way/434365023','way/434365024','way/434365025','way/434366739','way/434366741'],
 'leifeng-pagoda':['way/229726934'],'civic-center':['relation/4762996'],
 'city-balcony':['relation/8718551'],'grand-theatre':['way/626838819'],
 'international-conference-center':['way/626838544'],
 'hangzhou-gate':['way/1015040645','way/1015040647'],
 'big-lotus':['relation/8718531'],'little-lotus':['relation/9874418'],
 'broken-bridge':['way/28538289','way/1466925249'],
 'bai-causeway':['way/4326974','way/28538286','way/28538290','way/29416781'],
 'su-causeway':['way/4335991','way/30072127','way/30072131','way/30072138','way/30072145','way/30072148','way/30075393','way/975869980'],
 'qiantang-bridge':['way/4348186','way/826790145'],
 'fuxing-bridge':['way/29169666','way/29170042','way/154135283','way/154135290','way/336983476','way/340648409','way/589429905'],
 'zhijiang-bridge':['way/306360721','way/306360739','way/589558021'],
 'xixing-bridge':['way/5041735','way/28596734','way/28596757','way/331859982','way/331860328','way/331860329','way/340388832','way/346585778','way/388018764','way/420013388','way/420013389'],
 'boao-tunnel':['way/546241781','way/607103735'],
}

def main(source=None,output_path=None):
 profile=load_city('hangzhou')
 source=Path(source or ROOT/profile['assets']['processedRoot']).resolve()
 output_path=Path(output_path or ROOT/profile['assets']['identityManifest']).resolve()
 if ROOT/'data' not in output_path.parents or output_path.exists():raise ValueError('Fresh identity manifest under data required')
 manifest=json.loads((source/'extraction-manifest.json').read_text())
 features={}
 for layer in ['places','buildings','roads']:
  for f in json.loads((source/(layer+'.geojson')).read_text())['features']:features[f['id']]=f
 objects={}
 for key,values in IDENTITIES.items():
  for value in values:
   if value not in features:raise ValueError('Missing source identity '+value)
  objects[key]={'sourceFeatureIds':values,'sourceNames':{v:features[v]['properties']['name'] for v in values},
   'anchorMethod':'union-centroid-not-entrance','identityStatus':'source-objects-reviewed',
   'modelStatus':'pending','arrivalStatus':'pending-road-collision-and-browser',
   'sourceEvidence':'docs/hangzhou/research/'+('ali/README.md' if key.startswith('alibaba') or key=='cainiao-headquarters' else 'core/'+key+'.evidence.json')}
 objects['lingyin-temple'].update({'anchorFeatureId':'way/434365024',
  'anchorMethod':'Daxiong main hall centroid; not entrance or temple boundary',
  'rejectedFeatureIds':{'way/195189679':'ticket shop; not temple boundary/main hall'},
  'pendingSubscopes':['temple boundary','ground and steps','entry interaction']})
 objects['hangzhou-gate'].update({'anchorWGS84':[120.23255672887714,30.229744850587956],
  'anchorMethod':'mean of the two source tower centroids; gate-round2 spec',
  'sourceEvidence':'docs/hangzhou/research/core/gate-round2/spec.json'})
 objects['xixing-bridge'].update({'roadAccessStatus':'construction-closed-in-source',
  'sourceTags':{'highway':'construction'},'pendingSubscopes':['rebuilding state and visible construction details']})
 for key in ['big-lotus','little-lotus']:
  objects[key]['heightWarning']='OSM low height tag does not describe full stadium roof; architectural evidence required'
 output={'schemaVersion':1,'cityId':'hangzhou','sourceSha256':manifest['source']['sha256'],
  'sourceTimestamp':manifest['source']['osmReplicationTimestamp'],'extractionSha256':manifest['sha256'],
  'status':'geographic-identity-only-not-model-or-access-acceptance','objects':objects}
 output['extractionManifestPath']=str((source/'extraction-manifest.json').relative_to(ROOT))
 output['bboxWGS84']=manifest['bboxWGS84']
 output_path.parent.mkdir(parents=True,exist_ok=True)
 output_path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
 print('Reviewed source identities:',len(objects))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input');p.add_argument('--output')
 a=p.parse_args();main(a.input,a.output)
