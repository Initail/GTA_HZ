"""Record reviewed reference provenance; no source image is copied into this package."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PREFIX=str(OUT.relative_to(ROOT))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    rows=[
      ('grand','grand-official','https://en.lingyinsi.org/files/image/info/2013/01/10/1734508186.jpg',
       'front oblique close street view','red/yellow wall, green window bands, two named plaques; cropped top'),
      ('kings','kings-official','https://en.lingyinsi.org/files/image/info/2013/01/07/0135071200.jpg',
       'front street view heavily screened by trees','double eave bands, paired plaques, red lattice; exact outline obscured'),
      ('medicine','medicine-official','https://en.lingyinsi.org/files/image/info/2013/01/14/1625412825.jpg',
       'front-side oblique street view','double eaves, hipped-gabled end, high corner curves, red timber and yellow wall'),
      ('dharma','dharma-official','https://en.lingyinsi.org/files/image/info/2013/01/14/1624079367.jpg',
       'front street view','Sutra Library above Dharma Hall; double eaves; pale lower platform; partly screened by trees'),
      ('huayan','huayan-official','https://en.lingyinsi.org/files/image/info/2013/02/07/1620314817.jpg',
       'front-side close view, roof cropped','plaque, red timber lattice, white pillars, yellow wall; full roof not visible'),
      ('grand-wide','axis-photo-2020','https://static.lingyinsi.org/files/image/info/2020/09-24/6373656005492138228306314.jpg',
       'front street view','three-eave profile with shrinking upper tiers, red pillars, yellow end walls; tree occlusion'),
      ('dharma-wide','axis-photo-2020','https://static.lingyinsi.org/files/image/info/2020/09-24/6373656021206045827531159.jpg',
       'front-side upward oblique view','layered hall/library and broad stone terrace; exact rise not calibrated'),
      ('medicine-wide','hall-photo-2020','https://static.lingyinsi.org/files/image/info/2020/10-13/6373818229617920027239205.jpg',
       'opposite front-side oblique view','front plaque/window rhythm and yellow end wall; this angle crops upper roof'),
      ('huayan-wide','hall-photo-2020','https://static.lingyinsi.org/files/image/info/2020/10-13/6373818239314897051994753.jpg',
       'front-side upward view','front lower and upper plaques/eave structure, white terrace rails, yellow/red facade; upper roof incomplete'),
      ('overview','intro-official','https://static.lingyinsi.org/attachment/upload/2020/10/23/296955.jpeg',
       'front street view of Grand Hall','clear triple-eave height proportions; trees obscure both sides; source page date predates image upload path'),
      ('roof-detail-correct','roof-photo-2021','https://static.lingyinsi.org/attachment/upload/2021/10/06/944023.jpeg',
       'elevated close roof view','gray vertical tile ribs, green/gold frieze, elaborate ridge ornament; carving not reproduced')]
    photos=[]
    for ident,source,url,view,observations in rows:
        path=Path('<TEMP>/hz-lingyin-'+ident+'.jpg')
        assert path.is_file()
        photos.append({'id':ident,'sourceId':source,'url':url,'view':view,
                       'cameraAzimuth':'unknown; no EXIF or calibrated camera',
                       'capturedAt':None,'reviewedAt':'2026-10-13',
                       'reviewedBy':'landmark_evidence','reviewMethod':'actual view_image of temporary research cache',
                       'observations':observations,'sha256':digest(path),'downloadBytes':path.stat().st_size,
                       'license':'unknown; publisher retains copyright','bundled':False,'releaseTexture':False})
    illustrated=Path('<TEMP>/hz-lingyin-overview-2.jpg')
    result={'schemaVersion':1,'photos':photos,'illustration':{
        'sourceId':'intro-official','url':'https://static.lingyinsi.org/files/image/info/2015/07/2010164526470971.jpg',
        'sha256':digest(illustrated),'reviewMethod':'actual view_image',
        'interpretation':'uncalibrated birds-eye illustration/composite, not a field photograph',
        'use':'composition context only; not coordinates, height, boundary or DEM', 'bundled':False},
        'excludedDownloadedReferences':['map=transport diagram, not temple footprint',
          'huayan-2=interior statues, outside shell scope',
          'roof-detail=books, wrong image index, not used for roofs',
          'hill-down=stone carvings, not a calibrated hall survey',
          'hill-view=street scene, not a DEM or boundary'],
        'limitations':'2013–2021 published references; capture times unknown; no 2026 on-site survey; no rights to distribute photos obtained.'}
    review_path=OUT/'photo-review.json';write(review_path,result)
    evidence=json.loads((OUT/'evidence.json').read_text())
    evidence['photoReview']=PREFIX+'/photo-review.json'
    evidence['sourceSnapshots'][PREFIX+'/photo-review.json']=digest(review_path)
    write(OUT/'evidence.json',evidence)
    jobdir=OUT/'task-bundles/lingyin-temple'
    write(jobdir/'evidence.json',evidence)
    job=json.loads((jobdir/'job.json').read_text())
    job['ownership']['workerFiles']=['scripts/landmarks/lingyin_temple.py']
    job['ownership']['workerDirectories']=[PREFIX]
    write(jobdir/'job.json',job)
    spec=json.loads((OUT/'spec.json').read_text())
    model=json.loads((jobdir/'model.json').read_text())
    model.update({'artifactPath':'artifacts/cities/hangzhou/landmarks/lingyin-temple-v1/lingyin-temple.glb',
                  'sourceModule':'scripts/landmarks/lingyin_temple.py',
                  'sourceModuleSha256':digest(ROOT/'scripts/landmarks/lingyin_temple.py'),
                  'sourceSpec':PREFIX+'/spec.json','sourceSpecSha256':digest(OUT/'spec.json'),
                  'artifactMeshPrefix':'detail_lingyin-temple_','estimatedParameters':spec['estimates'],
                  'buildCommand':'/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job '+PREFIX+'/task-bundles/lingyin-temple/job.json --spec '+PREFIX+'/spec.json --module scripts/landmarks/lingyin_temple.py --output artifacts/cities/hangzhou/landmarks/lingyin-temple-v1',
                  'notes':'Command supplied but not executed in this round. Awaiting serial Blender export, matte ochre material, terrain/paths and current visual/runtime checks.'})
    write(jobdir/'model.json',model)
    write(OUT/'attempts.json',{'scope':'This round only, actual attempts', 'attempts':[
      {'action':'initial freeze_lingyin.py','result':'failed','reason':'ROOT parents index selected one directory too high; corrected from6 to5'},
      {'action':'first evidence-ready check','result':'passed','scope':'five axial hall shell evidence only'},
      {'action':'first CPU geometry check','result':'failed','triangles':25692,'reason':'above unchanged25000 triangle budget'},
      {'action':'second CPU geometry check','result':'passed','triangles':23844,'change':'one horizontal lattice bar per window; roof/pillars/hall count and checks retained'},
      {'action':'Blender/browser','result':'not-run','reason':'main integrator controls heavy/real-browser work serially'}]})
    print(json.dumps({'photosReviewed':len(photos),'photoHashesFrozen':True,'photosBundled':False},ensure_ascii=False))


if __name__=='__main__':main()
