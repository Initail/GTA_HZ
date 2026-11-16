"""Record actual ICC photo review without bundling reference pixels."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PREFIX=str(OUT.relative_to(ROOT))


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def main():
    refs=[]
    observations=[
      ('1422515492','actual exterior street side away from the large glazed wedge; geographic azimuth unknown',
       'Truncated ball with terrace gold/glass bands, low rounded gold podium and glass entrance canopy. Not a complete sphere touching ground.'),
      ('1422515494','close side view of rounded podium end',
       'Podium is a curved/clad barrel section with glazed end cut, grid seams; not a simple flat-roof elliptical box.'),
      ('1422515496','night entry frontage looking up at the non-wedge side',
       'Ground glazed lobby and projecting steel/glass canopy, recurring illuminated floor bands, deep vertical seam; light controls/count unknown.'),
      ('1422515498','night close podium-to-sphere frontage',
       'Gold curvature and dark recessed windows/floor bands, curved low podium profile; bushes obscure ground/base detail.'),
      ('1422515500','actual close low-angle sphere terrace detail',
       'Stepped curved panel bands with triangular/recessed side interfaces and glass reflection; spacing/structural dimensions uncalibrated.')]
    for ident,view,obs in observations:
        refs.append(('hunter-'+ident,'hunter','https://ap.hunterdouglas.asia/cms/imgs/project/lg_'+ident+'.jpg',
          '<TEMP>/hz-icc-hunter-'+ident+'.jpg',view,obs))
    petroff_urls={
      '2':'1693920363455-8A9GF9XC609HBCT5T9PM/Hangzhou+ICC+2.jpg',
      '3':'1693920363501-1CO7WO61UA5SHCHFMDEM/Hangzhou+ICC+3.jpg',
      '4':'1693920365027-BRZ2EHQ52IT73PJF2XTX/Hangzhou+ICC+4.jpg',
      '5':'1693920366032-ORKSHLS8FAIZZUD7ESDA/Hangzhou+ICC+5.jpg'}
    for ident,view,obs in [
      ('2','day distant side from landscaped pond/park','Gold bands, dark glazing and vertical seams visible. Historic young landscaping; full current condition/date unknown.'),
      ('3','night street opposite entrance glass and figurative sculpture','Gold bands and large vertical plain/cladding portions; sculpture not modelled or copied.'),
      ('4','actual interior atrium looking at skylight','Circular glass skylight with radial/concentric frame supports shallow glass roof; interior elevators/atrium not in this scope.'),
      ('5','night site sculpture with skyline','Site foreground/sculpture reference only; no extra independent sphere elevation from this photograph.')]:
        refs.append(('petroff-'+ident,'petroff','https://images.squarespace-cdn.com/content/v1/6230e195602a313448ee5b29/'+petroff_urls[ident],
          '<TEMP>/hz-icc-petroff-'+ident+'.jpg',view,obs))
    refs += [
      ('ihg-hero','ihg','https://digital.ihg.com/is/image/ihg/intercontinental-hangzhou-4466479350-2x1',
       '<TEMP>/hz-icc-ihg-hero.jpg','actual aerial twilight from rear/road side, looking toward the river',
       'Full globe, shallow glass skylight, two rounded podium wings, glazed entry corridor and deep vertical break; raised steps/site still unmeasured.'),
      ('ihg-sunmoon','ihg','https://digital.ihg.com/is/image/ihg/intercontinental-hangzhou-5071302710-2x1',
       '<TEMP>/hz-icc-ihg-sunmoon.jpg','actual theatre-facing night frontage from fountain/plaza side',
       'Large tall glazed wedge occupies the C-shaped front between stepped gold bands; not a uniform golden surface. Fountains/water/people not part of object.'),
      ('zjol-2017','zjol2017','https://town.zjol.com.cn/czjsb/201712/W020171214308389545922.png',
       '<TEMP>/hz-icc-zjol-2017.png','aerial context from theatre side; publication2017, capture date not explicit',
       'Confirms conference globe opposite theatre across plaza, glazed front and separated podium wings; low-resolution photo not a calibrated footprint survey.')]
    photos=[]
    for ident,source,url,path,view,obs in refs:
        p=Path(path);assert p.is_file()
        photos.append({'id':ident,'sourceId':source,'url':url,'sha256':digest(p),
          'downloadBytes':p.stat().st_size,'reviewedAt':'2026-10-14','reviewedBy':'landmark_evidence',
          'reviewMethod':'actual view_image of temporary source cache','view':view,
          'captureDate':None,'cameraCalibration':None,'observations':obs,
          'license':'unknown; source and photographer retain rights','bundled':False,'releaseTexture':False})
    review={'schemaVersion':1,'references':photos,
      'scope':'At least actual street side, rear aerial and opposite theatre-facing glazed-front exterior directions; no EXIF/survey azimuth accuracy claimed.',
      'limitations':['All images are reference-only, not release textures/atlas/photo packages.',
        'Interior/skylight and sculpture views do not count as independent full exterior façade directions.',
        'Source publication/upload dates do not establish current2026 exterior condition.']}
    write(OUT/'photo-review.json',review)
    evidence=json.loads((OUT/'evidence.json').read_text());evidence['photoReview']=PREFIX+'/photo-review.json'
    evidence['sourceSnapshots'][PREFIX+'/photo-review.json']=digest(OUT/'photo-review.json')
    write(OUT/'evidence.json',evidence)
    jobdir=OUT/'task-bundles/international-conference-center';write(jobdir/'evidence.json',evidence)
    job=json.loads((jobdir/'job.json').read_text());catalog=json.loads((OUT/'task-catalog.json').read_text())
    job['sourceManifestSha256']=digest(OUT/'task-catalog.json');job['sourceRecord']=catalog['places'][0]
    job['ownership']['workerFiles']=['scripts/landmarks/international_conference_center.py']
    job['ownership']['workerDirectories']=[PREFIX]
    job['budget'].update({'maxTriangles':26000,'maxMaterials':7})
    job['budget']['reason']='Independent truncated globe/podium candidate;26000/7 ceiling fixed before CPU construction, below main integrator30k cap. Material/actual GLB/runtime budget pending.'
    write(jobdir/'job.json',job)
    spec=json.loads((OUT/'spec.json').read_text());model=json.loads((jobdir/'model.json').read_text())
    model.update({'sourceModule':'scripts/landmarks/international_conference_center.py',
      'artifactPath':'artifacts/cities/hangzhou/landmarks/international-conference-center-v1/international-conference-center.glb',
      'artifactMeshPrefix':'detail_international-conference-center_','sourceSpec':PREFIX+'/spec.json',
      'sourceSpecSha256':digest(OUT/'spec.json'),'estimatedParameters':spec['estimates'],'buildCommand':None,
      'notes':'No worker Blender export. Serial main integration owns actual GLB, gold-tinted glass materials, current entry/base levels, night control and all eight formal validations.'})
    module=ROOT/'scripts/landmarks/international_conference_center.py'
    if module.is_file():model['sourceModuleSha256']=digest(module)
    write(jobdir/'model.json',model)
    prompt=jobdir/'prompt.md';prompt.write_text(prompt.read_text().replace('scripts/landmarks/international-conference-center.py',
      'scripts/landmarks/international_conference_center.py'))
    print(json.dumps({'actualImagesReviewed':len(photos),'imagesBundled':False,'triangleCeiling':26000},ensure_ascii=False))


if __name__=='__main__':main()
