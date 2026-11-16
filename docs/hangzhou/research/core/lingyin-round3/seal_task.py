"""Bind new independent source module, scope and predeclared budget to task."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent


def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    spec=json.loads((OUT/'spec.json').read_text())
    folder=OUT/'task-bundles/lingyin-temple'
    source=ROOT/'scripts/landmarks/lingyin_site.py'
    write(folder/'evidence.json',json.loads((OUT/'evidence.json').read_text()))
    job=json.loads((folder/'job.json').read_text())
    catalog=json.loads((OUT/'task-catalog.json').read_text())
    job['sourceRecord']=catalog['places'][0]
    job['sourceManifestSha256']=digest(OUT/'task-catalog.json')
    job['budget'].update({'maxTriangles':30000,'maxMaterials':8,
      'basis':'Round3 separate expanded site-detail scope; 30000 ceiling declared before initial31858failure, then geometry reduced to29784. Frozen round2 shellbudget/source unchanged.'})
    job['ownership']['workerFiles']=[str(source.relative_to(ROOT))]
    job['ownership']['workerDirectories']=[str(OUT.relative_to(ROOT))]
    job['scope']=spec['scope']
    job['pendingSubscopes']=spec['pendingSubscopes']
    job['externalGameHeightContract']=spec['baseYContract']
    write(folder/'job.json',job)
    sys.path.insert(0,str(ROOT/'scripts'))
    from landmark_tasks import prompt
    text=prompt(job,folder).replace('scripts/landmarks/lingyin-temple.py',str(source.relative_to(ROOT)))
    text+='\n本轮独立高度接口覆盖：冻结 round2 模块/规格不改。新模块需要显式五殿 hallBaseYGame（绝对游戏单位台基底面Y），不乘.60、不加lm.y。不得用CPU虚构高度当真实地坪。全寺寺界/地坪/真实台阶/安全入口仍pending。父集成串行控制Blender/browser；本工人不启动。\n'
    (folder/'prompt.md').write_text(text)
    model=json.loads((folder/'model.json').read_text())
    model.update({'artifactPath':'artifacts/cities/hangzhou/landmarks/lingyin-site-v1/lingyin-temple.glb',
      'sourceModule':str(source.relative_to(ROOT)),'sourceModuleSha256':digest(source),
      'sourceSpec':str((OUT/'spec.json').relative_to(ROOT)),'sourceSpecSha256':digest(OUT/'spec.json'),
      'sha256':None,'artifactMeshPrefix':None,'buildCommand':None,
      'accuracyClaim':'source-bound frozen shells and explicitly estimated limited site details',
      'estimatedParameters':{'terraces':spec['terraces'],'detailEstimates':spec['detailEstimates'],'plaquePositions':spec['inscriptions']},
      'sourceDependencies':[{'path':spec['baseHallModule'],'sha256':spec['baseHallModuleSha256']},
        {'path':spec['baseHallSpecPath'],'sha256':spec['baseHallSpecSha256']}],
      'externalGameHeightContract':spec['baseYContract'],
      'notes':'No worker GLB. Requires5finite external absolute gameY values; CPU synthetic fixture must not be copied as real ground. Parent must bind chosen-height sources/runtime facts and replace priorLingyin object before modelled/verified.'})
    write(folder/'model.json',model)
    print(json.dumps({'sourceModuleSha256':digest(source),'sourceSpecSha256':digest(OUT/'spec.json'),'artifactCreated':False}))


if __name__=='__main__':main()
