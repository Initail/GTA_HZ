"""Bind actually reviewed references; no reference photographs are packaged."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent;PREFIX=str(OUT.relative_to(ROOT))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
    ids=['1285568956484','1285568958421','1285568960421','1285568962328','1285568964156','1285568966000','1285568967906','1285568969812','1285568971812']
    views=[
      ('river-edge street toward one longitudinal direction','Actual transparent railing, dark top rail, dark/light paving, planter and lamp; no water/ground datum measured.'),
      ('opposing river-edge street direction','Opposite direction shows continuous clear guardrail and public path, repeated lamps/trees; source azimuth uncalibrated.'),
      ('under a shore-side raised bridge toward conference globe','Rectangular concrete piers, transverse steel beams and glass rails above lower open paved space; not a third full public slab.'),
      ('river-edge wood-like slatted surface and skyline','Deck has contrasting warm slatted strip and clear guardrails. Actual plank count/material/current replacement unknown.'),
      ('landward view from open deck toward globe and theatre','Foreground glass-enclosed pit/room, main glazed head behind, source skyline orientation; full hidden lower facade/vertical section not established.'),
      ('outward river-facing view from deck grass patch','Low glass-room wall at side, open park surface, round glass skylight visible; not an invented water feature.'),
      ('close guardrail looking along river in opposite direction','Transparent glass/metal top rail, riverbank edge beyond; uncalibrated grade/tide and current condition unknown.'),
      ('opposing open-park river-edge path with bench','Stone paving, warm slatted path, grass/tree/bench/lamp arrangement and circle skylight; exact inventory pending.'),
      ('landward furniture view toward golden sphere','Confirms slatted wooden-looking bench and concrete arms, public park setting; no unique current furniture placement used.')]
    references=[]
    for index,(ident,(view,obs)) in enumerate(zip(ids,views),1):
        p=Path('<TEMP>/hz-balcony-pc-'+str(index)+'.jpg');assert p.is_file()
        references.append({'id':'photographer-'+str(index),'sourceId':'photographer-2010',
          'url':'https://img.pconline.com.cn/images/upload/upc/tx/photoblog/1009/27/c5/5332390_5332390_'+ident+'_mthumb.jpg',
          'sha256':digest(p),'downloadBytes':p.stat().st_size,'view':view,'observations':obs,
          'reviewedAt':'2026-10-14','reviewMethod':'actual temporary source cache view_image','captureDate':None,
          'cameraCalibration':None,'license':'photographer copyright; unlicensed commercial use prohibited','bundled':False,'releaseTexture':False})
    for ident,source,url,path,view in [
      ('government-aerial','government-2020','https://www.ehangzhou.gov.cn/att/20180614/1528942539914088957.jpg','<TEMP>/hz-balcony-egov.jpg','actual official night aerial toward river; main balcony behind globe/theatre, limited background resolution'),
      ('ihg-aerial','ihg-context','https://digital.ihg.com/is/image/ihg/intercontinental-hangzhou-4466479350-2x1','<TEMP>/hz-icc-ihg-hero.jpg','actual hotel operator night aerial; main balcony behind globe, source outline/approach bridge context')]:
        p=Path(path);references.append({'id':ident,'sourceId':source,'url':url,'sha256':digest(p),'downloadBytes':p.stat().st_size,
          'view':view,'observations':'Illuminated elevated perimeter/shore bridges agree with mapped SW/NE axis. This is background shape context, not a close complete balcony elevation.',
          'reviewedAt':'2026-10-14','reviewMethod':'actual temporary cache view_image','captureDate':None,'cameraCalibration':None,
          'license':'unknown; source retains rights','bundled':False,'releaseTexture':False})
    write(OUT/'photo-review.json',{'schemaVersion':1,'references':references,'imagesAreGameScreenshots':False,
      'limitations':['Photographer street views supply actual opposing directions; two official aerials supply site context with the platform in background.',
        'Not full all-side or current2026 survey; exact glass-room head/section/entry stairs remain pending.',
        'No official or photographer source pixels are bundled, used as atlas or released texture.']})
    evidence=json.loads((OUT/'evidence.json').read_text());evidence['photoReview']=PREFIX+'/photo-review.json';evidence['sourceSnapshots'][PREFIX+'/photo-review.json']=digest(OUT/'photo-review.json')
    write(OUT/'evidence.json',evidence);jobdir=OUT/'task-bundles/city-balcony';write(jobdir/'evidence.json',evidence)
    job=json.loads((jobdir/'job.json').read_text());job['ownership']['workerFiles']=['scripts/landmarks/city_balcony.py'];job['ownership']['workerDirectories']=[PREFIX]
    job['budget'].update({'maxTriangles':28000,'maxMaterials':7});job['budget']['reason']='Source-bound two public floors,3glazed heads,glass rails/piers; ceiling28000/7 frozen before CPU build, under30k integrator cap.'
    write(jobdir/'job.json',job)
    spec=json.loads((OUT/'spec.json').read_text());model=json.loads((jobdir/'model.json').read_text());module=ROOT/'scripts/landmarks/city_balcony.py'
    model.update({'sourceModule':str(module.relative_to(ROOT)),'sourceModuleSha256':digest(module),'sourceSpec':PREFIX+'/spec.json',
      'sourceSpecSha256':digest(OUT/'spec.json'),'artifactPath':'artifacts/cities/hangzhou/landmarks/city-balcony-v1/city-balcony.glb',
      'artifactMeshPrefix':'detail_city-balcony_','estimatedParameters':spec['estimates'],'buildCommand':None,
      'notes':'No worker export. Main integrator owns base levels/water, current stair/ramp/route, material/lighting/collision and all8formal checks. Circle surface representations are not verified open shafts.'})
    write(jobdir/'model.json',model)
    prompt=jobdir/'prompt.md';prompt.write_text(prompt.read_text().replace('scripts/landmarks/city-balcony.py','scripts/landmarks/city_balcony.py'))
    print(json.dumps({'actualPhotosReviewed':len(references),'releasedPhotoPixels':0,'triangleCeiling':28000}))
if __name__=='__main__':main()
