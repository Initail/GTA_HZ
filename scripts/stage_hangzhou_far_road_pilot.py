"""Stage the independently sampled single-road far candidate; patch only image URIs."""
import json,struct,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/cities/hangzhou/far-lod-investigation-v1/outer-filter-v2/roads/-1_-2'
ORIGINAL=ROOT/'artifacts/cities/hangzhou/stream-mesh-v1/roads'
OUT=ROOT/'artifacts/cities/hangzhou/city-leisure-v15/public/base-far-pilot/roads'
def sha(data):return hashlib.sha256(data).hexdigest()
def unpack(data):
 n=struct.unpack_from('<I',data,12)[0];return json.loads(data[20:20+n]),data[20+n:]
def main():
 if OUT.exists():raise SystemExit('Existing pilot is protected')
 report=json.loads((SOURCE/'report.json').read_text());raw=(SOURCE/'far.glb').read_bytes()
 assert sha(raw)==report['output']['sha256']
 checks=[]
 for i,part in enumerate(report['geometryValidationParts']):
  p=SOURCE/('geometry-part-'+str(i)+'.json');r=json.loads(p.read_text())
  assert r['geometryPassed'] and r['id']==part and r['candidateSha256']==sha(raw) and r['reportSha256']==sha((SOURCE/'report.json').read_bytes())
  checks.append({'file':str(p.relative_to(ROOT)),'sha256':sha(p.read_bytes()),'maxGame':r['maxGame']})
 manifest=json.loads((ORIGINAL/'manifest.json').read_text());original=next(t for t in manifest['tiles'] if t['id']=='roads:-1,-2')
 assert original['sha256']==report['input']['sha256']
 doc,binary=unpack(raw);old,_=unpack((ORIGINAL/original['file']).read_bytes())
 assert [m['name'] for m in doc['materials']]==[m['name'] for m in old['materials']]
 assert len(doc['images'])==len(manifest['textures'])
 OUT.mkdir(parents=True);(OUT/'tiles').mkdir();(OUT/'textures').mkdir()
 for image,texture in zip(doc['images'],manifest['textures']):
  assert image.get('bufferView') is None
  source=(SOURCE/image['uri']).resolve();expected=(ORIGINAL/texture['file']).resolve();assert source==expected
  assert sha(source.read_bytes())==texture['sha256']
  image['uri']='../'+texture['file'];shutil.copyfile(source,OUT/texture['file'])
 head=json.dumps(doc,separators=(',',':')).encode();head+=b' '*((-len(head))%4)
 data=struct.pack('<IIIII',0x46546c67,2,20+len(head)+len(binary),len(head),0x4e4f534a)+head+binary
 file=OUT/original['file'];file.write_bytes(data)
 assert unpack(data)[1]==binary
 tile=dict(original,bytes=len(data),sha256=sha(data),logicalBytes=report['output']['logicalBytes'],triangles=report['output']['triangles'],role='roads')
 result={'schemaVersion':1,'scope':'one far road tile, never a full city manifest','fullCoverage':False,'tile':tile,'textures':manifest['textures'],'sourceManifestSha256':sha((ORIGINAL/'manifest.json').read_bytes()),'sourceReportSha256':sha((SOURCE/'report.json').read_bytes()),'sourceCandidateSha256':sha(raw),'geometryChecks':checks,'imageUriOnlyChange':True,'binaryPayloadPreserved':True,'browserAccepted':False,'runtimeInstalled':False}
 (OUT/'descriptor.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'bytes':len(data),'triangles':tile['triangles'],'geometryParts':len(checks),'maxSampledErrorGame':max(c['maxGame'] for c in checks),'fullCoverage':False}))
if __name__=='__main__':main()
