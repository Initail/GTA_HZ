"""Export only the two source-owned lake objects into a fresh candidate."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(argv):
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args(argv)
    input=ROOT/a.input;out=ROOT/a.output
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh artifact required')
    data=json.loads(input.read_text())
    for file,expected in data['inputs'].items():
        if sha(ROOT/file)!=expected:raise ValueError('Changed source '+file)
    from city_config import load_city,project
    from hangzhou_bai_mesh import make_faces
    paths={'causeway':'docs/hangzhou/research/core/west-lake-causeways-round2/spec.json','broken':'docs/hangzhou/research/core/broken-bridge-round2/spec.json'}
    specs={k:json.loads((ROOT/v).read_text()) for k,v in paths.items()};anchors={}
    for k,s in specs.items():
        x,z=project(s['anchor']['lon'],s['anchor']['lat'],load_city('hangzhou'));anchors[k]={'x':x,'z':z,'y':0}
    faces,reports=make_faces(data,specs,anchors)
    import city_mesh
    out.mkdir(parents=True);city_mesh.O=out;assets=[]
    for key,identifier in [('causeway','west-lake-causeways'),('broken','broken-bridge')]:
        b=city_mesh.B()
        for f in faces:
            if f['object']==key:b.face(f['material'],f['points'])
        objects=b.finish('detail_'+identifier)
        asset=city_mesh.export(identifier,objects);asset['sha256']=sha(out/asset['file']);assets.append(asset)
    # B emits independent triangles: exported support extraction can verify
    # exact finite positions instead of trusting another analytic sampler.
    (out/'source-faces.json').write_text(json.dumps(faces,separators=(',',':'))+'\n')
    manifest={'cityId':'hangzhou','kind':'Bai datum-bound source models, not visually accepted','assets':assets,
        'inputs':{**data['inputs'],str(input.relative_to(ROOT)):sha(input),
                  'scripts/hangzhou_bai_mesh.py':sha(ROOT/'scripts/hangzhou_bai_mesh.py'),
                  'scripts/build_hangzhou_bai_route.py':sha(Path(__file__))},
        'sourceFacesSha256':sha(out/'source-faces.json'),'sourceReports':reports,
        'changedFaces':sum(f['changed'] for f in faces),'pending':['actual GLB support/rail extraction','CPU actors','base render ownership','browser']}
    (out/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'assets':assets,'changedFaces':manifest['changedFaces']}))
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
